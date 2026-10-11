"""Audit new attempt boundaries and budget admission without executing snapshots."""

from __future__ import annotations

import json
from pathlib import Path

from proof_eval.evidence.audit import _require
from proof_eval.evidence.io import fingerprint, read
from proof_eval.protocol import code_identity
from proof_eval.providers import agy
from proof_eval.providers.costs import CostConfig
from proof_eval.providers.monitoring import read_events, verified_stream_stop
from proof_eval.providers.retries import recovery_count
from proof_eval.providers.spending import native_cost_guard, native_cost_stop

from .attempts import attempt_folders
from .prompts import budget_suffix
from .tracking import (
    ATTEMPT_EVIDENCE_VERSION,
    CLEANUP_RESERVE_SECONDS,
    attempt_cost,
    stop_decision,
)


def audit_attempts(
    config: dict, result: dict, folder: Path, checks: list, best_at: dict, row: dict
) -> None:
    if not config.get("attempt_evidence_version"):
        return
    _require(
        config["attempt_evidence_version"] == ATTEMPT_EVIDENCE_VERSION,
        "Unsupported attempt evidence version",
    )
    folders = attempt_folders(folder)
    records = [read(path / "attempt.json") for path in folders]
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
        if number:
            first_messages = read(folders[0] / "request.json")["messages"]
            first_payload, _ = json.JSONDecoder().raw_decode(
                first_messages[1]["content"][len(prefix) :]
            )
            _require(
                {
                    key: value
                    for key, value in payload.items()
                    if key not in ("incumbent_declaration", "incumbent_scores")
                }
                == {
                    key: value
                    for key, value in first_payload.items()
                    if key not in ("incumbent_declaration", "incumbent_scores")
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
                    < record["deadline_epoch"] - CLEANUP_RESERVE_SECONDS,
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
        _require(
            messages[1]["content"][len(prefix) + end_of_payload :]
            == budget_suffix(
                config,
                result.get("time_budget"),
                before,
                record["time_remaining_seconds"],
                number,
            ),
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
                    result["model"], result["effort"], **config["cost_assumptions"]
                ),
                config["budget_usd_per_problem"] - total,
            )
        _require(
            record["cost_budget"] == guard and request.get("cost_budget") == guard,
            "Native cost guard differs from the remaining problem budget",
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
                        result["model"], result["effort"], **config["cost_assumptions"]
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
        and record["admitted_epoch"] <= record["started_epoch"],
        "Attempt admission time changed",
    )
