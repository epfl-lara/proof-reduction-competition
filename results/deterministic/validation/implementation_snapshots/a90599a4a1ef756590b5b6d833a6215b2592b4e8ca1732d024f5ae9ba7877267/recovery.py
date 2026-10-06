"""Finalize controlled deadline stops solely from saved proof certificates."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from proof_eval.evidence.io import now, read, write_json, write_jsonl
from proof_eval.providers.registry import adapter
from proof_eval.verification.api import Evaluator

from .configuration import starting_point
from .limits import time_budget_summary
from .outcomes import finalize_cell
from .prompts import messages
from .session import ProofSession


def _generation(folder: Path, provider: str) -> dict:
    path = folder / "generation.json"
    if path.exists():
        return read(path)
    events = []
    event_path = folder / "events.jsonl"
    for line in event_path.read_text().splitlines() if event_path.exists() else []:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            # A killed CLI can leave a partial last line; keep its raw bytes.
            break
    final_path = folder / "workspace/final.txt"
    final = final_path.read_text() if final_path.exists() else ""
    if not final:
        answers = [
            e["item"].get("text", "")
            for e in events
            if e.get("type") == "item.completed"
            and e.get("item", {}).get("type") == "agent_message"
        ]
        final = answers[-1] if answers else ""
    parsed = adapter(provider).parse_events(events, final, 0)
    if parsed["status"] == "received":
        final_path.write_text(parsed["content"])
    elif not parsed.get("events_errors") and not any(
        e.get("type") == "result" for e in events
    ):
        parsed.update(
            status="budget_exhausted",
            error="Whole-problem wall deadline reached; not resampled",
        )
    parsed.update(provider=provider, finished_at=now(), termination="problem_deadline")
    write_json(path, parsed)
    return parsed


def recover_cell(
    folder: Path,
    config: dict,
    pack: dict,
    model: str,
    effort: str,
    evaluator: Evaluator,
) -> dict:
    """Never dispatch a model, compile Lean, or restart deterministic work."""
    end = read(folder / "budget_end.json")
    if not end["exhausted"]:
        raise ValueError("Deadline recovery requires a supervised deadline stop")
    seed = starting_point(pack, config["mode"])
    session = ProofSession(
        folder / "evidence", pack, evaluator, config["mode"], seed=seed
    )
    if not (folder / "input.json").exists():
        write_json(
            folder / "input.json",
            {
                "name": pack["name"],
                "model": model,
                "effort": effort,
                "mode": config["mode"],
                "messages": messages(pack, seed=seed),
                "seed_proof": session.seed_code,
                "seed_evaluation": session.seed_evaluation,
            },
        )
    generations = [
        _generation(attempt, config["provider"])
        for attempt in sorted(folder.glob("attempt_*"))
        if (attempt / "request.json").exists()
    ]
    pending = session.folder / "cleanup_started.json"
    if pending.exists() and not session.cleanup_calls:
        partial = read(pending)
        if "job" in partial:
            job = partial["job"]
            after = next(
                (
                    c
                    for c in session.checks
                    if c["origin"] == "deterministic_final_harness"
                    and c["code"] == job["proof"]
                    and c["evaluation"] == job["evaluation"]
                ),
                None,
            )
            if after is not None:
                record = {
                    "number": 1,
                    "at": now(),
                    "origin": "final_harness",
                    "input_code_sha256": partial["input_code_sha256"],
                    "input_check": partial["input_check"],
                    "output_check": after["number"],
                    "status": job["status"],
                    "job_path": job["job_path"],
                    "job_result_sha256": job["job_result_sha256"],
                    "counters": job["counters"],
                    "reused": job.get("reused", False),
                }
                write_jsonl(session.folder / "deterministic.jsonl", [record])
                session.cleanup_calls.append(record)
    before = (
        read(folder / "before_final_cleanup.json")
        if (folder / "before_final_cleanup.json").exists()
        else {
            "proof": session.best_code,
            "evaluation": deepcopy(session.best_evaluation),
        }
    )
    return finalize_cell(
        folder,
        config,
        pack,
        model,
        effort,
        session,
        generations,
        before,
        time_budget=time_budget_summary(folder, exhausted=True),
    )
