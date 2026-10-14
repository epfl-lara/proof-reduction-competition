"""Contracts for proof-theoretic rewrite proposals (never verified improvements)."""

from __future__ import annotations

import json
import textwrap
import unittest
from pathlib import Path

from proof_eval.optimization.engine import Budget, discovery
from proof_eval.optimization.proof_theory.methods import METHODS
from proof_eval.optimization.proof_theory.rewrites import (
    body_groups,
    joint_group,
    proof_theory_groups,
)
from proof_eval.optimization.proof_theory.spans import fill_hole
from proof_eval.optimization.syntax import apply_edits
from proof_eval.verification.metrics import validate_candidate

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "data" / "benchmark_data_warmup.jsonl"
ROW = {"name": "example", "source": "fixture", "statement": "theorem t : P"}


def body(text):
    return "by\n" + textwrap.indent(textwrap.dedent(text).strip("\n"), "  ")


def rewrites(text, reason=None):
    """Every proposed body, optionally only those of one rewrite family."""
    return [
        apply_edits(text, group)
        for group in body_groups(text)
        if reason is None or group[0].reason.split(":")[0] == reason
    ]


class HoleTests(unittest.TestCase):
    def test_argument_holes_are_parenthesized_and_slots_are_not(self):
        self.assertEqual(fill_hole("f ?_ h", "g x"), "f (g x) h")
        self.assertEqual(fill_hole("⟨a, ?_, c⟩", "g x"), "⟨a, g x, c⟩")

    def test_only_the_last_constructor_slot_is_flattened(self):
        self.assertEqual(fill_hole("⟨a, ?_⟩", "⟨b, c⟩"), "⟨a, b, c⟩")
        self.assertEqual(fill_hole("⟨?_, ?_⟩", "⟨b, c⟩"), "⟨⟨b, c⟩, ?_⟩")


class SynchronousTests(unittest.TestCase):
    def test_witness_and_split_become_one_anonymous_constructor(self):
        proof = body("""
            exists w
            constructor
            · exact hw
            · assumption
            """)
        self.assertEqual(
            rewrites(proof, "fuse_synchronous_phase"), [body("exact ⟨w, hw, ‹_›⟩")]
        )

    def test_nested_apply_holes_fill_in_goal_order(self):
        proof = body("""
            apply f ?_ h
            apply g ?_ k
            exact a b
            """)
        self.assertIn(
            body("exact f (g (a b) k) h"), rewrites(proof, "fuse_synchronous_phase")
        )

    def test_unclosed_hole_produces_no_fusion(self):
        proof = body("""
            exists w
            constructor
            · exact hw
            · constructor
              exact h
            """)
        self.assertEqual(rewrites(proof, "fuse_synchronous_phase"), [])


class AsynchronousTests(unittest.TestCase):
    def test_destructuring_moves_into_the_introduction_pattern(self):
        proof = body("intro x hx\nrcases hx with h | h\nexact h")
        self.assertEqual(
            rewrites(proof, "fuse_asynchronous_phase"),
            [body("rintro x (h | h)\nexact h")],
        )

    def test_consecutive_introductions_merge(self):
        self.assertEqual(
            rewrites(body("intro x\nintro y\nexact f x y"), "merge_intros"),
            [body("intro x y\nexact f x y")],
        )

    def test_ambiguous_binder_is_not_fused(self):
        proof = body("intro h h\nobtain ⟨a, b⟩ := h\nexact a")
        self.assertEqual(rewrites(proof, "fuse_asynchronous_phase"), [])


class MergingTests(unittest.TestCase):
    def test_identical_cases_share_one_branch(self):
        proof = body("""
            induction e
            case fvar =>
              simp_all
            case const n =>
              exact n
            case op =>
              simp_all
            """)
        self.assertEqual(
            rewrites(proof, "merge_cases"),
            [body("""
                    induction e
                    case fvar | op =>
                      simp_all
                    case const n =>
                      exact n
                    """)],
        )

    def test_cases_with_different_binders_are_not_merged(self):
        proof = body("cases h\ncase inl a =>\n  exact a\ncase inr b =>\n  exact a")
        self.assertEqual(rewrites(proof, "merge_cases"), [])

    def test_identical_trailing_bullets_become_all_goals(self):
        proof = body("""
            constructor
            · intro x
              simp [x]
            · intro x
              simp [x]
            """)
        self.assertEqual(
            rewrites(proof, "merge_trailing_bullets"),
            [body("constructor\nall_goals\n  intro x\n  simp [x]")],
        )

    def test_bullets_followed_by_another_step_are_kept(self):
        proof = body("constructor\n· simp\n· simp\nrfl")
        self.assertEqual(rewrites(proof, "merge_trailing_bullets"), [])


