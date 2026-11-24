"""Offline audit of source identity, saved score arithmetic and best-proof selection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from proof_eval.evidence.audit import _evaluation, _implementation, _require
from proof_eval.evidence.io import digest, read, write_json
from proof_eval.harness.session import code_identity
from proof_eval.paths import ROOT
from proof_eval.protocol import FIELDS, fingerprint
from proof_eval.providers import agy, claude, deadline_cleanup
from proof_eval.providers.costs import rate_card
from proof_eval.providers.events import parse_events
from proof_eval.providers.monitoring import read_events, verified_stream_stop
from proof_eval.providers.response_usage import audit_usage
from proof_eval.providers.retries import owned_client_eof, retryable_transport_failure
from proof_eval.providers.signal_scope import audit_generation as audit_signal_scope
from proof_eval.providers.spending import native_cost_stop
from proof_eval.verification.feedback import all_versions_passed

from .archived_schedules import attempt_condition, validate_archive
from .attempts import attempt_folders
from .carryover import audit_deadline
from .incumbents import select_seed
from .proof_history import SUPPORTED_VERSIONS as PROOF_HISTORY_VERSIONS
from .proof_history import scope_for as proof_history_scope
from .proof_history_audit import audit_proof_history
from .tracking import attempt_cost
from .tracking_audit import audit_attempts
from .usage_policy import resolve_usage_policy
from .web_audit import audit_web


def _audit_responses_terminal(folder: Path, generation: dict, request: dict) -> None:
    """Recheck native counters using the request's pinned terminal protocol."""
    events = read_events(folder / "events.jsonl")
    parsed = parse_events(
        events,
        generation["content"],
        0,
        allow_empty_final=request["cli"].get("terminal_schema_version") == 2,
    )
    if generation.get("response_usage_schema_version") is not None:
        parsed = audit_usage(folder, events, request["model"], parsed)
    _require(
        parsed["status"] == "received"
        and parsed["codex_usage"] == generation["codex_usage"],
        "Responses CLI terminal usage changed",
    )
    if "token_usage" in generation:
        _require(
            parsed["token_usage"] == generation["token_usage"],
            "Normalized token usage changed",
        )


def _compatible_rate_card(saved: dict, current: dict) -> bool:
    """Adding an unpriced model changes no historical pricing assumption."""
    return {k: v for k, v in saved.items() if k != "unpriced_models"} == {
        k: v for k, v in current.items() if k != "unpriced_models"
    } and set(saved.get("unpriced_models", [])) <= set(
        current.get("unpriced_models", [])
    )


def _audit_native_ownership(
    folder: Path,
    generation: dict,
    events: list[dict],
    *,
    recorded_folder: Path | None = None,
) -> None:
    """Bind local EOF recovery to host-owned process and event evidence."""
    marker = generation.get("owned_client_eof")
    ownership = generation.get("process_ownership")
    process = (
        read(folder / "process.json") if (folder / "process.json").exists() else {}
    )
    receipt = folder / "process_ownership.json"
    if not (
        marker is not None
        or ownership is not None
        or process.get("native_supervisor")
        or receipt.exists()
    ):
        audit_signal_scope(folder, generation, recorded_folder=recorded_folder)
        return  # Historical and nonlocal executions keep their saved contract.
    _require(
        generation.get("provider") == "lemex-local"
        and process.get("native_supervisor") is True,
        "Native ownership evidence has no local supervised process",
    )
    if ownership is None:
        _require(
            marker is None
            and not receipt.exists()
            and generation.get("status") != "received",
            "Native completion or recovery is missing its ownership receipt",
        )
        if process.get("ownership_schema_version") == 2:
            _require(
                generation.get("host_deadline_cleanup") is not None,
                "Native deadline is missing complete host cleanup evidence",
            )
        deadline_cleanup.audit(folder, generation)
        audit_signal_scope(folder, generation, recorded_folder=recorded_folder)
        return  # An interrupted supervisor never authorizes a retry.
    _require(
        isinstance(ownership, dict) and receipt.exists() and read(receipt) == ownership,
        "Native ownership receipt differs from saved generation",
    )
    if process.get("ownership_schema_version") == 2:
        startup = ownership.get("startup", {})
        _require(
            (folder / "process_ownership_started.json").exists()
            and read(folder / "process_ownership_started.json") == startup
            and startup.get("supervisor") == ownership.get("supervisor")
            and startup.get("native") == ownership.get("native")
            and startup.get("native_exec_gated") is True,
            "Native exec was not gated by durable process identities",
        )
    supervisor = ownership.get("supervisor", {})
    native = ownership.get("native", {})
    cleanup = ownership.get("cleanup", {})
    _require(
        all(isinstance(p, dict) for p in (supervisor, native, cleanup)),
        "Native ownership receipt has malformed process evidence",
    )
    _require(
        ownership.get("schema_version") == 1
        and generation.get("supervisor_returncode") == 0
        and supervisor == {k: process.get(k) for k in ("pid", "start_ticks")}
        and all(
            type(p.get("pid")) is int
            and p["pid"] > 0
            and isinstance(p.get("start_ticks"), str)
            and p["start_ticks"].isdigit()
            for p in (supervisor, native)
        )
        and supervisor["pid"] != native["pid"]
        and ownership.get("native_exited") is True
        and type(ownership.get("native_returncode")) is int
        and ownership["native_returncode"] == generation.get("returncode", 0)
        and cleanup.get("complete") is True
        and cleanup.get("remaining_pids") == [],
        "Native ownership receipt does not prove an exited and reaped client",
    )
    notices = ownership.get("supervisor_signals")
    if notices is not None:
        _require(
            isinstance(notices, list)
            and bool(notices)
            and (folder / "process_signals.json").exists()
            and read(folder / "process_signals.json") == notices
            and all(
                isinstance(n, dict)
                and n.get("signal") in (1, 2, 15)
                and isinstance(n.get("sender"), dict)
                and type(n["sender"].get("pid")) is int
                and type(n.get("sender_uid")) is int
                and type(n.get("code")) is int
                and type(n.get("at_epoch")) in (int, float)
                for n in notices
            ),
            "Native supervisor signal evidence changed",
        )
    audit_signal_scope(folder, generation, recorded_folder=recorded_folder)
    if marker is not None:
        _require(
            owned_client_eof(events)
            and retryable_transport_failure(generation)
            and generation.get("events_errors", [])
            == [e for e in events if e.get("type") in {"error", "turn.failed"}],
            "Owned native EOF has no matching active stream and stopped-process evidence",
        )


