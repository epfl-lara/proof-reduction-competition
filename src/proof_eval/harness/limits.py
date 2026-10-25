"""Durable whole-problem deadlines; reading a budget never replenishes it."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path

from proof_eval.evidence.io import now, read, write_json


def start_budget(folder: Path, seconds: float) -> dict:
    if type(seconds) not in (float, int) or not isfinite(seconds) or seconds <= 0:
        raise ValueError("Problem time limit must be positive and finite")
    path = folder / "budget_started.json"
    if path.exists():
        budget = read(path)
        if budget["timeout_seconds"] != seconds:
            raise ValueError("Saved problem time limit changed")
        return budget
    epoch = time.time()
    budget = {
        "started_at": now(),
        "started_epoch": epoch,
        "deadline_epoch": epoch + seconds,
        "deadline_at": datetime.fromtimestamp(
            epoch + seconds, timezone.utc
        ).isoformat(),
        "timeout_seconds": seconds,
        "scope": "one_problem_including_tools_and_cleanup",
    }
    write_json(path, budget)
    return budget


def time_budget_summary(folder: Path, *, exhausted: bool) -> dict | None:
    path = folder / "budget_started.json"
    if not path.exists():
        return None
    budget = read(path)
    end = (
        read(folder / "budget_end.json")
        if (folder / "budget_end.json").exists()
        else {}
    )
    return {
        **budget,
        "exhausted": exhausted or end.get("exhausted") is True,
        "elapsed_seconds": max(
            0.0, end.get("work_stopped_epoch", time.time()) - budget["started_epoch"]
        ),
    }
