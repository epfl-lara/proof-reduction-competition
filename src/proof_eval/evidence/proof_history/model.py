"""Pure identities, ledger validation and whole-proof history measurements."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from proof_eval.evidence.io import fingerprint, sha
from proof_eval.verification.feedback import all_versions_passed

SCHEMA_VERSION = 1
DIFF_VERSION = 1
MAX_PROOF_BYTES = 16 * 1024 * 1024
PROVENANCES = {"host_selected", "model_declared", "unknown"}


def exact_id(kind: str, text: str) -> str:
    """Hash exact UTF-8 bytes; evaluator normalization is deliberately absent."""
    if not isinstance(text, str):
        raise ValueError("History text must be a string")
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("History text must be valid UTF-8") from exc
    return sha(f"proof-history:v{SCHEMA_VERSION}:{kind}\0" + text)


def snapshot_id(text: str) -> str:
    return exact_id("snapshot", text)


def fragment_id(text: str) -> str:
    if not text:
        raise ValueError("Empty text has no fragment identity; use a boundary span")
    return exact_id("fragment", text)


def integer(value: Any, name: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer between {low} and {high}")
    return value


def check_base(base: int | None, count: int) -> int | None:
    if base is None:
        return None
    return integer(base, "base_check", 0, count)


def metadata(
    scope_sha256: str,
    code: str,
    base_check: int | None,
    base_provenance: str,
    evaluated_code: str | None = None,
) -> dict:
    if not isinstance(base_provenance, str) or base_provenance not in PROVENANCES:
        raise ValueError("Unknown base provenance")
    if (base_check is None) != (base_provenance == "unknown"):
        raise ValueError("Unknown bases require unknown provenance and vice versa")
    result = {
        "schema_version": SCHEMA_VERSION,
        "scope_sha256": scope_sha256,
        "snapshot_id": snapshot_id(code),
        "base_check": base_check,
        "base_provenance": base_provenance,
    }
    if evaluated_code is not None and evaluated_code != code:
        result.update(
            evaluated_code=evaluated_code,
            evaluated_snapshot_id=snapshot_id(evaluated_code),
        )
    return result


def validate_ledger(
    checks: Sequence[dict],
    *,
    scope: Mapping[str, Any],
    seed_code: str,
    seed_evaluation: dict,
    versions: Sequence[str],
) -> list[dict]:
    """Derive events without reading files, mutating evidence or doing Lean work.

    Missing history metadata is historical unknown parentage. Metadata that is
    present must be internally consistent; it is never silently repaired.
    """
    if not isinstance(scope, Mapping) or not scope:
        raise ValueError("History scope must be a nonempty mapping")
    if (
        isinstance(versions, (str, bytes))
        or not versions
        or any(not isinstance(v, str) or not v for v in versions)
        or len(set(versions)) != len(versions)
    ):
        raise ValueError("History requires unique nonempty version names")
    if isinstance(checks, (str, bytes)) or not isinstance(checks, Sequence):
        raise ValueError("History checks must be a sequence")
    scope_hash = fingerprint(dict(scope))
    seed = {
        "number": 0,
        "code": seed_code,
        "evaluation": seed_evaluation,
        "origin": "seed",
        "duplicate": False,
        "accepted": False,
        "history": metadata(scope_hash, seed_code, None, "unknown"),
    }
    events = []
    for number, raw in enumerate([seed, *checks]):
        if not isinstance(raw, dict) or type(raw.get("number")) is not int:
            raise ValueError("History check must have an integer number")
        if raw["number"] != number:
            raise ValueError("History check numbers must form a complete prefix")
        code = raw.get("code")
        identity = snapshot_id(code)
        if len(code.encode("utf-8")) > MAX_PROOF_BYTES:
            raise ValueError("History snapshot exceeds 16 MiB")
        if not isinstance(raw.get("evaluation"), dict):
            raise ValueError("History check must contain an evaluation")
        history = raw.get("history")
        if history is None:
            history = metadata(scope_hash, code, None, "unknown")
        else:
            if not isinstance(history, dict):
                raise ValueError("History metadata must be an object")
            if (
                type(history.get("schema_version")) is not int
                or history.get("schema_version") != SCHEMA_VERSION
            ):
                raise ValueError("Unsupported proof history schema")
            if history.get("scope_sha256") != scope_hash:
                raise ValueError("History check belongs to a different scope")
            if history.get("snapshot_id") != identity:
                raise ValueError("History submitted snapshot identity mismatch")
            base = check_base(history.get("base_check"), number - 1)
            expected = metadata(
                scope_hash,
                code,
                base,
                history.get("base_provenance"),
                history.get("evaluated_code"),
            )
            if history != expected:
                raise ValueError(
                    "History metadata has unsupported or inconsistent fields"
                )
        event = {
            "check_id": number,
            "snapshot_id": identity,
            "code": code,
            "evaluation": deepcopy(raw["evaluation"]),
            "base_check": history["base_check"],
            "base_provenance": history["base_provenance"],
            "duplicate": raw.get("duplicate") is True,
            "accepted": raw.get("accepted") is True,
            "origin": raw.get("origin"),
            "source_sha256": fingerprint(raw),
        }
        if "evaluated_code" in history:
            event["evaluated_code"] = history["evaluated_code"]
            event["evaluated_snapshot_id"] = history["evaluated_snapshot_id"]
        events.append(event)
    return events


def _number(value: Any) -> float | int | None:
    return value if type(value) in (int, float) and math.isfinite(value) else None


def score_view(event: dict, versions: Sequence[str]) -> dict:
    evaluation = event["evaluation"]
    checks = evaluation.get("per_version", {})
    checks = checks if isinstance(checks, dict) else {}
    valid = all_versions_passed(evaluation, versions)
    failed = evaluation.get("status") == "invalid" or any(
        isinstance(checks.get(v), dict) and checks[v].get("status") == "failed"
        for v in versions
    )
    status = "valid" if valid else "invalid" if failed else "incomplete"
    raw_scores = evaluation.get("scores", {})
    raw_scores = raw_scores if isinstance(raw_scores, dict) else {}
    scores = {
        key: _number(raw_scores.get(key))
        for key in (
            "combined_pct",
            "length_reduction_pct",
            "heartbeat_reduction_pct",
            "compatibility_pct",
        )
    }
    candidate = evaluation.get("candidate", {})
    candidate = candidate if isinstance(candidate, dict) else {}
    primary = checks.get(versions[0], {})
    primary = primary if isinstance(primary, dict) else {}
    return {
        "verification": status,
        "all_versions_passed": valid,
        "score_scope": "whole_proof",
        "total_score": scores["combined_pct"] if valid else None,
        "scores": scores if valid else None,
        "raw_gated_scores": scores if not valid else None,
        "source_tokens": _number(candidate.get("length")),
        "primary_heartbeats": _number(primary.get("heartbeats")),
    }


def score_delta(base: dict, result: dict, versions: Sequence[str]) -> float | None:
    before = score_view(base, versions)["total_score"]
    after = score_view(result, versions)["total_score"]
    if before is None or after is None:
        return None
    return _number(after - before)
