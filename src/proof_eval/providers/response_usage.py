"""Reconcile native Codex request traces with terminal usage, including retries.

The regular exec stream hides some retries and drops counters on failed turns.
Keep reported counters separate from explicit heuristics for missing usage; strict
accounting remains unknown when a request has no complete counters.
"""

from __future__ import annotations

import json
import re
from math import ceil
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, read, write_json

from .costs import USAGE_FIELDS, normalize_token_usage

SCHEMA_VERSION = 2
TRACE_DIRECTORY = "workspace/native_trace"


def rejected_request(error: str) -> bool:
    """Only explicit admission refusals, never generic stream/network failures."""
    # Codex also renders generic HTTP 500 errors as "high demand". Neither
    # that message nor a generic 503 proves refusal before model processing.
    return error == (
        "Selected model is at capacity. Please try a different model."
    ) or bool(re.match(r"^unexpected status 429\b", error))


def _collect_usage_v1(folder: Path, events: list[dict], model: str) -> dict:
    """Rebuild historical accounting with its original compaction stop behavior."""
    folder = folder.resolve()
    files: dict[str, str] = {}
    record = {"schema_version": 1, "files": files, "requests": []}

    def saved(path: Path) -> object:
        path = path.resolve(strict=True)
        if not path.is_relative_to((folder / TRACE_DIRECTORY).resolve()):
            raise ValueError("Native usage payload escapes its trace directory")
        files[str(path.relative_to(folder))] = digest(path)
        return read(path)

    try:
        manifests = list((folder / TRACE_DIRECTORY).glob("*/manifest.json"))
        if len(manifests) != 1:
            raise ValueError("Expected one native usage trace")
        manifest = saved(manifests[0])
        threads = [e["thread_id"] for e in events if e.get("type") == "thread.started"]
        if (
            manifest["schema_version"] != 1
            or threads != [manifest["root_thread_id"]]
            or manifest["raw_event_log"] != "trace.jsonl"
        ):
            raise ValueError(
                "Native usage trace identity does not match the exec stream"
            )
        record["thread_id"] = threads[0]
        trace_path = manifests[0].parent / "trace.jsonl"
        files[str(trace_path.relative_to(folder))] = digest(trace_path)
        rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
        if not rows or rows[-1]["payload"]["type"] != "rollout_ended":
            raise ValueError("Native usage trace has no terminal rollout record")
        requests: dict[str, dict] = {}
        for seq, row in enumerate(rows, 1):
            if (
                row["schema_version"] != 1
                or row["seq"] != seq
                or row["rollout_id"] != manifest["rollout_id"]
                or row.get("thread_id") not in (None, threads[0])
            ):
                raise ValueError("Native usage trace order or identity changed")
            payload = row["payload"]
            kind = payload["type"]
            if kind == "thread_started" and payload["thread_id"] != threads[0]:
                raise ValueError("Unexpected child thread in native usage trace")
            if kind.startswith("compaction_request_"):
                raise ValueError("Compaction usage is not covered by inference tracing")
            if not kind.startswith("inference_"):
                continue
            call_id = payload["inference_call_id"]
            if kind == "inference_started":
                if call_id in requests or payload["model"] != model:
                    raise ValueError(
                        "Duplicate request or changed model in usage trace"
                    )
                requests[call_id] = {"call_id": call_id, "status": "started"}
                record["requests"].append(requests[call_id])
                continue
            request = requests[call_id]
            if request["status"] != "started":
                raise ValueError("Duplicate native request terminal record")
            if kind == "inference_completed":
                response = saved(
                    manifests[0].parent / payload["response_payload"]["path"]
                )
                if response["response_id"] != payload["response_id"]:
                    raise ValueError("Native response identity changed")
                request.update(
                    status="completed",
                    response_id=payload["response_id"],
                    usage=normalize_token_usage(response["token_usage"]),
                )
            elif kind in ("inference_failed", "inference_cancelled"):
                error = payload.get("error", payload.get("reason", ""))
                request.update(status="unknown", error=error)
                if (
                    kind == "inference_failed"
                    and payload.get("partial_response_payload") is None
                    and rejected_request(error)
                ):
                    request["status"] = "rejected"
            else:
                raise ValueError("Unsupported native inference record")
        if not requests:
            raise ValueError("Native usage trace contains no requests")
        total = dict.fromkeys(USAGE_FIELDS, 0)
        for request in requests.values():
            for key, value in request.get("usage", {}).items():
                total[key] += value
        record["token_usage"] = total
        turns = [e for e in events if e.get("type") == "turn.completed"]
        if turns and (
            len(turns) != 1 or normalize_token_usage(turns[0].get("usage")) != total
        ):
            raise ValueError("Native request counters do not match terminal counters")
        unknown = [
            r["call_id"]
            for r in requests.values()
            if r["status"] in ("unknown", "started")
        ]
        record.update(complete=not unknown, unknown_request_ids=unknown)
        if unknown:
            record["reason"] = (
                "Interrupted native requests have no complete usage counters"
            )
    except (OSError, ValueError, KeyError, TypeError) as error:
        record.update(complete=False, reason=str(error))
    return record


