"""Read-only proof-history replay and native tool-delivery integrity checks."""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from proof_eval.evidence.io import fingerprint
from proof_eval.evidence.proof_history.model import metadata, validate_ledger
from proof_eval.verification.metrics import validate_candidate

Replay = Callable[[dict, int, int], dict]
ATTEMPT_FIELDS = {
    "proof_history_start",
    "proof_history_query_start",
    "proof_history_query_end",
    "proof_history_queries_before_sha256",
    "proof_history_queries_after_sha256",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _integer(value: Any, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite history evidence JSON constant: {value}")


def _json(value: bytes | str) -> Any:
    return json.loads(value, parse_constant=_reject_constant)


def _records(
    path: Path, *, allow_partial_tail: bool = False
) -> tuple[list[dict], bool]:
    if not path.exists():
        return [], False
    lines = path.read_bytes().splitlines(keepends=True)
    partial = bool(lines and not lines[-1].endswith(b"\n"))
    if partial:
        _require(allow_partial_tail, f"Incomplete history evidence: {path.name}")
        lines.pop()
    records = []
    for line in lines:
        try:
            record = _json(line)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError(f"Malformed history evidence: {path.name}") from exc
        _require(isinstance(record, dict), "History evidence record must be an object")
        records.append(record)
    return records, partial


def _wire(record: dict, field: str) -> bytes:
    try:
        value = base64.b64decode(record[field], validate=True)
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("Invalid tool RPC wire capture") from exc
    return value


def _time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid proof history attempt timestamp") from exc
    _require(parsed.tzinfo is not None, "Proof history timestamps require a timezone")
    return parsed


def _attempt_payload(folder: Path, record: dict, number: int) -> dict:
    path = folder / f"attempt_{number:02d}" / "request.json"
    request = _json(path.read_bytes()) if path.exists() else record
    messages = request.get("messages") if isinstance(request, dict) else None
    _require(
        isinstance(messages, list)
        and len(messages) == 2
        and isinstance(messages[1], dict)
        and isinstance(messages[1].get("content"), str),
        "Proof history attempt has no structured task prompt",
    )
    prefix = "Optimize this declaration using the supplied tools.\n"
    content = messages[1]["content"]
    _require(content.startswith(prefix), "Proof history task prompt prefix changed")
    try:
        payload, _ = json.JSONDecoder(parse_constant=_reject_constant).raw_decode(
            content[len(prefix) :]
        )
    except ValueError as exc:
        raise ValueError("Malformed proof history task prompt") from exc
    _require(isinstance(payload, dict), "Proof history task payload must be an object")
    return payload


def audit_history_attempts(
    config: dict,
    result: dict,
    folder: Path,
    records: Sequence[dict],
    checks: Sequence[dict],
    *,
    scope: dict | None = None,
) -> None:
    """Bind reset pointers and query prefixes to the attempt that observed them.

    Native execution drains accepted tool handlers before ``finish_attempt``;
    that terminal boundary includes the final host check when one occurred.
    Interrupted native replies remain eligible journal entries inside these
    bounds. This helper does not require any new artifact for disabled archives.
    """
    from .proof_history import SUPPORTED_VERSIONS, context_for

    folder = Path(folder)
    queries, _ = _records(folder / "evidence" / "history_queries.jsonl")
    enabled = config.get("proof_history_version") is not None
    if enabled:
        _require(
            type(config["proof_history_version"]) is int
            and config["proof_history_version"] in SUPPORTED_VERSIONS
            and isinstance(scope, dict)
            and bool(scope),
            "Unsupported or missing proof history attempt scope",
        )
    else:
        _require(not queries, "Unconfigured proof history query journal")
    previous_query_end = 0
    for number, record in enumerate(records):
        payload = _attempt_payload(folder, record, number)
        fields = {key for key in record if key.startswith("proof_history")}
        if not enabled:
            _require(
                not fields and "proof_history" not in payload,
                "Unconfigured proof history attempt context",
            )
            continue
        _require(fields == ATTEMPT_FIELDS, "Proof history attempt fields changed")
        start, end = record.get("check_start"), record.get("check_end")
        _require(
            _integer(start, 0, len(checks)) and _integer(end, start, len(checks)),
            "Proof history attempt check boundaries changed",
        )
        expected = context_for(
            scope, list(checks[:start]), result["seed_proof"], record["incumbent_proof"]
        )
        _require(
            fingerprint(payload.get("proof_history")) == fingerprint(expected)
            and fingerprint(record["proof_history_start"]) == fingerprint(expected),
            "Proof history reset context differs from its admitted evidence prefix",
        )
        query_start = record["proof_history_query_start"]
        query_end = record["proof_history_query_end"]
        _require(
            _integer(query_start, previous_query_end, previous_query_end)
            and _integer(query_end, query_start, len(queries)),
            "Proof history attempt query boundaries are inconsistent",
        )
        _require(
            record["proof_history_queries_before_sha256"]
            == fingerprint(queries[:query_start])
            and record["proof_history_queries_after_sha256"]
            == fingerprint(queries[:query_end]),
            "Proof history attempt query prefix changed",
        )
        began, ended = _time(record.get("started_at")), _time(record.get("ended_at"))
        _require(began <= ended, "Proof history attempt time moved backwards")
        for query in queries[query_start:query_end]:
            _require(
                query.get("scope") == scope
                and _integer(query.get("check_count"), start, end)
                and began <= _time(query.get("at")) <= ended,
                "Proof history query crosses an attempt or evidence boundary",
            )
        previous_query_end = query_end
    _require(previous_query_end == len(queries), "Unbound proof history queries")


def audit_query_journal(
    records: Sequence[dict],
    *,
    scope: dict,
    checks: Sequence[dict],
    replay: Replay,
) -> None:
    """Rebuild every delivered view from its committed prefix, never live state.

    ``replay(request, check_count, query_id)`` must be side-effect-free and return
    the complete response including the trusted ``history_query_id`` field.
    """
    previous_count = 0
    for number, record in enumerate(records, 1):
        required = {
            "number",
            "at",
            "scope",
            "check_count",
            "checks_sha256",
            "request",
            "response",
        }
        _require(
            required <= set(record) <= required | {"tool_request"},
            "History query journal fields changed",
        )
        count = record["check_count"]
        _require(
            type(record["number"]) is int
            and record["number"] == number
            and isinstance(record["at"], str)
            and record["scope"] == scope
            and _integer(count, previous_count, len(checks)),
            "History query identity, scope or committed prefix changed",
        )
        _require(
            record["checks_sha256"] == fingerprint(list(checks[:count])),
            "History query committed evidence prefix changed",
        )
        request, response = record["request"], record["response"]
        _require(
            isinstance(request, dict)
            and request.get("op") == "history"
            and isinstance(response, dict)
            and type(response.get("history_query_id")) is int
            and response["history_query_id"] == number,
            "History query request or response identity changed",
        )
        _require(
            response == replay(request, count, number),
            "History query response differs from committed evidence replay",
        )
        previous_count = count


def audit_history_rpc(
    records: Sequence[dict],
    *,
    queries: Sequence[dict],
    checks: Sequence[dict],
    require_rpc: bool = False,
) -> dict:
    """Match terminal deliveries without assigning checks to interrupted starts.

    A query or check can commit before a process is stopped while recording its
    RPC response. Consequently an unmatched start, or an undelivered committed
    query/check, is retained rather than promoted into a completed delivery.
    """
    started: dict[tuple[str, str], dict] = {}
    completed: set[tuple[str, str]] = set()
    query_ids: set[int] = set()
    check_ids: set[int] = set()
    for record in records:
        _require(
            type(record.get("schema_version")) is int
            and record["schema_version"] == 1
            and isinstance(record.get("service_id"), str)
            and bool(record["service_id"])
            and isinstance(record.get("request_id"), str)
            and bool(record["request_id"])
            and isinstance(record.get("workspace"), str),
            "Invalid tool RPC identity",
        )
        key = (record["service_id"], record["request_id"])
        if record.get("event") == "request_started":
            _require(key not in started, "Duplicate tool RPC request identity")
            wire = _wire(record, "request_wire_base64")
            decoded = None
            if len(wire) <= 1024 * 1024 and wire.endswith(b"\n"):
                try:
                    decoded = _json(wire)
                except (ValueError, UnicodeDecodeError):
                    pass
            _require(decoded == record.get("request"), "Tool RPC request wire changed")
            started[key] = record
            continue
        _require(
            record.get("event") == "response_completed"
            and key in started
            and key not in completed,
            "Tool RPC response has no unique preceding request",
        )
        request_record = started[key]
        _require(
            record["workspace"] == request_record["workspace"],
            "Tool RPC response crossed workspaces",
        )
        wire = _wire(record, "response_wire_base64")
        try:
            decoded = _json(wire)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("Invalid tool RPC response wire") from exc
        response = record.get("response")
        _require(
            wire.endswith(b"\n") and isinstance(response, dict) and decoded == response,
            "Tool RPC response wire changed",
        )
        completed.add(key)
        request = request_record.get("request")
        if not isinstance(request, dict) or response.get("kind") == "tool_error":
            continue
        if request.get("op") == "history":
            number = response.get("history_query_id")
            _require(
                _integer(number, 1, len(queries)) and number not in query_ids,
                "History RPC has no unique committed query",
            )
            query = queries[number - 1]
            _require(
                query["request"] == request
                and query["response"] == response
                and (
                    query.get("tool_request") is None
                    or query["tool_request"]
                    == {"service_id": key[0], "request_id": key[1]}
                ),
                "History RPC differs from its committed query",
            )
            query_ids.add(number)
        elif request.get("op") == "check":
            number = response.get("history_check_id")
            _require(
                _integer(number, 1, len(checks)) and number not in check_ids,
                "Check RPC has no unique committed history check",
            )
            check = checks[number - 1]
            _require(
                _check_request(check, request)
                and (
                    check.get("tool_request") is None
                    or check["tool_request"]
                    == {"service_id": key[0], "request_id": key[1]}
                ),
                "Check RPC submitted bytes or selected base changed",
            )
            _audit_check_history_response(response, check, checks[:number])
            check_ids.add(number)
    claimed: set[tuple[str, str]] = set()
    for record, is_query in [
        *((record, False) for record in checks),
        *((record, True) for record in queries),
    ]:
        needs_request = is_query or record.get("origin") == "agent_tool"
        reference = record.get("tool_request")
        if reference is None:
            _require(
                not require_rpc or not needs_request,
                "Committed history event lacks native request identity",
            )
            continue
        _require(
            needs_request
            and isinstance(reference, dict)
            and set(reference) == {"request_id", "service_id"}
            and all(isinstance(value, str) for value in reference.values()),
            "Invalid committed history request identity",
        )
        key = (reference["service_id"], reference["request_id"])
        _require(
            key in started and key not in claimed,
            "Committed history event lacks a unique preceding native request",
        )
        request = started[key].get("request")
        _require(
            isinstance(request, dict)
            and (
                record["request"] == request
                if is_query
                else _check_request(record, request)
            ),
            "Committed history event differs from its native request",
        )
        claimed.add(key)
    return {
        "request_count": len(started),
        "completed_count": len(completed),
        "interrupted_request_count": len(started) - len(completed),
        "delivered_history_queries": len(query_ids),
        "delivered_history_checks": len(check_ids),
    }


def _check_request(check: dict, request: dict) -> bool:
    history = check.get("history", {})
    has_base = "base_check_id" in request
    unknown = request.get("base_unknown") is True
    return (
        request.get("op") == "check"
        and check.get("origin") == "agent_tool"
        and check.get("code") == request.get("code")
        and has_base != unknown
        and (
            (
                has_base
                and type(request["base_check_id"]) is int
                and request["base_check_id"] == history.get("base_check")
                and history.get("base_provenance") == "model_declared"
            )
            or (
                unknown
                and history.get("base_check") is None
                and history.get("base_provenance") == "unknown"
            )
        )
    )


def _audit_check_history_response(
    response: dict, check: dict, prefix: Sequence[dict]
) -> None:
    history = check["history"]
    best = next(
        (
            record["number"]
            for record in reversed(prefix)
            if record.get("accepted") is True
        ),
        0,
    )
    expected = {
        "history_check_id": check["number"],
        "history_base_check_id": history["base_check"],
        "history_base_provenance": history["base_provenance"],
        "history_snapshot_id": history["snapshot_id"],
        "history_best_check_id": best,
        "history_available_checks": check["number"],
    }
    _require(
        expected.keys() <= response.keys()
        and fingerprint({key: response[key] for key in expected})
        == fingerprint(expected),
        "Check RPC history feedback differs from its committed prefix",
    )


def audit_proof_history(
    folder: Path,
    *,
    scope: dict,
    seed_code: str,
    seed_evaluation: dict,
    versions: Sequence[str],
    checks: Sequence[dict],
    row: dict,
    replay: Replay | None = None,
    require_rpc: bool = False,
) -> dict:
    """Audit host records only; never create/rebuild a persistent index or run Lean."""
    folder = Path(folder)
    validate_ledger(
        checks,
        scope=scope,
        seed_code=seed_code,
        seed_evaluation=seed_evaluation,
        versions=versions,
    )
    for record in checks:
        history = record.get("history")
        _require(isinstance(history, dict), "Enabled history check lacks metadata")
        try:
            evaluated_code = validate_candidate(row, record["code"])[0]
        except ValueError:
            evaluated_code = None
        _require(
            history
            == metadata(
                fingerprint(scope),
                record["code"],
                history["base_check"],
                history["base_provenance"],
                evaluated_code,
            ),
            "History evaluated bytes differ from candidate validation",
        )
    queries, _ = _records(folder / "history_queries.jsonl")
    if replay is None:
        from proof_eval.evidence.proof_history import ProofHistory

        history = ProofHistory(
            folder, scope, seed_code, seed_evaluation, versions, memory_only=True
        )

        def replay(request: dict, count: int, number: int) -> dict:
            history.sync(list(checks[:count]))
            return history.query(request, query_id=number)

        try:
            audit_query_journal(queries, scope=scope, checks=checks, replay=replay)
        finally:
            history.close()
    else:
        audit_query_journal(queries, scope=scope, checks=checks, replay=replay)
    rpc_path = folder / "tool_rpc.jsonl"
    needs_rpc = bool(queries) or any(
        record.get("origin") == "agent_tool" for record in checks
    )
    _require(
        not require_rpc or not needs_rpc or rpc_path.exists(),
        "Missing history tool RPC evidence",
    )
    rpc, partial = _records(rpc_path, allow_partial_tail=True)
    result = audit_history_rpc(
        rpc, queries=queries, checks=checks, require_rpc=require_rpc
    )
    return {
        "check_count": len(checks),
        "query_count": len(queries),
        "partial_rpc_tail": partial,
        **result,
    }
