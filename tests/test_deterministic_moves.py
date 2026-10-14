"""Collapse, deletion, consolidation and relaxation proposals."""

from __future__ import annotations

import json
import textwrap
import unittest
from pathlib import Path

from proof_eval.optimization.engine import LEAN_FREE_METHODS, Budget, discovery
from proof_eval.optimization.proof_theory.methods import METHODS, discover
from proof_eval.optimization.syntax import apply_edits
from proof_eval.verification.metrics import validate_candidate

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "data" / "benchmark_data_warmup.jsonl"
SOL = ROOT / (
    "results/harness/05_model_config/conditions/gpt-6.1-sol__max/"
    "selected_candidates.jsonl"
)


def body(text):
    return "by\n" + textwrap.indent(textwrap.dedent(text).strip("\n"), "  ")


def proposals(method, text):
    finder, _ = METHODS[method]
    return [apply_edits(text, group) for group in finder(text)]


class CollapseTests(unittest.TestCase):
    def test_alternatives_collapse_with_their_common_closer_first(self):
        proof = body("""
            induction e with
            | fvar => simp_all
            | op => simp_all
            | app f a ih => exact ih
            """)
        out = proposals("collapse", proof)
        self.assertEqual(out[0], body("induction e <;> simp_all"))
        self.assertNotIn(body("induction e <;> exact ih"), out)

    def test_trailing_bullets_after_a_split_collapse(self):
        out = proposals("collapse", body("constructor\n· exact ha\n· exact hb"))
        self.assertEqual(out[0], body("constructor <;> exact ha"))
        self.assertIn(body("constructor <;> simp_all"), out)

    def test_branch_binders_are_never_used_by_a_collapsed_closer(self):
        proof = body("cases h\ncase inl a => exact a\ncase inr b => exact b")
        out = proposals("collapse", proof)
        self.assertTrue(out)
        self.assertFalse(any("exact a" in o or "exact b" in o for o in out))

    def test_a_split_followed_by_other_steps_is_left_alone(self):
        self.assertEqual(proposals("collapse", body("constructor\n· simp\nrfl")), [])


class DeletionTests(unittest.TestCase):
    PROOF = body("""
        simp at h
        rw [foo] at h
        have k := h
        intro x
        simp_all <;> omega
        try linarith
        exact k
        """)

    def test_never_deletes_binders_or_the_closing_step(self):
        for out in proposals("delete", self.PROOF):
            for kept in ("have k := h", "intro x", "exact k"):
                self.assertIn(kept, out)

    def test_steps_tails_and_try_wrappers(self):
        out = proposals("delete", self.PROOF)
        self.assertIn(self.PROOF.replace("  simp at h\n", ""), out)
        self.assertIn(self.PROOF.replace("simp_all <;> omega", "simp_all"), out)
        self.assertIn(self.PROOF.replace("try linarith", "linarith"), out)
        self.assertIn(self.PROOF.replace("  try linarith\n", ""), out)

    def test_term_continuation_lines_are_never_deleted_alone(self):
        proof = body("exact foo\n    (bar baz) *\n    qux\nrfl")
        outs = proposals("delete", proof)
        self.assertTrue(outs)
        for out in outs:
            kept = {part in out for part in ("exact foo", "(bar baz) *", "qux")}
            self.assertEqual(len(kept), 1)  # The whole step stays or goes.


class ConsolidationTests(unittest.TestCase):
    def test_rewrites_merge_only_at_the_same_location(self):
        proof = body("""
            rw [a]
            rw [b, c]
            rw [d] at h
            simp only [x] at h
            simp only [y] at h
            exact h
            """)
        out = proposals("consolidate", proof)
        self.assertIn(proof.replace("rw [a]\n  rw [b, c]", "rw [a, b, c]"), out)
        self.assertIn(
            proof.replace(
                "simp only [x] at h\n  simp only [y] at h", "simp only [x, y] at h"
            ),
            out,
        )
        self.assertEqual(len(out), 2)

    def test_relaxation_drops_lists_but_keeps_hypothesis_wildcards(self):
        proof = body("simp only [a, b] at h\nsimpa only [x] using h\nsimp [*] at *")
        out = proposals("relax", proof)
        self.assertIn(proof.replace("simp only [a, b] at h", "simp at h"), out)
        self.assertIn(proof.replace("simpa only [x] using h", "simpa using h"), out)
        self.assertEqual(len(out), 2)


class RegistryTests(unittest.TestCase):
    def test_engine_dispatches_every_registered_method_without_lean(self):
        self.assertEqual(set(METHODS), set(LEAN_FREE_METHODS))
        row = {"name": "t", "source": "s", "statement": "theorem t : P"}
        code = row["statement"] + " := by\n  rw [a]\n  rw [b]\n  simp only [c]\n"
        for method in METHODS:
            with self.subTest(method=method):
                groups, policy, evidence = discovery(None, row, code, method, Budget())
                self.assertEqual(policy, METHODS[method][1])
                self.assertEqual(evidence["analysis_requests"], 0)

    def test_every_proposal_on_saved_proofs_is_a_valid_declaration(self):
        with BENCHMARK.open(encoding="utf-8") as handle:
            rows = {r["name"]: r for r in map(json.loads, handle)}
        with SOL.open(encoding="utf-8") as handle:
            finals = {i["name"]: i["proof"] for i in map(json.loads, handle)}
        for name, row in rows.items():
            for code in (row["src"], finals[name]):
                for method in ("collapse", "delete", "consolidate", "relax"):
                    groups, _ = discover(method, row, code)
                    for group in groups:
                        with self.subTest(name=name, method=method):
                            validate_candidate(row, apply_edits(code, group))


if __name__ == "__main__":
    unittest.main()