def collect_usage(
    folder: Path,
    events: list[dict],
    model: str,
    *,
    schema_version: int = SCHEMA_VERSION,
) -> dict:
    """Retain known counters and evidence even when other requests lack usage."""
    if schema_version == 1:
        return _collect_usage_v1(folder, events, model)
    if schema_version != SCHEMA_VERSION:
        raise ValueError("Unsupported native response usage schema")
    folder = folder.resolve()
    files: dict[str, str] = {}
    requests: dict[tuple[str, str], dict] = {}
    request_payloads: dict[tuple[str, str], object] = {}
    record = {"schema_version": schema_version, "files": files, "requests": []}
    reason = None

    def saved(path: Path) -> object:
        path = path.resolve(strict=True)
        if not path.is_relative_to((folder / TRACE_DIRECTORY).resolve()):
            raise ValueError("Native usage payload escapes its trace directory")
        files[str(path.relative_to(folder))] = digest(path)
        return read(path)

    def estimate(request: dict, key: tuple[str, str], response: object) -> None:
        # Compaction history and its response may contain encrypted text. Their
        # serialized size is an explicit heuristic, not an observed token count
        # or a certified upper bound. Cache/reasoning attribution is unreported.
        def tokens(payload: object) -> int:
            serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            return ceil(len(serialized.encode("utf-8")) / 4)

        request.update(
            estimated_usage={
                **dict.fromkeys(USAGE_FIELDS, 0),
                "input_tokens": tokens(request_payloads[key]),
                "output_tokens": 0 if response is None else tokens(response),
            },
            estimation_basis="canonical_json_utf8_bytes_divided_by_four_uncached",
        )

    try:
        manifests = list((folder / TRACE_DIRECTORY).glob("*/manifest.json"))
        if len(manifests) != 1:
            raise ValueError("Expected one native usage trace")
        manifest = saved(manifests[0])
        threads = [e["thread_id"] for e in events if e.get("type") == "thread.started"]
        if (
            manifest["schema_version"] != 1
            or threads != [manifest["root_thread_id"]]
            or manifest["raw_event_log"] != "trace.jsonl"
        ):
            raise ValueError(
                "Native usage trace identity does not match the exec stream"
            )
        record["thread_id"] = threads[0]
        trace_path = manifests[0].parent / "trace.jsonl"
        files[str(trace_path.relative_to(folder))] = digest(trace_path)
        lines = trace_path.read_text().splitlines()
        last_row = None
        # Scan the full trace before validating its end. Completed responses remain
        # useful evidence when a later request or the native process is interrupted.
        for seq, line in enumerate(lines, 1):
            row = json.loads(line)
            last_row = row
            if (
                row["schema_version"] != 1
                or row["seq"] != seq
                or row["rollout_id"] != manifest["rollout_id"]
                or row.get("thread_id") not in (None, threads[0])
            ):
                raise ValueError("Native usage trace order or identity changed")
            payload = row["payload"]
            kind = payload["type"]
            if kind == "thread_started" and payload["thread_id"] != threads[0]:
                raise ValueError("Unexpected child thread in native usage trace")
            if kind == "compaction_installed":
                saved(manifests[0].parent / payload["checkpoint_payload"]["path"])
                continue
            if kind.startswith("inference_"):
                request_kind, prefix, id_key = (
                    "inference",
                    "inference_",
                    "inference_call_id",
                )
            elif kind.startswith("compaction_request_"):
                request_kind, prefix, id_key = (
                    "compaction",
                    "compaction_request_",
                    "compaction_request_id",
                )
            else:
                continue
            call_id = payload[id_key]
            key = (request_kind, call_id)
            status = kind.removeprefix(prefix)
            if status == "started":
                if key in requests or payload["model"] != model:
                    raise ValueError(
                        "Duplicate request or changed model in usage trace"
                    )
                requests[key] = {
                    "call_id": call_id,
                    "kind": request_kind,
                    "status": "started",
                }
                record["requests"].append(requests[key])
                request_payloads[key] = saved(
                    manifests[0].parent / payload["request_payload"]["path"]
                )
                body = request_payloads[key]
                if (
                    not isinstance(body, dict)
                    or body.get("model") != model
                    or not isinstance(body.get("input"), list)
                ):
                    raise ValueError(
                        "Native request payload is missing or inconsistent"
                    )
                continue
            request = requests[key]
            if request["status"] != "started":
                raise ValueError("Duplicate native request terminal record")
            if status == "completed":
                response = saved(
                    manifests[0].parent / payload["response_payload"]["path"]
                )
                if not isinstance(response, dict):
                    raise ValueError(
                        "Native response payload is missing or inconsistent"
                    )
                if request_kind == "inference":
                    if response["response_id"] != payload["response_id"]:
                        raise ValueError("Native response identity changed")
                    request["response_id"] = payload["response_id"]
                if request_kind == "compaction" and not isinstance(
                    response.get("output_items"), list
                ):
                    raise ValueError("Native compaction response has no output items")
                if request_kind == "compaction" and response.get("token_usage") is None:
                    request.update(
                        status="unknown",
                        error="Completed compaction has no complete usage counters",
                    )
                    estimate(request, key, response)
                else:
                    request.update(
                        status="completed",
                        usage=normalize_token_usage(response["token_usage"]),
                    )
            elif status in ("failed", "cancelled"):
                error = payload.get("error", payload.get("reason", ""))
                request.update(status="unknown", error=error)
                partial = payload.get("partial_response_payload")
                if partial is not None:
                    partial_response = saved(manifests[0].parent / partial["path"])
                    if not isinstance(partial_response, dict) or not isinstance(
                        partial_response.get("output_items"), list
                    ):
                        raise ValueError("Native partial response has no output items")
                    if partial_response.get("token_usage") is not None:
                        request.update(
                            status="accounted_failure",
                            usage=normalize_token_usage(
                                partial_response["token_usage"]
                            ),
                        )
                    else:
                        estimate(request, key, partial_response)
                if status == "failed" and partial is None and rejected_request(error):
                    request["status"] = "rejected"
                elif (
                    status == "failed"
                    and partial is None
                    and request_kind == "inference"
                ):
                    request.update(
                        estimated_usage=dict.fromkeys(USAGE_FIELDS, 0),
                        estimation_basis="failed_inference_without_partial_output_assumed_zero",
                    )
                elif partial is None:
                    estimate(request, key, None)
            else:
                raise ValueError("Unsupported native request record")
        if last_row is None or last_row["payload"]["type"] != "rollout_ended":
            raise ValueError("Native usage trace has no terminal rollout record")
        if not requests:
            raise ValueError("Native usage trace contains no requests")
    except (OSError, ValueError, KeyError, TypeError) as error:
        reason = str(error)

    total = dict.fromkeys(USAGE_FIELDS, 0)
    inference_total = dict.fromkeys(USAGE_FIELDS, 0)
    completed_inference_total = dict.fromkeys(USAGE_FIELDS, 0)
    for request in requests.values():
        for key, value in request.get("usage", {}).items():
            total[key] += value
            if request["kind"] == "inference":
                inference_total[key] += value
                if request["status"] == "completed":
                    completed_inference_total[key] += value
    record["token_usage"] = total
    turns = [e for e in events if e.get("type") == "turn.completed"]
    try:
        # Current native finals omit remote compaction usage. Accept a future
        # final including it only when complete per-request counters also agree.
        if turns and (
            len(turns) != 1
            or normalize_token_usage(turns[0].get("usage"))
            not in (completed_inference_total, inference_total, total)
        ):
            raise ValueError("Native request counters do not match terminal counters")
    except (ValueError, TypeError) as error:
        reason = reason or str(error)
    unknown = [
        request["call_id"]
        for request in requests.values()
        if request["status"] in ("unknown", "started")
    ]
    record.update(complete=reason is None and not unknown, unknown_request_ids=unknown)
    if reason or unknown:
        record["reason"] = reason or "Native requests have no complete usage counters"
    ordered = list(requests.values())
    for index, request in enumerate(ordered):
        if (
            request["kind"] != "compaction"
            or request.get("error")
            != "Completed compaction has no complete usage counters"
        ):
            continue
        # Ciphertext size is a poor proxy for its underlying model tokens. Prefer
        # observed context sizes on either side of the compaction. The next input
        # also contains retained history, so this is a deliberately conservative
        # proxy for compact output, not an observed compact response counter.
        preceding = next(
            (
                other
                for other in reversed(ordered[:index])
                if other["kind"] == "inference" and other["status"] == "completed"
            ),
            None,
        )
        following = next(
            (
                other
                for other in ordered[index + 1 :]
                if other["kind"] == "inference" and other["status"] == "completed"
            ),
            None,
        )
        evidence = {}
        if preceding is not None:
            usage = preceding["usage"]
            request["estimated_usage"]["input_tokens"] = (
                usage["input_tokens"] + usage["output_tokens"]
            )
            evidence["input"] = {
                "call_id": preceding["call_id"],
                "counter": "input_tokens_plus_output_tokens",
            }
        if following is not None:
            request["estimated_usage"]["output_tokens"] = following["usage"][
                "input_tokens"
            ]
            evidence["output"] = {
                "call_id": following["call_id"],
                "counter": "input_tokens_including_retained_history",
            }
        if evidence:
            request["estimation_basis"] = (
                "neighboring_reported_context_tokens"
                if preceding is not None and following is not None
                else "reported_context_tokens_with_json_size_fallback"
            )
            request["estimation_evidence"] = evidence
    estimated_total = total.copy()
    estimates = []
    for request in requests.values():
        if "estimated_usage" not in request:
            continue
        for key, value in request["estimated_usage"].items():
            estimated_total[key] += value
        estimates.append(
            {
                "call_id": request["call_id"],
                "kind": request["kind"],
                "basis": request["estimation_basis"],
                "token_usage": request["estimated_usage"],
                **(
                    {"evidence": request["estimation_evidence"]}
                    if "estimation_evidence" in request
                    else {}
                ),
            }
        )
    record.update(
        structurally_valid=reason is None,
        estimated_token_usage=estimated_total,
        estimated_usage_complete=reason is None
        and all(request["status"] != "started" for request in requests.values()),
        usage_estimates=estimates,
    )
    return record


