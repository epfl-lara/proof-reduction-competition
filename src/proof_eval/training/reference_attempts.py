"""Bounded recovery only from a finished original-reference wall timeout."""

from __future__ import annotations

import time
from pathlib import Path

from proof_eval import Evaluator
from proof_eval.evidence.immutable import immutable
from proof_eval.verification.references import required_versions


def prepare_reference_attempts(
    evaluator: Evaluator, row: dict, folder: Path, timeout_retries: int
) -> dict:
    """Preserve every attempt, never retry semantic or unavailable evidence.

    prepare_reference stores only successfully measured fixed references. A
    timeout stores no usable reference, so selecting just those versions on
    the next call cannot replay a successful measurement or candidate cache.
    """
    if type(timeout_retries) is not int or timeout_retries not in (0, 1):
        raise ValueError("Reference preparation permits at most one timeout retry")
    selected = required_versions({"row": row})
    outcomes = {}
    for attempt in range(timeout_retries + 1):
        marker = folder / f"{attempt:02d}-started.json"
        if marker.exists():
            raise RuntimeError("Reference attempt is indeterminate; do not replay")
        started = time.time()
        immutable(
            marker, {"attempt": attempt, "started_epoch": started, "versions": selected}
        )
        result = evaluator.prepare_reference(row["name"], versions=selected)
        immutable(
            folder / f"{attempt:02d}.json",
            {
                "attempt": attempt,
                "started_epoch": started,
                "finished_epoch": time.time(),
                "versions": selected,
                "result": result,
            },
        )
        if set(result["versions"]) != set(selected):
            raise ValueError("Reference attempt returned a different version cohort")
        outcomes.update(result["versions"])
        checks = list(outcomes.values())
        if not all(v.get("status") in {"prepared", "timeout"} for v in checks):
            break
        selected = [
            v for v, value in outcomes.items() if value.get("status") == "timeout"
        ]
        if not selected:
            break
    return {
        "name": row["name"],
        "status": (
            "prepared"
            if all(v.get("status") == "prepared" for v in outcomes.values())
            else "incomplete"
        ),
        "versions": outcomes,
    }
