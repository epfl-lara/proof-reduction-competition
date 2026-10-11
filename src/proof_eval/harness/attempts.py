"""Host-owned attempt boundaries, including incumbent, usage and finish decisions."""

from __future__ import annotations

import time
from copy import deepcopy
from pathlib import Path

from proof_eval.evidence.io import fingerprint, now, read, write_json
from proof_eval.protocol import code_identity

from .session import ProofSession


def attempt_folders(folder: Path) -> list[Path]:
    return sorted(
        (path for path in folder.glob("attempt_*") if path.is_dir()),
        key=lambda path: int(path.name.removeprefix("attempt_")),
    )


def start_attempt(
    folder: Path,
    session: ProofSession,
    messages: list[dict],
    number: int,
    cost: dict,
    timeout: float | None,
    cost_budget: dict | None,
    remaining: float | None = None,
) -> dict:
    path = folder / "attempt.json"
    if path.exists():
        raise RuntimeError(
            "Started attempt evidence exists; not restarted or resampled"
        )
    epoch = time.time()
    record = {
        "number": number,
        "status": "started",
        "started_at": now(),
        "started_epoch": epoch,
        "check_start": len(session.checks),
        "incumbent_proof": session.best_code,
        "incumbent_evaluation": deepcopy(session.best_evaluation),
        "incumbent_sha256": code_identity(session.row, session.best_code),
        "messages_sha256": fingerprint(messages),
        "messages": deepcopy(messages),
        "finish_cleared": session.finished is None,
        "cost_before": cost,
        "cost_budget": cost_budget,
        "generation_timeout_seconds": timeout,
        "deadline_epoch": session.deadline_at,
        "time_remaining_seconds": remaining,
        "admitted_epoch": (
            session.deadline_at - remaining if remaining is not None else epoch
        ),
    }
    write_json(path, record)
    return record


def finish_attempt(
    folder: Path, session: ProofSession, generation: dict, cost: dict
) -> dict:
    record = {
        **read(folder / "attempt.json"),
        "status": "terminal",
        "ended_at": now(),
        "ended_epoch": time.time(),
        "check_end": len(session.checks),
        "generation_status": generation["status"],
        "generation_sha256": fingerprint(generation),
        "agent_stop": deepcopy(session.finished),
        "cost_after": cost,
    }
    write_json(folder / "attempt.json", record)
    return record


def record_stop(
    folder: Path, stop: dict, number: int | None, *, at_epoch: float | None = None
) -> dict:
    record = {
        **stop,
        "attempt": number,
        "at": now(),
        "at_epoch": time.time() if at_epoch is None else at_epoch,
    }
    write_json(folder / "search_stop.json", record)
    return record
