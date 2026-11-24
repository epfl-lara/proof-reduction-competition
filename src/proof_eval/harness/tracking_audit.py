"""Audit new attempt boundaries and budget admission without executing snapshots."""

from __future__ import annotations

import json
import math
from pathlib import Path

from proof_eval.evidence.audit import _require
from proof_eval.evidence.io import fingerprint, read
from proof_eval.protocol import code_identity
from proof_eval.providers import agy
from proof_eval.providers.costs import CostConfig
from proof_eval.providers.monitoring import read_events, verified_stream_stop
from proof_eval.providers.retries import recovery_count
from proof_eval.providers.spending import native_cost_guard, native_cost_stop

from .archived_schedules import attempt_condition
from .attempts import attempt_folders
from .prompts import budget_suffix
from .proof_history_audit import audit_history_attempts
from .restart_history import VERSION
from .restart_history import read_events as read_history_events
from .restart_history_audit import audit_history_attempt
from .tracking import (
    ATTEMPT_EVIDENCE_VERSION,
    CLEANUP_RESERVE_SECONDS,
    attempt_cost,
    stop_decision,
)


def _attempt_budget_suffix(config, result, record, actual, cost, number):
    """Keep prompt construction time distinct from the later dispatch boundary."""
    remaining = record.get(
        "prompt_time_remaining_seconds", record["time_remaining_seconds"]
    )
    expected = budget_suffix(config, result.get("time_budget"), cost, remaining, number)
    legacy = (
        "prompt_time_remaining_seconds" not in record
        and config["code_sha256"].get("src/proof_eval/harness/attempts.py")
        == "f474f7dfa22797406047b6eb117b3b657e75293b9756aaed33ade210302dbc59"
    )
    if actual != expected and legacy and result.get("time_budget") is not None:
        # This exact producer refreshed admission after rendering the prompt.
        # Recover only its displayed numeric interval; every other suffix byte,
        # the request timeout, original clock and native closure stay audited.
        template = budget_suffix(config, result["time_budget"], cost, 0.0, number)
        marker = "(0 seconds remaining)"
        if marker in template:
            prefix, suffix = template.split(marker, 1)
            ending = " seconds remaining)" + suffix
            _require(
                actual.startswith(prefix + "(") and actual.endswith(ending),
                "Attempt changed the host budget instructions",
            )
            text = actual[len(prefix) + 1 : -len(ending)]
            try:
                remaining = float(text)
            except ValueError:
                raise ValueError("Attempt prompt has an invalid remaining interval") from None
            expected = budget_suffix(config, result["time_budget"], cost, remaining, number)
    if remaining is not None:
        _require(
            isinstance(remaining, (int, float))
            and not isinstance(remaining, bool)
            and math.isfinite(remaining)
            and 0 < remaining <= result["time_budget"]["timeout_seconds"],
            "Prompt time is outside its original problem window",
        )
        admitted = record["time_remaining_seconds"]
        _require(
            admitted <= remaining + 1e-6
            or legacy and float(f"{admitted:g}") <= remaining,
            "Prompt construction moved after the recorded admission",
        )
    return expected


