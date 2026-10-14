"""Opt-in host pass after final cleanup: Lean-free deterministic rewrites.

The pass runs the deterministic engine's Lean-free methods in `METHODS` order
on the session's best proof: structural deletions and branch collapses first,
then consolidation, proof-theoretic rewrites, simp relaxation, and tokenizer
rewrites last. Each engine run keeps its own resumable
state and event log beside the session ledger. The engine sees an all-version
eligibility adapter, so it never accepts a candidate that fails any required
Lean version. The final proof then goes through `ProofSession.check`, so it
replaces the best proof only under the session's all-version rule and 0.05-point
margin.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from proof_eval.evidence.io import read, write_json
from proof_eval.optimization.cleanup import AllVersionsEvaluator
from proof_eval.optimization.engine import Budget, optimize
from proof_eval.verification.references import required_versions

from .session import ProofSession

METHODS = ("delete", "collapse", "consolidate", "proof_theory", "relax", "golf")
BUDGET = Budget(rounds=3, trials=24, sites=6, min_gain=0.05)


def frozen_record() -> dict:
    """The configuration entry that enables this pass."""
    return {"methods": list(METHODS), "budget": asdict(BUDGET)}


def final_rewrites(folder: Path, pack: dict, evaluator, session: ProofSession) -> dict:
    """Run every method on the best proof; return per-method outcomes."""
    folder = Path(folder)
    eligibility = folder / "final_rewrites_eligibility.jsonl"

    def record(event):
        with eligibility.open("a") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")

    checker = AllVersionsEvaluator(evaluator, required_versions(pack), record)
    code = session.best_code
    before = session.best_evaluation["scores"]["combined_pct"]
    outcomes = []
    for method in METHODS:
        state_path = folder / f"final_rewrites_{method}.json"
        events_path = folder / f"final_rewrites_{method}.jsonl"

        def emit(event, path=events_path):
            with path.open("a") as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")

        def save(state, path=state_path):
            write_json(path, state)

        state = read(state_path) if state_path.exists() else None
        outcome = optimize(
            checker, pack["row"], code, method, BUDGET, emit, save, state=state
        )
        outcomes.append(
            {
                "method": method,
                "stop_reason": outcome["stop_reason"],
                "attempts": outcome["attempts"],
                "accepted_transitions": outcome["accepted_transitions"],
                "changed": outcome["changed"],
            }
        )
        code = outcome["proof"]
    if code != session.best_code:
        session.check(code, origin="final_rewrites")
    return {
        "methods": outcomes,
        "accepted": code == session.best_code and outcomes_changed(outcomes),
        "gain_pp": session.best_evaluation["scores"]["combined_pct"] - before,
    }


def outcomes_changed(outcomes: list[dict]) -> bool:
    return any(item["changed"] for item in outcomes)
