"""Deterministic rewrites never accept a proof that fails a required version."""

from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import proof_eval.harness.session as toolmod
from proof_eval.harness.final_rewrites import final_rewrites
from proof_eval.harness.session import ProofSession
from proof_eval.optimization.cleanup import AllVersionsEvaluator
from proof_eval.optimization.runner import eligibility_checker

ROW = {
    "name": "x",
    "source": "test",
    "statement": "theorem x : P",
    "src": "theorem x : P := by\n  simp",
    "file_path": "Example.lean",
    "version_info": [{"v1": "a"}, {"v2": "b"}],
}
BEST = ROW["statement"] + " := by\n  exact f a (g x)"
GOLFED = ROW["statement"] + " := by\n  exact f a $ g x"


def evaluation(score, code, *, secondary_passes=True):
    passed = {"v1": True, "v2": secondary_passes}
    return {
        "status": "passed",
        "primary_version": "v1",
        "candidate": {"length": 3, "code_sha256": toolmod.code_identity(ROW, code)},
        "scores": {
            "length_reduction_pct": 3 * score - 120,
            "heartbeat_reduction_pct": 20.0,
            "compatibility_pct": 100.0 if secondary_passes else 50.0,
            "combined_pct": score,
        },
        "per_version": {
            v: {
                "status": "passed" if ok else "failed",
                "passed": ok,
                "heartbeats": 100,
                "diagnostics": [],
            }
            for v, ok in passed.items()
        },
    }


class Evaluator:
    def __init__(self, project, golfed_passes_secondary):
        self.projects = {("test", "v1"): project, ("test", "v2"): project}
        self.golfed_passes_secondary = golfed_passes_secondary

    def evaluate(self, name, code, versions="all"):
        if code == GOLFED:
            # Higher combined score, but only when every version passes.
            return evaluation(75.0, code, secondary_passes=self.golfed_passes_secondary)
        return evaluation(70.0 if code == BEST else 0.0, code)


class FinalPassGateTests(unittest.TestCase):
    def run_pass(self, golfed_passes_secondary):
        seed = evaluation(100 / 3, ROW["src"])
        original = toolmod.original_evaluation
        toolmod.original_evaluation = lambda _: deepcopy(seed)
        try:
            with tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                evaluator = Evaluator(folder, golfed_passes_secondary)
                session = ProofSession(
                    folder / "ledger", {"name": "x", "row": ROW}, evaluator, "score"
                )
                session.check(BEST)
                outcome = final_rewrites(
                    folder / "ledger", {"row": ROW}, evaluator, session
                )
                return session, outcome
        finally:
            toolmod.original_evaluation = original

    def test_a_candidate_failing_a_secondary_version_is_never_accepted(self):
        session, outcome = self.run_pass(golfed_passes_secondary=False)
        self.assertEqual(session.best_code, BEST)
        self.assertEqual(outcome["gain_pp"], 0.0)
        self.assertNotIn("final_rewrites", [c["origin"] for c in session.checks])

    def test_the_same_candidate_is_accepted_when_every_version_passes(self):
        session, outcome = self.run_pass(golfed_passes_secondary=True)
        self.assertEqual(session.best_code, GOLFED)
        self.assertAlmostEqual(outcome["gain_pp"], 5.0)


class RunnerGateTests(unittest.TestCase):
    def test_flag_selects_the_all_version_gate(self):
        raw = object()
        self.assertIs(eligibility_checker(raw, ROW, print, False), raw)
        gated = eligibility_checker(raw, ROW, print, True)
        self.assertIsInstance(gated, AllVersionsEvaluator)
        self.assertEqual(gated.required, ["v1", "v2"])


if __name__ == "__main__":
    unittest.main()