def _audit_claude_terminal(folder: Path, generation: dict, request: dict) -> None:
    events = [
        json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()
    ]
    version = generation.get("usage_schema_version", 1)
    parsed = claude.parse_events(
        events,
        generation.get("content", ""),
        generation["returncode"],
        model=request["model"],
        usage_schema_version=version,
    )
    fields = [
        "status",
        "actual_model",
        "session_id",
        "claude_result",
        "claude_usage",
        "token_usage",
        "cli_cost_usd",
        "permission_denials",
    ]
    if version == 2:
        fields += [
            "usage_schema_version",
            "reasoning_usage_reported",
            "cache_write_ttl_reported",
        ]
    for field in fields:
        if field == "status" and generation[field] == "budget_exhausted":
            if generation.get("termination") == "cost_limit":
                _require(
                    native_cost_stop("claude", events, request.get("cost_budget"))
                    and generation["actual_model"] == request["model"],
                    "Claude cost limit has no native stop evidence",
                )
                continue
            end = read(folder.parent / "budget_end.json")
            _require(
                end["exhausted"] is True and parsed[field] != "received",
                "Claude time limit has no supervised stop evidence",
            )
            continue
        _require(
            parsed[field] == generation[field],
            "Claude terminal evidence changed: " + field,
        )


def _audit_agy_terminal(folder: Path, generation: dict, request: dict) -> None:
    events = read_events(
        folder / "events.jsonl",
        allow_partial=generation["status"] == "budget_exhausted",
    )
    if generation.get("requested_model") is not None:
        _require(
            generation["requested_model"]
            == agy.slug(request["model"], request["reasoning_effort"]),
            "Antigravity requested model differs from its frozen configuration",
        )
    parsed = agy.parse_events(
        events,
        generation.get("content", ""),
        generation["returncode"],
        requested_slug=generation.get("requested_model"),
    )
    fields = [
        "status",
        "returncode",
        "requested_model",
        "actual_model",
        "conversation_id",
        "agy_result",
        "agy_usage",
        "token_usage",
        "usage_complete",
        "cache_write_reported",
        "completed_turns",
        "tool_items",
        "tool_item_types",
        "denied_actions",
    ]
    for field in fields:
        if field == "status" and generation[field] == "budget_exhausted":
            if generation.get("termination") == "cost_limit":
                _require(
                    verified_stream_stop(
                        folder, events, request.get("cost_budget"), agy.stream_usage
                    )
                    and generation["host_cost_stop_sha256"]
                    == fingerprint(read(folder / "cost_stop.json"))
                    and generation["actual_model"]
                    in (None, generation["requested_model"]),
                    "Antigravity cost limit has no host stream stop evidence",
                )
                continue
            end = read(folder.parent / "budget_end.json")
            _require(
                end["exhausted"] is True and parsed[field] != "received",
                "Antigravity time limit has no supervised stop evidence",
            )
            continue
        _require(
            parsed[field] == generation[field],
            "Antigravity terminal evidence changed: " + field,
        )


