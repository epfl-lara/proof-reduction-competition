"""Original-proof measurement and initial-only optimization inside the run clock."""

from __future__ import annotations

import time
from pathlib import Path

from proof_eval.evidence.io import digest, write_json
from proof_eval.optimization.bounded import run_bounded


def initial_optimization(
    session, folder: Path, config: dict, budget: dict | None
) -> dict:
    phase = run_bounded(
        evaluator=session.evaluator,
        row=session.row,
        proof=session.seed_code,
        evaluation=session.seed_evaluation,
        folder=folder / "initial_optimization",
        methods=tuple(config["initial_deterministic_methods"]),
        seconds=config["initial_deterministic_seconds"],
        deadline_epoch=budget["deadline_epoch"] if budget else None,
        provenance={
            "input_sha256": config["input_sha256"][session.row["name"]],
            "code_sha256": config["code_sha256"],
        },
    )
    if phase["status"] in ("failed", "incomplete_discovery"):
        raise RuntimeError("Initial optimization failed; inspect its saved evidence")
    if phase["accepted_improvements"] and not any(
        c["origin"] == "initial_harness" for c in session.checks
    ):
        # Its certificate is already measured within this phase's hard deadline.
        from proof_eval.protocol import code_identity

        session.cache[code_identity(session.row, phase["proof"])] = phase["evaluation"]
        session.check(phase["proof"], origin="initial_harness")
    if config.get("deterministic_checkpoint"):
        from .checkpoint import adopt_checkpoint

        adopt_checkpoint(session, folder, config)
    if config.get("starting_proofs"):
        from .starting import adopt_starting_proof

        adopt_starting_proof(session, folder, config)
    if (folder / "initial_phase.json").exists():
        return phase
    write_json(
        folder / "initial_phase.json",
        {
            **(
                {"checkpoint_sha256": digest(folder / "checkpoint.json")}
                if config.get("deterministic_checkpoint")
                else {}
            ),
            **(
                {"starting_proof_sha256": digest(folder / "starting_proof.json")}
                if config.get("starting_proofs")
                else {}
            ),
            "measurement_sha256": digest(folder / "initial_measurement.json"),
            "optimization_sha256": digest(folder / "initial_optimization/result.json"),
            "status": phase["status"],
            "check_end": len(session.checks),
            "finished_epoch": time.time(),
        },
    )
    return phase