class NormalizationTests(unittest.TestCase):
    def test_by_exact_detours(self):
        self.assertEqual(rewrites(body("exact foo x"), "by_exact"), ["foo x"])
        self.assertEqual(
            rewrites(body("exact f (by exact h)\nrfl"), "by_exact"),
            [body("exact f (h)\nrfl")],
        )
        for sequence in ("exact p; rfl", "exact p <;> rfl"):
            proof = body(f"have h : P := by {sequence}\nexact h")
            self.assertEqual(rewrites(proof, "by_exact"), [])

    def test_eta_reductions(self):
        self.assertEqual(
            rewrites(body("rw [e]\nexact congrArg (fun x => f x) h"), "fun_eta"),
            [body("rw [e]\nexact congrArg (f) h")],
        )
        self.assertEqual(
            rewrites(body("intro x\nexact f a x"), "intro_eta"),
            [body("exact f a")],
        )
        self.assertEqual(rewrites(body("intro x\nexact f x x"), "intro_eta"), [])

    def test_final_apply_exact_becomes_one_application(self):
        self.assertEqual(
            rewrites(body("rw [e]\napply f\nexact g x"), "apply_exact"),
            [body("rw [e]\nexact f (g x)")],
        )

    def test_only_a_term_cut_used_once_is_inlined(self):
        once = body("have h := f a\nexact g h.1")
        typed = body("have h : A := f a\nexact g h.1")
        self.assertEqual(
            rewrites(typed, "inline_linear_cut"), [body("exact g (f a).1")]
        )
        twice = body("have h := f a\nexact g h h")
        tactic = body("have h := by simp\nexact g h")
        self.assertEqual(rewrites(once, "inline_linear_cut"), [body("exact g (f a).1")])
        self.assertEqual(rewrites(twice, "inline_linear_cut"), [])
        self.assertEqual(rewrites(tactic, "inline_linear_cut"), [])

    def test_a_typed_cut_used_as_a_rewrite_lemma_keeps_its_statement(self):
        # `simp only [rfl]` would lose the fact `f 0 = 0`.
        for use in ("simp only [h0]", "rw [h0] at h", "simp [foo, h0]"):
            typed = body(f"have h0 : f 0 = 0 := rfl\n{use}")
            self.assertEqual(rewrites(typed, "inline_linear_cut"), [], use)
        untyped = body("have h0 := foo 0\nsimp only [h0]")
        self.assertEqual(
            rewrites(untyped, "inline_linear_cut"), [body("simp only [foo 0]")]
        )


class DeclarationTests(unittest.TestCase):
    def test_comments_do_not_shift_offsets(self):
        code = ROW["statement"] + " := by\n  use w -- witness\n  exact hw\n"
        groups = proof_theory_groups(ROW, code)
        self.assertEqual(
            [apply_edits(code, g) for g in groups],
            [ROW["statement"] + " := by\n  exact ⟨w, hw⟩\n"],
        )

    def test_every_original_proposal_keeps_a_valid_declaration(self):
        with BENCHMARK.open(encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle]
        for row in rows:
            groups = proof_theory_groups(row, row["src"])
            joint = joint_group(groups)
            for group in groups + [joint]:
                with self.subTest(name=row["name"], reason=group[:1]):
                    candidate = apply_edits(row["src"], group)
                    self.assertTrue(candidate.startswith(row["statement"]))
                    validate_candidate(row, candidate)
            for a in joint:
                for b in joint:
                    if a is not b:
                        self.assertTrue(a.end <= b.start or b.end <= a.start)

    def test_engine_discovery_needs_no_lean_analysis(self):
        code = ROW["statement"] + " := by\n  intro x\n  intro y\n  exact f x y\n"
        groups, policy, evidence = discovery(None, ROW, code, "proof_theory", Budget())
        self.assertEqual(policy, "joint_then_first")
        self.assertEqual(evidence["analysis_requests"], 0)
        self.assertEqual(
            {apply_edits(code, group) for group in groups},
            {
                ROW["statement"] + " := by\n  intro x y\n  exact f x y\n",
                ROW["statement"] + " := by\n  intro x\n  exact f x\n",
            },
        )


if __name__ == "__main__":
    unittest.main()


class BulletContinuationTests(unittest.TestCase):
    def test_a_multi_line_statement_after_a_bullet_is_one_step(self):
        # The statement continues past the bullet's tactic column; the closing
        # `exact` of the nested block must never be offered for deletion.
        proof = body("""
            constructor
            · have hs : a ⊆
                  b := by
                intro x hx
                simp at hx
                exact hx
              exact hs
            · rfl
            """)
        finder, _ = METHODS["delete"]
        outs = [apply_edits(proof, group) for group in finder(proof)]
        self.assertEqual(len(outs), 1)  # only the redundant `simp at hx`
        self.assertNotIn("simp at hx", outs[0])
        self.assertIn("exact hx", outs[0])