def audit(
    output: Path,
    *,
    code_root: Path | None = None,
    cell_paths: list[Path] | None = None,
    recorded_cells: dict[Path, Path] | None = None,
) -> dict:
    """Audit saved evidence, optionally verifying bytes in its frozen runtime."""
    code_root = Path(code_root) if code_root is not None else ROOT
    config = read(output / "config.json")
    proof_history_enabled = "proof_history_version" in config
    _require(
        (
            type(config["proof_history_version"]) is int
            and config["proof_history_version"] in PROOF_HISTORY_VERSIONS
            and isinstance(config.get("proof_history_run_id"), str)
            and bool(config["proof_history_run_id"])
            if proof_history_enabled
            else "proof_history_run_id" not in config
        ),
        "Unsupported or unconfigured proof history",
    )
    if "usage_policy" in config:
        _require(
            config.get("schema_version") == 8
            and config["usage_policy"]
            == resolve_usage_policy(
                config["usage_policy"],
                config.get("provider", "codex"),
                config.get("budget_tracking"),
            ),
            "Unpinned or invalid usage accounting policy",
        )
    validate_archive(config)
    dataset_path = Path(
        config.get("dataset_path", code_root / "data/benchmark_data_warmup.jsonl")
    )
    _require(
        digest(dataset_path) == config["dataset_sha256"], "Dataset identity changed"
    )
    if "references_sha256" in config:
        _require(
            digest(config["references_path"]) == config["references_sha256"],
            "Reference export identity changed",
        )
    if "cost_estimate_sha256" in config:
        costs = read(output / "cost_estimate.json")
        _require(
            (fingerprint(costs) == config["cost_estimate_sha256"]),
            str("Saved harness evidence is inconsistent at audit line 22"),
        )
        _require(
            (
                costs["rate_card"] == config["rate_card"]
                and _compatible_rate_card(
                    config["rate_card"], rate_card(config.get("provider", "codex"))
                )
            ),
            str("Saved harness evidence is inconsistent at audit line 23"),
        )
        for rel, expected in costs["source_result_sha256"].items():
            _require(
                (digest(code_root / rel) == expected),
                str("Saved harness evidence is inconsistent at audit line 25"),
            )
    for rel, expected in config["code_sha256"].items():
        _implementation(
            rel,
            expected,
            code_root,
            code_root / "results/deterministic/validation/implementation_snapshots",
            str(output),
        )
    for rel, expected in {
        **config["historical_control_sha256"],
        **config["structural_control_sha256"],
        **config.get("score_control_sha256", {}),
    }.items():
        _require((digest(code_root / rel) == expected), str(rel))
    rows = {
        r["name"]: r
        for r in map(
            json.loads,
            Path(
                config.get(
                    "dataset_path", code_root / "data/benchmark_data_warmup.jsonl"
                )
            )
            .read_text()
            .splitlines(),
        )
    }
    refs = {
        r["name"]: r
        for r in map(
            json.loads,
            Path(
                config.get(
                    "references_path",
                    code_root
                    / "results/deterministic/00_reference_baseline/reference_values.jsonl",
                )
            )
            .read_text()
            .splitlines(),
        )
    }
    if config.get("starting_proofs") or proof_history_enabled:
        from proof_eval.evidence.proof_states import guard_proof_states

        from .configuration import BASE, load_inputs

        packs = load_inputs(Path(config.get("base_directory", BASE)))
        _require(
            {name: fingerprint(pack) for name, pack in packs.items()}
            == config["input_sha256"],
            "Frozen starting-state input preparation changed",
        )
        for condition in config["conditions"] if config.get("starting_proofs") else []:
            guard_proof_states(
                config["starting_proofs"],
                packs,
                Path(config["references_path"]),
                condition=tuple(condition),
            )
    outcomes, trials, requests, cells, seen = 0, 0, 0, 0, set()
    cleanup_jobs = set()
    web_counts = {"requests": 0, "retrieved": 0, "errors": 0, "interrupted": 0}
    proof_history_counts = {}
    paths = (
        (output / "cells").glob("*/result.json") if cell_paths is None else cell_paths
    )
    for path in sorted(paths):
        result = read(path)
        _require(
            result.get("first_attempt_condition")
            == config.get("first_attempt_condition"),
            "Result attempt schedule differs from its frozen configuration",
        )
        name = result["name"]
        key = (name, result["model"], result["effort"], result["mode"])
        _require(
            (key not in seen and path.parent.name == fingerprint(key)),
            str("Saved harness evidence is inconsistent at audit line 64"),
        )
        seen.add(key)
        _require(
            (
                name in config["names"]
                and [result["model"], result["effort"]] in config["conditions"]
            ),
            str("Saved harness evidence is inconsistent at audit line 66"),
        )
        _require(
            (result["mode"] == config["mode"]),
            str("Saved harness evidence is inconsistent at audit line 70"),
        )
        inp = read(path.parent / "input.json")
        if config.get("initial_pipeline_version"):
            from .initial_audit import audit_initial

            outcomes += audit_initial(
                config, result, path.parent, rows[name], refs[name]
            )
        audit_deadline(config, result, path.parent)
        counts = audit_web(
            path.parent / "evidence",
            config.get("web_search"),
            deadline_expired=result.get("time_budget", {}).get("exhausted", False),
        )
        for field, count in counts.items():
            web_counts[field] += count
        if config.get("problem_timeout_seconds") is not None:
            budget = result["time_budget"]
            started = read(path.parent / "budget_started.json")
            _require(
                all(budget[k] == v for k, v in started.items())
                and budget["timeout_seconds"] == config["problem_timeout_seconds"]
                and abs(
                    budget["deadline_epoch"]
                    - budget["started_epoch"]
                    - budget["timeout_seconds"]
                )
                < 1e-5,
                "Whole-problem deadline differs from its frozen configuration",
            )
            if budget["exhausted"]:
                end = read(path.parent / "budget_end.json")
                _require(
                    end["exhausted"] is True
                    and end["work_stopped_epoch"] >= budget["deadline_epoch"]
                    and result["stop"]["kind"] == "time_limit",
                    "Deadline outcome has no supervised deadline evidence",
                )
            _require(
                result["generation_status"] != "budget_exhausted"
                or budget["exhausted"]
                or (
                    config.get("budget_tracking") == "cost"
                    and result["generations"][-1].get("termination") == "cost_limit"
                ),
                "A native interruption was mislabeled as a controlled problem deadline",
            )
        elif "problem_timeout_seconds" in config:
            _require(
                config.get("budget_tracking") == "cost"
                and config["generation_timeout"] is None
                and result.get("time_budget") is None
                and not (path.parent / "budget_started.json").exists()
                and not (path.parent / "budget_end.json").exists(),
                "Cost-only run contains a wall-time budget",
            )
        best_code, best_evaluation = (
            inp.get("seed_proof", rows[name]["src"]),
            inp["seed_evaluation"],
        )
        if config.get("incumbent_sources"):
            from .configuration import load_inputs, starting_point

            pack = load_inputs(Path(config["base_directory"]))[name]
            _require(
                fingerprint(pack) == config["input_sha256"][name],
                "Frozen incumbent preparation changed",
            )
            expected_seed = select_seed(
                config,
                pack,
                result["model"],
                result["effort"],
                starting_point(
                    pack,
                    config["mode"],
                    selection_margin_pp=config["selection_margin_pp"],
                ),
            )
            _require(
                (best_code, best_evaluation) == expected_seed,
                "Initial proof differs from its frozen same-condition incumbent",
            )
        outcomes += _evaluation(
            rows[name], refs[name], best_code, best_evaluation, str(key)
        )
        checks = (
            [
                json.loads(line)
                for line in (path.parent / "evidence/checks.jsonl")
                .read_text()
                .splitlines()
            ]
            if (path.parent / "evidence/checks.jsonl").exists()
            else []
        )
        versions = [v for spec in rows[name]["version_info"] for v in spec]
        cell_history_scope = None
        if proof_history_enabled:
            cell_history_scope = proof_history_scope(
                config, packs[name], result["model"], result["effort"]
            )
            counts = audit_proof_history(
                path.parent / "evidence",
                scope=cell_history_scope,
                seed_code=best_code,
                seed_evaluation=best_evaluation,
                versions=versions,
                checks=checks,
                row=rows[name],
                require_rpc=True,
            )
            for field, value in counts.items():
                proof_history_counts[field] = proof_history_counts.get(field, 0) + value
        else:
            _require(
                not any("history" in check for check in checks)
                and not (path.parent / "evidence/history_queries.jsonl").exists(),
                "Unconfigured proof history evidence",
            )
        valid_code = None
        valid_evaluation = None
        best_at = {0: (best_code, best_evaluation)}
        for i, c in enumerate(checks, 1):
            _require(
                (c["number"] == i),
                str("Saved harness evidence is inconsistent at audit line 94"),
            )
            ev = c["evaluation"]
            if ev["status"] == "passed":
                outcomes += _evaluation(
                    rows[name], refs[name], c["code"], ev, str(key) + f"/check{i}"
                )
            elif ev["status"] in ("failed", "invalid"):
                _require(
                    (all(ev["scores"][f] == 0 for f in FIELDS)),
                    str("Saved harness evidence is inconsistent at audit line 101"),
                )
            valid = all_versions_passed(ev, versions)
            _require(
                (c["all_versions_passed"] == valid),
                str("Saved harness evidence is inconsistent at audit line 103"),
            )
            previous = best_evaluation["scores"]["combined_pct"]
            accepted = (
                valid
                and ev["scores"]["combined_pct"] is not None
                and ev["scores"]["combined_pct"]
                > previous + config["selection_margin_pp"]
            )
            _require(
                (c["accepted"] == accepted and c["previous_best_score"] == previous),
                str("Saved harness evidence is inconsistent at audit line 111"),
            )
            if valid and valid_code is None:
                valid_code, valid_evaluation = c["code"], ev
            if config["mode"] == "correctness" and valid_code is not None:
                from proof_eval.verification.metrics import validate_candidate

                _require(
                    (
                        validate_candidate(rows[name], c["code"])[0]
                        == validate_candidate(rows[name], valid_code)[0]
                    ),
                    str("Saved harness evidence is inconsistent at audit line 117"),
                )
            if accepted:
                best_code, best_evaluation = c["code"], ev
            best_at[i] = (best_code, best_evaluation)
            trials += 1
        _require(
            (
                result["selected_proof"] == best_code
                and result["selected_evaluation"] == best_evaluation
            ),
            str("Saved harness evidence is inconsistent at audit line 125"),
        )
        _require(
            (
                result["first_valid_proof"] == valid_code
                and result["first_valid_evaluation"] == valid_evaluation
            ),
            str("Saved harness evidence is inconsistent at audit line 129"),
        )
        _require(
            (result["checks"] == len(checks)),
            str("Saved harness evidence is inconsistent at audit line 133"),
        )
        _require(
            (
                result["agent_tool_checks"]
                == sum(c["origin"] == "agent_tool" for c in checks)
            ),
            str("Saved harness evidence is inconsistent at audit line 134"),
        )
        _require(
            (result["valid_checks"] == sum(c["all_versions_passed"] for c in checks)),
            str("Saved harness evidence is inconsistent at audit line 137"),
        )
        _require(
            (result["improvements"] == sum(c["accepted"] for c in checks)),
            str("Saved harness evidence is inconsistent at audit line 138"),
        )
        if config.get("deterministic_cleanup") and not config.get(
            "initial_pipeline_version"
        ):
            cleanup_calls = (
                [
                    json.loads(line)
                    for line in (path.parent / "evidence/deterministic.jsonl")
                    .read_text()
                    .splitlines()
                ]
                if (path.parent / "evidence/deterministic.jsonl").exists()
                else []
            )
            _require(
                (result["deterministic_calls"] == len(cleanup_calls)),
                str("Saved harness evidence is inconsistent at audit line 146"),
            )
            initial_calls = [
                c for c in cleanup_calls if c["origin"] == "initial_harness"
            ]
            if config.get("proof_theory_cleanup_version"):
                from proof_eval.optimization.cleanup import (
                    METHODS,
                    PROOF_THEORY_METHODS,
                )

                _require(
                    config["proof_theory_cleanup_version"] == 1
                    and config["initial_deterministic_methods"]
                    == list(PROOF_THEORY_METHODS)
                    and config["deterministic_methods"]
                    == list(METHODS + PROOF_THEORY_METHODS)
                    and (
                        len(initial_calls) == 1
                        or (
                            not initial_calls
                            and result.get("time_budget", {}).get("exhausted") is True
                            and not result["generations"]
                            and result.get("initial_cleanup_status")
                            in ("skipped_time_limit", "interrupted_time_limit")
                        )
                    ),
                    "Extended cleanup has no unique pinned beginning pass",
                )
                if initial_calls:
                    initial_call = initial_calls[0]
                    _require(
                        initial_call["number"] == 1
                        and checks[initial_call["input_check"] - 1]["code"]
                        == inp["seed_proof"]
                        and result["initial_cleanup_status"] == initial_call["status"],
                        "Beginning cleanup did not start from the frozen seed",
                    )
                first_attempt_path = path.parent / "attempt_00/attempt.json"
                if first_attempt_path.exists():
                    first_attempt = read(first_attempt_path)
                    _require(
                        initial_call["output_check"] is not None
                        and initial_call["output_check"]
                        == first_attempt["check_start"],
                        "Beginning cleanup occurred after model search started",
                    )
                else:
                    _require(
                        not result["generations"], "Missing first attempt boundary"
                    )
            else:
                _require(not initial_calls, "Unconfigured beginning cleanup")
            _require(
                (
                    result["deterministic_tool_calls"]
                    == sum(c["origin"] == "agent_tool" for c in cleanup_calls)
                ),
                str("Saved harness evidence is inconsistent at audit line 147"),
            )
            _require(
                (
                    len([c for c in cleanup_calls if c["origin"] == "final_harness"])
                    == (
                        0
                        if result.get("final_cleanup_status")
                        in ("skipped_time_limit", "interrupted_time_limit")
                        else 1
                    )
                ),
                str("Saved harness evidence is inconsistent at audit line 150"),
            )
            _require(
                (
                    result["seed_proof"] == inp["seed_proof"]
                    and result["seed_evaluation"] == inp["seed_evaluation"]
                ),
                str("Saved harness evidence is inconsistent at audit line 153"),
            )
            valid_proposals = {
                c["code_sha256"]
                for c in checks
                if c["origin"] in ("agent_tool", "deterministic_input", "final_harness")
                and c["all_versions_passed"]
                and not c["duplicate"]
                and c["code_sha256"] != code_identity(rows[name], inp["seed_proof"])
            }
            covered = valid_proposals & {
                c["input_code_sha256"]
                for c in cleanup_calls
                if c["origin"] == "agent_tool" and c["status"] != "skipped_invalid"
            }
            _require(
                (result["valid_changed_proposals"] == len(valid_proposals)),
                str("Saved harness evidence is inconsistent at audit line 170"),
            )
            _require(
                (result["proposals_with_tool_cleanup"] == len(covered)),
                str("Saved harness evidence is inconsistent at audit line 171"),
            )
            _require(
                (
                    result["deterministic_tool_coverage_pct"]
                    == (
                        100 * len(covered) / len(valid_proposals)
                        if valid_proposals
                        else None
                    )
                ),
                str("Saved harness evidence is inconsistent at audit line 172"),
            )
            _require(
                (
                    result["incomplete_cleanups"]
                    == sum(
                        c["status"] not in ("complete", "skipped_invalid")
                        for c in cleanup_calls
                    )
                ),
                str("Saved harness evidence is inconsistent at audit line 175"),
            )
            if result["score_control_score"] is not None:
                _require(
                    (
                        abs(
                            result["gain_over_score_control_pp"]
                            - (
                                best_evaluation["scores"]["combined_pct"]
                                - result["score_control_score"]
                            )
                        )
                        < 1e-9
                    ),
                    str("Saved harness evidence is inconsistent at audit line 180"),
                )
            else:
                _require(
                    (result["gain_over_score_control_pp"] is None),
                    str("Saved harness evidence is inconsistent at audit line 191"),
                )
            for i, c in enumerate(cleanup_calls, 1):
                _require(
                    (c["number"] == i),
                    str("Saved harness evidence is inconsistent at audit line 193"),
                )
                before = checks[c["input_check"] - 1]
                _require(
                    (before["code_sha256"] == c["input_code_sha256"]),
                    str("Saved harness evidence is inconsistent at audit line 195"),
                )
                if c["status"] == "skipped_invalid":
                    _require(
                        (
                            not before["all_versions_passed"]
                            and c["output_check"] is None
                        ),
                        str("Saved harness evidence is inconsistent at audit line 197"),
                    )
                    continue
                job_folder = Path(c["job_path"])
                _require(
                    (
                        job_folder.resolve().is_relative_to(
                            Path(config["deterministic_jobs"]).resolve()
                        )
                    ),
                    str("Saved harness evidence is inconsistent at audit line 202"),
                )
                _require(
                    (digest(job_folder / "result.json") == c["job_result_sha256"]),
                    str("Saved harness evidence is inconsistent at audit line 205"),
                )
                job = read(job_folder / "result.json")
                after = checks[c["output_check"] - 1]
                _require(
                    (
                        after["code"] == job["proof"]
                        and after["evaluation"] == job["evaluation"]
                    ),
                    str("Saved harness evidence is inconsistent at audit line 208"),
                )
                _require(
                    (c["status"] == job["status"] and c["counters"] == job["counters"]),
                    str("Saved harness evidence is inconsistent at audit line 212"),
                )
                _require(
                    (
                        code_identity(rows[name], job["input_proof"])
                        == c["input_code_sha256"]
                    ),
                    str("Saved harness evidence is inconsistent at audit line 213"),
                )
                _require(
                    (before["all_versions_passed"] and after["all_versions_passed"]),
                    str("Saved harness evidence is inconsistent at audit line 217"),
                )
                if str(job_folder) not in cleanup_jobs:
                    spec = read(job_folder / "job_config.json")
                    _require(
                        (job["job_config_sha256"] == fingerprint(spec)),
                        str("Saved harness evidence is inconsistent at audit line 220"),
                    )
                    _require(
                        (
                            spec["methods"]
                            == config[
                                (
                                    "initial_deterministic_methods"
                                    if c["origin"] == "initial_harness"
                                    else "deterministic_methods"
                                )
                            ]
                            and spec["budget"] == config["deterministic_budget"]
                        ),
                        str("Saved harness evidence is inconsistent at audit line 221"),
                    )
                    for relative, expected in job["stage_result_sha256"].items():
                        _require(
                            (digest(job_folder / relative) == expected),
                            str(
                                "Saved harness evidence is inconsistent at audit line 226"
                            ),
                        )
                    code = job["input_proof"]
                    for stage in job["stages"]:
                        outcomes += _evaluation(
                            rows[name],
                            refs[name],
                            code,
                            stage["initial"],
                            "cleanup initial",
                        )
                        outcomes += _evaluation(
                            rows[name],
                            refs[name],
                            stage["proof"],
                            stage["final"],
                            "cleanup final",
                        )
                        _require(
                            (
                                stage["final"]["scores"]["combined_pct"]
                                >= stage["initial"]["scores"]["combined_pct"]
                            ),
                            str(
                                "Saved harness evidence is inconsistent at audit line 243"
                            ),
                        )
                        code = stage["proof"]
                    _require(
                        (code == job["proof"]),
                        str("Saved harness evidence is inconsistent at audit line 248"),
                    )
                    cleanup_jobs.add(str(job_folder))
                if c["origin"] == "final_harness":
                    prior_code, prior_eval = best_at[c["input_check"] - 1]
                    _require(
                        (
                            result["before_final_cleanup"]
                            == {
                                "proof": prior_code,
                                "evaluation": prior_eval,
                            }
                        ),
                        str("Saved harness evidence is inconsistent at audit line 252"),
                    )
            _require(
                (
                    abs(
                        result["final_cleanup_gain_pp"]
                        - (
                            best_evaluation["scores"]["combined_pct"]
                            - result["before_final_cleanup"]["evaluation"]["scores"][
                                "combined_pct"
                            ]
                        )
                    )
                    < 1e-9
                ),
                str("Saved harness evidence is inconsistent at audit line 256"),
            )
            _require(
                (result["final_cleanup_gain_pp"] >= 0),
                str("Saved harness evidence is inconsistent at audit line 268"),
            )
            if config["mode"] == "score_edges":
                _require(
                    (result["deterministic_tool_calls"] == 0),
                    str("Saved harness evidence is inconsistent at audit line 270"),
                )
        if result["historical_score"] is not None:
            _require(
                (
                    abs(
                        result["gain_over_historical_pp"]
                        - (
                            best_evaluation["scores"]["combined_pct"]
                            - result["historical_score"]
                        )
                    )
                    < 1e-9
                ),
                str("Saved harness evidence is inconsistent at audit line 272"),
            )
        else:
            _require(
                (result["gain_over_historical_pp"] is None),
                str("Saved harness evidence is inconsistent at audit line 283"),
            )
        if result["structural_control_score"] is not None:
            _require(
                (
                    abs(
                        result["gain_over_structural_control_pp"]
                        - (
                            best_evaluation["scores"]["combined_pct"]
                            - result["structural_control_score"]
                        )
                    )
                    < 1e-9
                ),
                str("Saved harness evidence is inconsistent at audit line 285"),
            )
        outcomes += _evaluation(
            rows[name], refs[name], best_code, best_evaluation, str(key) + "/selected"
        )
        cell_generations = []
        for folder in attempt_folders(path.parent):
            gen = read(folder / "generation.json")
            cell_generations.append(gen)
            if not (folder / "request.json").exists():
                _require(
                    config.get("attempt_evidence_version")
                    and result.get("time_budget", {}).get("exhausted", False)
                    and gen.get("dispatch_status") == "not_dispatched"
                    and gen["status"] == "budget_exhausted"
                    and gen.get("termination") == "problem_deadline"
                    and not (folder / "request_started.json").exists()
                    and not (folder / "process.json").exists(),
                    "Missing request has no host evidence of a deadline before dispatch",
                )
                continue
            req = read(folder / "request.json")
            number = int(folder.name.removeprefix("attempt_"))
            expected_model, expected_effort = attempt_condition(
                config, result["model"], result["effort"], number
            )
            _require(
                (req["model"], req["reasoning_effort"], req["mode"])
                == (expected_model, expected_effort, result["mode"]),
                "Request model/effort differs from the frozen attempt schedule",
            )
            _require(
                (req["tool_instructions"] == config["tool_instructions"]),
                str("Saved harness evidence is inconsistent at audit line 304"),
            )
            _require(
                req.get("provider", "codex") == config.get("provider", "codex"),
                "Request provider differs from its frozen configuration",
            )
            _require(req["cli"] == config["cli"], "Request CLI identity changed")
            _require(
                req.get("tool_context", {}).get("web_search")
                == config.get("web_search"),
                "Request web tools differ from the frozen condition",
            )
            if config.get("transport_recovery_version") and config.get(
                "provider", "codex"
            ) in ("codex", "lemex"):
                events = []
                event_path = folder / "events.jsonl"
                _require(
                    event_path.exists()
                    or (
                        result.get("time_budget", {}).get("exhausted", False)
                        and not (folder / "request_started.json").exists()
                    ),
                    "Native event evidence is missing after dispatch",
                )
                events = (
                    read_events(
                        event_path,
                        allow_partial=result.get("time_budget", {}).get(
                            "exhausted", False
                        ),
                    )
                    if event_path.exists()
                    else []
                )
                original = (recorded_cells or {}).get(path.parent)
                _audit_native_ownership(
                    folder,
                    gen,
                    events,
                    recorded_folder=original / folder.name if original else None,
                )
                parsed = parse_events(
                    events,
                    gen.get("content", ""),
                    gen.get("returncode", 0),
                    allow_empty_final=req["cli"].get("terminal_schema_version") == 2,
                )
                if (
                    req["cli"].get("response_usage_schema_version") in (1, 2)
                    and gen.get("status") == "received"
                ):
                    _require(
                        gen.get("response_usage_schema_version")
                        == req["cli"]["response_usage_schema_version"],
                        "Successful native response is missing request usage evidence",
                    )
                if gen.get("response_usage_schema_version") is not None:
                    _require(
                        gen["response_usage_schema_version"] in (1, 2)
                        and gen["response_usage_schema_version"]
                        == req["cli"].get("response_usage_schema_version"),
                        "Unpinned native response usage version",
                    )
                    parsed = audit_usage(folder, events, req["model"], parsed)
                    for field in (
                        "response_usage_schema_version",
                        "response_usage_sha256",
                        "token_usage",
                        "structurally_valid",
                        "estimated_usage_complete",
                        "estimated_token_usage",
                        "usage_estimates",
                    ):
                        _require(
                            parsed.get(field) == gen.get(field),
                            "Native response usage changed: " + field,
                        )
                for field in (
                    "events_errors",
                    "recovered_transport_errors",
                    "usage_complete",
                    "usage_incomplete_reason",
                ):
                    _require(
                        parsed.get(field) == gen.get(field),
                        "Native retry evidence changed: " + field,
                    )
            _require(
                (req["messages"][0] == inp["messages"][0]),
                str("Saved harness evidence is inconsistent at audit line 305"),
            )
            _require(
                (req["max_output_tokens"] is None and req["max_attempts"] is None),
                str("Saved harness evidence is inconsistent at audit line 306"),
            )
            _require(
                (
                    config.get("attempt_evidence_version")
                    or req["timeout"] == config["generation_timeout"]
                ),
                str("Saved harness evidence is inconsistent at audit line 307"),
            )
            if folder.name == "attempt_00":
                _require(
                    (req["messages"] == inp["messages"]),
                    str("Saved harness evidence is inconsistent at audit line 309"),
                )
            if (
                config.get("provider") == "claude"
                and gen.get("usage_schema_version") == 2
                and gen["status"] != "received"
            ):
                _audit_claude_terminal(folder, gen, req)
            if (
                config.get("provider") == "agy"
                and gen["status"] != "received"
                and "agy_usage" in gen
            ):
                _audit_agy_terminal(folder, gen, req)
            if gen["status"] == "received":
                _require(
                    (
                        (folder / "workspace/final.txt").read_text().strip()
                        == gen["content"].strip()
                    ),
                    str("Saved harness evidence is inconsistent at audit line 311"),
                )
                if "cost_assumptions" in config:
                    if config.get("provider", "codex") == "claude":
                        _audit_claude_terminal(folder, gen, req)
                    elif config.get("provider", "codex") == "agy":
                        _audit_agy_terminal(folder, gen, req)
                    else:
                        _audit_responses_terminal(folder, gen, req)
            if config["mode"] == "correctness":
                for line in (folder / "events.jsonl").read_text().splitlines():
                    event = json.loads(line)
                    item = event.get("item", {})
                    if (
                        event.get("type") != "item.completed"
                        or item.get("type") != "command_execution"
                    ):
                        continue
                    text = item.get("aggregated_output", "")
                    _require(
                        ('"kind": "lean_score_feedback"' not in text),
                        str("Saved harness evidence is inconsistent at audit line 333"),
                    )
            requests += 1
        _require(
            (
                cell_generations == result["generations"]
                and (
                    cell_generations
                    or result.get("time_budget", {}).get("exhausted")
                    or result["stop"]["kind"] == "cost_reserve"
                )
            ),
            str("Saved harness evidence is inconsistent at audit line 335"),
        )
        if "cost_assumptions" in config:
            _require(
                (
                    result["cost"]
                    == attempt_cost(
                        config,
                        result["model"],
                        result["effort"],
                        cell_generations,
                        name=result["name"],
                        final=True,
                    )
                ),
                str("Saved harness evidence is inconsistent at audit line 337"),
            )
        audit_attempts(
            config,
            result,
            path.parent,
            checks,
            best_at,
            rows[name],
            proof_history_scope=cell_history_scope,
        )
        cells += 1
    return {
        "status": "passed",
        "completed_cells": cells,
        "saved_checks": trials,
        "checked_version_outcomes": outcomes,
        "requests": requests,
        "unique_cleanup_jobs": len(cleanup_jobs),
        **({"web_tools": web_counts} if config.get("web_search") is not None else {}),
        **({"proof_history": proof_history_counts} if proof_history_enabled else {}),
        "scope": "Saved evidence and arithmetic; no new Lean or model calls.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = audit(args.output.resolve())
    write_json(args.output / "audit.json", result)
    print(json.dumps(result))
