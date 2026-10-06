"""Resumable per-theorem and batch model search; orchestration only."""

from __future__ import annotations

import fcntl
import json
from copy import deepcopy
from pathlib import Path

from proof_eval.evidence.io import fingerprint, read, write_json
from proof_eval.optimization.jobs import DeterministicCleanup
from proof_eval.protocol import extract_declaration
from proof_eval.providers.contracts import AgentGenerator
from proof_eval.verification.api import Evaluator
from proof_eval.verification.feedback import build_validity_feedback
from proof_eval.verification.references import required_versions

from .agent import generate
from .configuration import (
    BASE,
    DETERMINISTIC_MODES,
    guard,
    starting_point,
)
from .limits import time_budget_summary
from .outcomes import finalize_cell
from .prompts import messages
from .session import ProofSession


def run_cell(
    output: Path,
    config: dict,
    pack: dict,
    model: str,
    effort: str,
    evaluator: Evaluator,
    generator: AgentGenerator = generate,
) -> dict:
    mode = config["mode"]
    folder = output / "cells" / fingerprint((pack["name"], model, effort, mode))
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".cell.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (folder / "result.json").exists():
            return read(folder / "result.json")

        def checked_guard():
            return guard(config, pack, evaluator)

        checked_guard()
        seed = starting_point(pack, mode) if mode in DETERMINISTIC_MODES else None
        cleanup = None
        if seed is not None:
            base = read(Path(config.get("base_directory", BASE)) / "config.json")
            provenance = {
                "input_sha256": config["input_sha256"][pack["name"]],
                "contexts": base["contexts"][pack["name"]],
                "references_sha256": fingerprint(
                    {
                        v: e["reference"]
                        for v, e in pack["incumbent"]["per_version"].items()
                    }
                ),
                "code_sha256": config["code_sha256"],
            }
            cleanup = DeterministicCleanup(
                config["deterministic_jobs"], pack, evaluator, provenance, checked_guard
            )
        budget = (
            read(folder / "budget_started.json")
            if (folder / "budget_started.json").exists()
            else None
        )
        session = ProofSession(
            folder / "evidence",
            pack,
            evaluator,
            mode,
            guard=checked_guard,
            seed=seed,
            cleanup=cleanup,
            deadline_at=budget["deadline_epoch"] if budget else None,
            problem_timeout_seconds=budget["timeout_seconds"] if budget else None,
        )
        context = {
            "name": pack["name"],
            "source_file": pack["row"]["file_path"],
            "required_versions": required_versions(pack),
            "source_projects": {
                v: str(evaluator.projects[(pack["row"]["source"], v)])
                for v in required_versions(pack)
            },
        }
        initial = messages(pack, seed=seed) if seed else messages(pack)
        if budget:
            initial[1]["content"] += (
                f"\nWhole-problem time limit: {budget['timeout_seconds']:g} seconds, including host checks and final cleanup. "
                "Use status to see remaining seconds. Leave time for final cleanup; the host keeps the best proof already verified across every required version when the deadline arrives."
            )
        write_json(
            folder / "input.json",
            {
                "name": pack["name"],
                "model": model,
                "effort": effort,
                "mode": mode,
                "messages": initial,
                "seed_proof": session.seed_code,
                "seed_evaluation": session.seed_evaluation,
            },
        )
        generations = []
        final_code, final_feedback = "", None
        max_rounds = config["max_outer_correctness_repairs"]
        for round_number in range(max_rounds + 1):
            checked_guard()
            request = deepcopy(initial)
            if round_number:
                request[1]["content"] += (
                    "\nCorrectness repair only. Repair this proposal using the following compiler feedback.\n"
                    + json.dumps(
                        {
                            "previous_declaration": final_code,
                            "correctness_feedback": final_feedback,
                        },
                        ensure_ascii=False,
                    )
                )
                # A failed unverified final is allowed another correctness-only turn.
                session.finished = None
                (session.folder / "finished.json").unlink(missing_ok=True)
            generation = generator(
                folder=folder / f"attempt_{round_number:02d}",
                messages=request,
                model=model,
                effort=effort,
                mode=mode,
                session=session,
                context=context,
                expected_cli=config["cli"],
                provider=config.get("provider", "codex"),
                **(
                    {"timeout": config["generation_timeout"]}
                    if "problem_timeout_seconds" in config
                    else {}
                ),
            )
            generations.append(generation)
            if generation["status"] != "received":
                break
            try:
                final_code = extract_declaration(
                    generation["content"], generation["finish_reason"]
                )
            except ValueError:
                final_code = generation["content"]
            before = len(session.checks)
            final_feedback = session.check(final_code, origin="final_harness")
            final_eval = (
                session.checks[-1]["evaluation"]
                if len(session.checks) > before
                else None
            )
            if mode != "correctness" or session.first_valid_code is not None:
                break
            if final_eval is None or final_eval["status"] not in (
                "invalid",
                "failed",
                "passed",
            ):
                break
            final_feedback = build_validity_feedback(final_eval, session.versions)
        checked_guard()
        before_final_cleanup = {
            "proof": session.best_code,
            "evaluation": deepcopy(session.best_evaluation),
        }
        write_json(folder / "before_final_cleanup.json", before_final_cleanup)
        if mode in DETERMINISTIC_MODES:
            session.deterministic(session.best_code, origin="final_harness")
        return finalize_cell(
            folder,
            config,
            pack,
            model,
            effort,
            session,
            generations,
            before_final_cleanup,
            time_budget=time_budget_summary(folder, exhausted=False),
        )
