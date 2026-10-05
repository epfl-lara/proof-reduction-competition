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
from proof_eval.providers import claude
from proof_eval.providers.costs import CostConfig, generations_cost, rate_card
from proof_eval.providers.events import parse_events
from proof_eval.verification.feedback import all_versions_passed


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
        _require(
            parsed[field] == generation[field],
            "Claude terminal evidence changed: " + field,
        )


def audit(output: Path) -> dict:
    config = read(output / "config.json")
    dataset_path = Path(
        config.get("dataset_path", ROOT / "data/benchmark_data_warmup.jsonl")
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
                costs["rate_card"]
                == config["rate_card"]
                == rate_card(config.get("provider", "codex"))
            ),
            str("Saved harness evidence is inconsistent at audit line 23"),
        )
        for rel, expected in costs["source_result_sha256"].items():
            _require(
                (digest(ROOT / rel) == expected),
                str("Saved harness evidence is inconsistent at audit line 25"),
            )
    for rel, expected in config["code_sha256"].items():
        _implementation(
            rel,
            expected,
            ROOT,
            ROOT / "results/deterministic/validation/implementation_snapshots",
            str(output),
        )
    for rel, expected in {
        **config["historical_control_sha256"],
        **config["structural_control_sha256"],
        **config.get("score_control_sha256", {}),
    }.items():
        _require((digest(ROOT / rel) == expected), str(rel))
    rows = {
        r["name"]: r
        for r in map(
            json.loads,
            Path(config.get("dataset_path", ROOT / "data/benchmark_data_warmup.jsonl"))
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
                    ROOT
                    / "results/deterministic/00_reference_baseline/reference_values.jsonl",
                )
            )
            .read_text()
            .splitlines(),
        )
    }
    outcomes, trials, requests, cells, seen = 0, 0, 0, 0, set()
    cleanup_jobs = set()
    for path in sorted((output / "cells").glob("*/result.json")):
        result = read(path)
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
        best_code, best_evaluation = (
            inp.get("seed_proof", rows[name]["src"]),
            inp["seed_evaluation"],
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
        if config.get("deterministic_cleanup"):
            cleanup_calls = [
                json.loads(line)
                for line in (path.parent / "evidence/deterministic.jsonl")
                .read_text()
                .splitlines()
            ]
            _require(
                (result["deterministic_calls"] == len(cleanup_calls)),
                str("Saved harness evidence is inconsistent at audit line 146"),
            )
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
                    == 1
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
                            spec["methods"] == config["deterministic_methods"]
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
        for folder in sorted(path.parent.glob("attempt_*")):
            req = read(folder / "request.json")
            gen = read(folder / "generation.json")
            cell_generations.append(gen)
            _require(
                ((req["model"], req["reasoning_effort"], req["mode"]) == key[1:]),
                str("Saved harness evidence is inconsistent at audit line 303"),
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
                (req["messages"][0] == inp["messages"][0]),
                str("Saved harness evidence is inconsistent at audit line 305"),
            )
            _require(
                (req["max_output_tokens"] is None and req["max_attempts"] is None),
                str("Saved harness evidence is inconsistent at audit line 306"),
            )
            _require(
                (req["timeout"] == config["generation_timeout"]),
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
                    else:
                        events = [
                            json.loads(line)
                            for line in (folder / "events.jsonl")
                            .read_text()
                            .splitlines()
                        ]
                        parsed = parse_events(events, gen["content"], 0)
                        _require(
                            parsed["status"] == "received"
                            and parsed["codex_usage"] == gen["codex_usage"],
                            "Responses CLI terminal usage changed",
                        )
                        if "token_usage" in gen:
                            _require(
                                parsed["token_usage"] == gen["token_usage"],
                                "Normalized token usage changed",
                            )
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
            (cell_generations == result["generations"] and cell_generations),
            str("Saved harness evidence is inconsistent at audit line 335"),
        )
        if "cost_assumptions" in config:
            _require(
                (
                    result["cost"]
                    == generations_cost(
                        CostConfig(
                            result["model"],
                            result["effort"],
                            **config["cost_assumptions"],
                        ),
                        cell_generations,
                        budget_usd=config["budget_usd_per_problem"],
                    )
                ),
                str("Saved harness evidence is inconsistent at audit line 337"),
            )
        cells += 1
    return {
        "status": "passed",
        "completed_cells": cells,
        "saved_checks": trials,
        "checked_version_outcomes": outcomes,
        "requests": requests,
        "unique_cleanup_jobs": len(cleanup_jobs),
        "scope": "Saved evidence and arithmetic; no new Lean or model calls.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = audit(args.output.resolve())
    write_json(args.output / "audit.json", result)
    print(json.dumps(result))
