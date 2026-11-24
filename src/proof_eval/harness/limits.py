"""Durable whole-problem deadlines; reading a budget never replenishes it."""

from __future__ import annotations

import fcntl
import json
import time
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, now, read, write_json

from .attempts import attempt_folders


def start_budget(folder: Path, seconds: float, *, announce: bool = False) -> dict:
    if announce:
        # Serialize just the first-clock publication across the worker pool.
        # The event uses the real durable problem clock, never the time at which
        # the model server was launched or became HTTP-ready.
        root = folder.parent.parent
        with (root / ".model-timer.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            budget = start_budget(folder, seconds)
            marker = root / "model-timer-started.json"
            if marker.exists():
                saved = read(marker)
                if digest(Path(saved["clock_path"])) != saved["clock_sha256"]:
                    raise ValueError("First model-search clock changed")
            else:
                event = {
                    "event": "MODEL_SEARCH_STARTED",
                    "started_at": budget["started_at"],
                    "started_epoch": budget["started_epoch"],
                    "clock_path": str(folder / "budget_started.json"),
                    "clock_sha256": digest(folder / "budget_started.json"),
                    "setup_and_model_loading_excluded": True,
                    "tools_and_candidate_verification_included": True,
                }
                write_json(marker, event)
                print(json.dumps(event), flush=True)
            return budget
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


def native_deadline_reached(folder: Path) -> bool:
    """Require a terminal native stop covering the persisted problem deadline."""
    attempts = attempt_folders(folder)
    if not attempts or not (folder / "budget_started.json").exists():
        return False
    attempt = attempts[-1]
    paths = [
        attempt / name
        for name in ("attempt.json", "generation.json", "termination.json")
    ]
    if not all(path.exists() for path in paths):
        return False
    record, generation, termination = map(read, paths)
    budget = read(folder / "budget_started.json")
    timeout = record.get("generation_timeout_seconds")
    admitted = record.get("admitted_epoch")
    return (
        record.get("status") == "terminal"
        and record.get("generation_sha256") == fingerprint(generation)
        and generation.get("status") == "budget_exhausted"
        and generation.get("termination") != "cost_limit"
        and generation.get("process_exit") == termination
        and termination.get("controlled") is True
        and termination.get("reason") == "deadline"
        and termination.get("monitor_error") is None
        and timeout is not None
        and admitted is not None
        and admitted < budget["deadline_epoch"]
        and admitted + timeout >= budget["deadline_epoch"] - 1e-5
        and datetime.fromisoformat(termination["at"]).timestamp()
        >= budget["deadline_epoch"]
        and record["ended_epoch"] >= budget["deadline_epoch"]
    )