def audit_attempts(
    config: dict,
    result: dict,
    folder: Path,
    checks: list,
    best_at: dict,
    row: dict,
    *,
    proof_history_scope: dict | None = None,
) -> None:
    if not config.get("attempt_evidence_version"):
        return
    _require(
        config["attempt_evidence_version"] == ATTEMPT_EVIDENCE_VERSION,
        "Unsupported attempt evidence version",
    )
    folders = attempt_folders(folder)
    records = [read(path / "attempt.json") for path in folders]
    audit_history_attempts(
        config, result, folder, records, checks, scope=proof_history_scope
    )
    _require(
        result.get("attempts") == records
        and len(records) == len(result["generations"]),
        "Attempt boundary records differ from the result",
    )
    tracking = config.get("budget_tracking")
    if config["mode"] == "score_edges":
        _require(
            len(records)
            <= (config["max_budget_restarts"] + 1 if tracking else 1)
            + config.get("max_transport_restarts", 0),
            "Attempt count exceeds the configured restart policy",
        )
    previous_end = 0
    if config.get("initial_pipeline_version") and records:
        previous_end = read(folder / "initial_phase.json")["check_end"]
    if config.get("proof_theory_cleanup_version") and records:
        beginning = [
            json.loads(line)
            for line in (folder / "evidence/deterministic.jsonl")
            .read_text()
            .splitlines()
            if json.loads(line)["origin"] == "initial_harness"
        ]
        _require(len(beginning) == 1, "Missing unique beginning cleanup boundary")
        previous_end = beginning[0]["output_check"]
    history_enabled = config.get("restart_history_version") is not None
    history_events = read_history_events(folder / "evidence")
    _require(
        (
            config.get("restart_history_version") == VERSION
            if history_enabled
            else not history_events
        ),
        "Unsupported or unconfigured restart history",
    )
    previous_event_end = 0
    for number, (attempt, record, generation) in enumerate(
        zip(folders, records, result["generations"])
    ):
        _require(
            attempt.name == f"attempt_{number:02d}" and record["number"] == number,
            "Attempt numbering is not consecutive",
        )
        start, end = record["check_start"], record["check_end"]
        _require(
            record["status"] == "terminal"
            and start == previous_end
            and start <= end <= len(checks),
            "Attempt check boundaries are inconsistent",
        )
        previous_end = end
        _require(
            (record["incumbent_proof"], record["incumbent_evaluation"])
            == best_at[start],
            "Attempt incumbent differs from the best verified proof at admission",
        )
        _require(
            record["incumbent_sha256"] == code_identity(row, record["incumbent_proof"]),
            "Attempt incumbent identity changed",
        )
        _require(
            record["finish_cleared"] is True,
            "Previous attempt finish state was not cleared",
        )
        request = (
            read(attempt / "request.json")
            if (attempt / "request.json").exists()
            else {
                "messages": record["messages"],
                "timeout": record["generation_timeout_seconds"],
                "cost_budget": record["cost_budget"],
            }
        )
        messages = request["messages"]
        scheduled_model, scheduled_effort = attempt_condition(
            config, result["model"], result["effort"], number
        )
        if config.get("first_attempt_condition") is not None:
            _require(
                (record.get("model"), record.get("effort"))
                == (scheduled_model, scheduled_effort),
                "Attempt boundary model/effort differs from the frozen schedule",
            )
        _require(
            [message["role"] for message in messages] == ["system", "user"],
            "Restart leaked conversation history",
        )
        _require(
            messages == record["messages"]
            and fingerprint(messages) == record["messages_sha256"],
            "Attempt prompt differs from its host boundary record",
        )
        prefix = "Optimize this declaration using the supplied tools.\n"
        _require(
            messages[1]["content"].startswith(prefix),
            "Attempt has no fresh incumbent context",
        )
        payload, end_of_payload = json.JSONDecoder().raw_decode(
            messages[1]["content"][len(prefix) :]
        )
        _require(
            payload["incumbent_declaration"] == record["incumbent_proof"]
            and payload["incumbent_scores"] == record["incumbent_evaluation"]["scores"],
            "Restart prompt does not match its verified incumbent",
        )
        previous_event_end = audit_history_attempt(
            config,
            result,
            record,
            payload,
            checks,
            number,
            previous_event_end,
            history_events,
        )
        if number:
            first_messages = read(folders[0] / "request.json")["messages"]
            first_payload, _ = json.JSONDecoder().raw_decode(
                first_messages[1]["content"][len(prefix) :]
            )
            _require(
                {
                    key: value
                    for key, value in payload.items()
                    if key
                    not in (
                        "incumbent_declaration",
                        "incumbent_scores",
                        "restart_history",
                        "proof_history",
                    )
                }
                == {
                    key: value
                    for key, value in first_payload.items()
                    if key
                    not in (
                        "incumbent_declaration",
                        "incumbent_scores",
                        "restart_history",
                        "proof_history",
                    )
                },
                "Restart changed the fixed theorem context or denominators",
            )
            previous = result["generations"][number - 1]
            permitted = stop_decision(
                config,
                previous,
                attempt_cost(
                    config,
                    result["model"],
                    result["effort"],
                    result["generations"][:number],
                    name=result["name"],
                ),
                unavailable=any(
                    check["evaluation"]["status"] == "incomplete"
                    for check in checks[:start]
                ),
                round_number=number - 1,
                time_remaining=(
                    record["deadline_epoch"] - record["admitted_epoch"]
                    if record["deadline_epoch"] is not None
                    else None
                ),
                transport_restarts_used=recovery_count(result["generations"][:number]),
            )
            _require(
                permitted is None,
                "A failed or indeterminate request was resampled outside the recovery policy",
            )
            _require(
                not any(
                    check["evaluation"]["status"] == "incomplete"
                    for check in checks[:start]
                ),
                "A request restarted after unavailable host verification",
            )
            if record["deadline_epoch"] is not None:
                _require(
                    record["admitted_epoch"]
                    < record["deadline_epoch"]
                    - config.get("cleanup_reserve_seconds", CLEANUP_RESERVE_SECONDS),
                    "A request restarted inside the cleanup reserve",
                )
        before = attempt_cost(
            config,
            result["model"],
            result["effort"],
            result["generations"][:number],
            name=result["name"],
        )
        after = attempt_cost(
            config,
            result["model"],
            result["effort"],
            result["generations"][: number + 1],
            name=result["name"],
        )
        actual_suffix = messages[1]["content"][len(prefix) + end_of_payload :]
        _require(
            actual_suffix
            == _attempt_budget_suffix(config, result, record, actual_suffix, before, number),
            "Attempt prompt contains history or changed budget instructions",
        )
        _require(
            record["cost_before"] == before and record["cost_after"] == after,
            "Cumulative attempt spending changed",
        )
        _require(
            record["generation_sha256"] == fingerprint(generation)
            and record["generation_status"] == generation["status"],
            "Attempt terminal response changed",
        )
        _require(
            record["ended_epoch"] >= record["started_epoch"],
            "Attempt time moved backwards",
        )
        timeout = record["generation_timeout_seconds"]
        if config.get("problem_timeout_seconds") is None:
            _require(
                tracking == "cost"
                and timeout is None
                and request["timeout"] is None
                and config["generation_timeout"] is None
                and record["deadline_epoch"] is None
                and record["time_remaining_seconds"] is None
                and result.get("time_budget") is None
                and record["admitted_epoch"] <= record["started_epoch"],
                "Cost-only attempt acquired a time limit or invalid admission time",
            )
        else:
            _audit_attempt_time(config, result, record, request)
        guard = None
        if tracking == "cost":
            total = before["total_usd"]
            _require(
                total is not None and total < config["budget_usd_per_problem"] - 1e-12,
                "Attempt started without known remaining spending",
            )
            guard = native_cost_guard(
                config["provider"],
                CostConfig(
                    scheduled_model, scheduled_effort, **config["cost_assumptions"]
                ),
                config["budget_usd_per_problem"] - total,
                version=config.get("native_cost_guard_version", 1),
            )
        _require(
            record["cost_budget"] == guard and request.get("cost_budget") == guard,
            "Native cost guard differs from the remaining problem budget",
        )
        if config.get("cost_assumptions", {}).get("service_tier") == "fast":
            command = read(attempt / "command.json")["argv"]
            _require(
                config.get("provider") == "codex"
                and request.get("service_tier") == "fast"
                and 'service_tier="fast"' in command,
                "Fast request tier differs from the frozen pricing configuration",
            )
        if generation.get("termination") == "cost_limit":
            events = read_events(attempt / "events.jsonl", allow_partial=True)
            _require(
                tracking == "cost"
                and (
                    verified_stream_stop(attempt, events, guard, agy.stream_usage)
                    if config["provider"] == "agy"
                    else native_cost_stop(config["provider"], events, guard)
                ),
                "Controlled cost stop has no budget evidence",
            )
    _require(
        previous_event_end == len(history_events), "Unbound restart history events"
    )
    if records and not result.get("time_budget", {}).get("exhausted", False):
        stop = read(folder / "search_stop.json")
        _require(
            result["stop"] == stop
            and stop["attempt"] == len(records) - 1
            and stop["at_epoch"] >= records[-1]["ended_epoch"],
            "Result host stop differs from durable search evidence",
        )
        expected = stop_decision(
            config,
            result["generations"][-1],
            records[-1]["cost_after"],
            unavailable=any(
                check["evaluation"]["status"] == "incomplete"
                for check in checks[: records[-1]["check_end"]]
            ),
            round_number=len(records) - 1,
            time_remaining=(
                records[-1]["deadline_epoch"] - stop["at_epoch"]
                if records[-1]["deadline_epoch"] is not None
                else None
            ),
            transport_restarts_used=recovery_count(result["generations"]),
        )
        _require(
            expected is not None
            and (
                stop["kind"] == expected["kind"]
                or (
                    expected["kind"] == "model_final"
                    and stop["kind"] == "agent_decision"
                )
            ),
            "Host stop does not follow the recorded budget policy",
        )
    elif not records and not result.get("time_budget", {}).get("exhausted", False):
        _require(
            tracking == "cost"
            and result["stop"]["kind"] == "cost_reserve"
            and read(folder / "search_stop.json") == result["stop"]
            and (
                attempt_cost(
                    config, result["model"], result["effort"], [], name=result["name"]
                )["total_usd"]
                >= config["budget_usd_per_problem"] - 1e-12
                or native_cost_guard(
                    config["provider"],
                    CostConfig(
                        *attempt_condition(
                            config, result["model"], result["effort"], 0
                        ),
                        **config["cost_assumptions"],
                    ),
                    config["budget_usd_per_problem"],
                ).get("limit_tokens")
                == 0
            ),
            "A search without requests has no budget admission evidence",
        )
    if tracking:
        _require(
            result.get("budget_tracking") == tracking
            and result["budget_outcome"]["stop_kind"] == result["stop"]["kind"]
            and result["budget_outcome"]["hard_cost_cap"] is False,
            "Budget outcome metadata changed",
        )


def _audit_attempt_time(
    config: dict, result: dict, record: dict, request: dict
) -> None:
    timeout = record["generation_timeout_seconds"]
    _require(
        request["timeout"] == timeout
        and 0 < timeout <= config["generation_timeout"]
        and timeout <= record["deadline_epoch"] - record["started_epoch"] + 1,
        "Attempt timeout replenished the problem deadline",
    )
    _require(
        record["deadline_epoch"] == result["time_budget"]["deadline_epoch"],
        "Attempt has a different problem deadline",
    )
    _require(
        0
        < record["time_remaining_seconds"]
        <= record["deadline_epoch"] - record["started_epoch"] + 1,
        "Attempt advertised replenished time",
    )
    _require(
        record["admitted_epoch"]
        == record["deadline_epoch"] - record["time_remaining_seconds"]
        # Subtracting a remaining interval from an absolute float timestamp can
        # round a fraction of a microsecond past the original timestamp.
        and record["admitted_epoch"] <= record["started_epoch"] + 1e-6,
        "Attempt admission time changed",
    )
