"""Opt-in host pass after final cleanup: proof-theoretic and tokenizer rewrites.

The pass runs the deterministic engine's `proof_theory` and `golf` methods, in
that order, on the session's best proof. Each engine run keeps its own resumable
state and event log beside the session ledger. The final proof then goes through
`ProofSession.check`, so it replaces the best proof only under the session's
usual all-version rule and 0.05-point margin.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from proof_eval.evidence.io import read, write_json
from proof_eval.optimization.engine import Budget, optimize

from .session import ProofSession

METHODS = ("proof_theory", "golf")
BUDGET = Budget(rounds=3, trials=24, sites=6, min_gain=0.05)


def frozen_record() -> dict:
    """The configuration entry that enables this pass."""
    return {"methods": list(METHODS), "budget": asdict(BUDGET)}


def final_rewrites(folder: Path, pack: dict, evaluator, session: ProofSession) -> dict:
    """Run every method on the best proof; return per-method outcomes."""
    folder = Path(folder)
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
            evaluator, pack["row"], code, method, BUDGET, emit, save, state=state
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