def apply_usage(result: dict, record: dict) -> dict:
    """Use reconciled request counters without changing the native task outcome."""
    result = dict(result)
    result.update(
        response_usage_schema_version=record["schema_version"],
        response_usage_sha256=fingerprint(record),
        usage_complete=record["complete"],
    )
    if "token_usage" in record:
        result["token_usage"] = record["token_usage"]
    if record["schema_version"] == 2:
        for key in (
            "structurally_valid",
            "estimated_token_usage",
            "estimated_usage_complete",
            "usage_estimates",
        ):
            result[key] = record[key]
    if record["complete"]:
        result.pop("usage_incomplete_reason", None)
    else:
        result["usage_incomplete_reason"] = record["reason"]
    return result


def reconcile_usage(
    folder: Path,
    events: list[dict],
    model: str,
    result: dict,
    *,
    schema_version: int = SCHEMA_VERSION,
) -> dict:
    """Persist host-owned accounting separately from the native workspace."""
    record = collect_usage(folder, events, model, schema_version=schema_version)
    write_json(folder / "response_usage.json", record)
    return apply_usage(result, record)


def audit_usage(folder: Path, events: list[dict], model: str, result: dict) -> dict:
    """Rebuild accounting from pinned native evidence without model requests."""
    record = read(folder / "response_usage.json")
    if record != collect_usage(
        folder, events, model, schema_version=record["schema_version"]
    ):
        raise ValueError("Native response usage evidence changed")
    return apply_usage(result, record)
