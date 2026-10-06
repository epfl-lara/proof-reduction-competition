"""Contracts for the Lean-free proof-theoretic analysis signals."""

from __future__ import annotations

import json
import textwrap
import unittest
from pathlib import Path

from proof_eval.optimization.proof_theory import (
    SATURATION,
    AnalysisConfig,
    analyze_declaration,
    analyze_proof,
    classify_holes,
    dualize,
)
from proof_eval.verification.metrics import token_count

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "data" / "benchmark_data_warmup.jsonl"


def body(text):
    return "by\n" + textwrap.indent(textwrap.dedent(text).strip("\n"), "  ")


def rows():
    with BENCHMARK.open(encoding="utf-8") as handle:
        return {row["name"]: row for row in map(json.loads, handle)}


class DatasetTests(unittest.TestCase):
    def test_token_count_matches_fixed_reference_for_every_original(self):
        for name, row in rows().items():
            with self.subTest(name=name):
                analysis = analyze_declaration(row, row["src"])
                self.assertEqual(analysis.tokens, row["proof_length"])
                json.dumps(analysis.summary())

    def test_changed_statement_is_rejected_before_analysis(self):
        row = rows()["putnam_1964_b2"]
        with self.assertRaises(ValueError):
            analyze_declaration(row, row["src"].replace("P.card", "P.card + 0", 1))

    def test_duplicated_lemma_is_found_up_to_renaming(self):
        # The original proves the same 776-token digit identity for (d, e) and
        # again for (e, f); one generalized local lemma can replace both.
        row = rows()["putnam_1995_a3"]
        shared = analyze_declaration(row, row["src"]).shared_subproofs
        alpha = [s for s in shared if s.verdict == "alpha"]
        self.assertTrue(alpha)
        self.assertGreater(max(s.saving_tokens for s in alpha), 700)

    def test_mirrored_bisimulation_directions_are_duals(self):
        row = rows()["Cslib.CCS.bisimilarity_congr_choice"]
        shared = analyze_declaration(row, row["src"]).shared_subproofs
        duals = [s for s in shared if s.verdict == "dual"]
        self.assertEqual(len(duals), 1)
        self.assertIn(("hb.follow_fst", "hb.follow_snd"), duals[0].holes)


class CutTests(unittest.TestCase):
    def test_statement_and_proof_split_at_top_level_assignment(self):
        analysis = analyze_proof(body("""
                have h : f (n := 1) = 2 := by
                  simp
                have k : P :=
                  foo bar
                exact k h
                """))
        tactic, term = analysis.cuts
        self.assertEqual(tactic.names, ("h",))
        self.assertEqual(tactic.statement_tokens, token_count("f (n := 1) = 2"))
        self.assertEqual(tactic.proof_tokens, token_count("by\nsimp"))
        self.assertFalse(tactic.term_proof)
        self.assertTrue(term.term_proof)
        self.assertEqual([c.usage for c in analysis.cuts], ["linear", "linear"])

    def test_unreferenced_fact_is_dead_only_without_later_automation(self):
        dead = analyze_proof(body("have a : P := p\nexact q")).cuts[0]
        hidden = analyze_proof(body("have a : P := p\nsimp_all")).cuts[0]
        self.assertEqual(dead.usage, "dead")
        self.assertEqual(hidden.usage, "unnamed_use_possible")

    def test_references_ignore_comments_and_longer_identifiers(self):
        analysis = analyze_proof(body("""
                have h₁ : P := p
                have h₂ : Q := q
                -- h₁ is mentioned only in this comment
                exact f h₁' h₂ h₂
                """))
        self.assertEqual([c.usage for c in analysis.cuts], ["dead", "shared"])

    def test_rebinding_stops_reference_counting(self):
        analysis = analyze_proof(body("""
                have h : A ∧ B := hab
                have h : A := h.1
                exact h
                """))
        self.assertEqual([c.references for c in analysis.cuts], [1, 1])
        self.assertTrue(analysis.cuts[0].alias)
        self.assertEqual(
            analysis.summary()["alias_cut_tokens"],
            sum(c.statement_tokens for c in analysis.cuts),
        )

    def test_destructuring_binds_every_pattern_name(self):
        cut = analyze_proof(
            body("obtain ⟨x, hx, rfl⟩ : ∃ x, P x ∧ x = y := h\nexact hx")
        ).cuts[0]
        self.assertEqual(cut.names, ("x", "hx"))
        self.assertEqual(cut.statement_tokens, token_count("∃ x, P x ∧ x = y"))


class DetourTests(unittest.TestCase):
    def test_introduction_followed_by_elimination(self):
        detours = analyze_proof(body("have h : P := by exact p\nexact h")).detours
        self.assertEqual(sorted(d.kind for d in detours), ["by_exact", "have_exact"])
        self.assertEqual({d.line for d in detours}, {2})

    def test_eta_redex_requires_the_bound_variable_last(self):
        # A preceding step keeps the body's own `by exact` detour out of view.
        redex = analyze_proof(body("rw [hf]\nexact congrArg (fun x => f x) h"))
        applied = analyze_proof(body("rw [hf]\nexact congrArg (fun x => f x y) h"))
        redex, applied = redex.detours, applied.detours
        self.assertEqual([d.kind for d in redex], ["fun_eta"])
        self.assertEqual(applied, ())


class PhaseTests(unittest.TestCase):
    PROOF = body("""
        intro x hx
        obtain ⟨y, hy⟩ := hx
        exists y
        constructor
        · exact hy
        · exact rfl
        """)

    def test_invertible_and_focused_runs_are_separate_phases(self):
        phases = analyze_proof(self.PROOF).phases
        self.assertEqual(
            [(p.kind, p.line, len(p.steps)) for p in phases],
            [("asynchronous", 2, 2), ("synchronous", 4, 4)],
        )

    def test_large_step_is_not_fused_into_a_phase(self):
        config = AnalysisConfig(max_phase_step_tokens=1)
        self.assertEqual(analyze_proof(self.PROOF, config).phases, ())


class AntiUnificationTests(unittest.TestCase):
    def test_dual_names_swap_simultaneously(self):
        self.assertEqual(dualize("hb.follow_fst"), "hb.follow_snd")
        self.assertEqual(dualize("h.1 left right"), "h.2 right left")
        self.assertEqual(dualize("leftover h.10"), "leftover h.10")

    def test_hole_classes(self):
        cases = {
            "renaming": ([(["s1"], ["s2"]), (["s1"], ["s2"])], ["renaming"] * 2),
            "conflict": (
                [(["a"], ["b"]), (["a"], ["c"])],
                ["renaming", "structural"],
            ),
            "dual": (
                [(["hb.follow_fst"], ["hb.follow_snd"]), (["h.1"], ["h.2"])],
                ["dual", "dual"],
            ),
            "instance": (
                [(["A"], ["(", "B", "∪", "C", ")"]), (["A"], ["B"])],
                ["instance", "structural"],
            ),
            "layout": ([([], ["·"])], ["layout"]),
        }
        for label, (holes, expected) in cases.items():
            with self.subTest(label=label):
                self.assertEqual(classify_holes(holes), expected)

    def test_branches_equal_up_to_renaming_are_alpha_equivalent(self):
        shared = analyze_proof(body("""
                constructor
                case left =>
                  intro x hx
                  apply foo
                  exact bar x hx
                case right =>
                  intro y hy
                  apply foo
                  exact bar y hy
                """)).shared_subproofs
        self.assertEqual([s.verdict for s in shared], ["alpha"])
        self.assertGreater(shared[0].saving_tokens, 0)

    def test_mirrored_branches_are_duals(self):
        shared = analyze_proof(body("""
                constructor
                case left =>
                  intro h
                  exact h.1.trans (foo.left h)
                case right =>
                  intro h
                  exact h.2.trans (foo.right h)
                """)).shared_subproofs
        self.assertEqual([s.verdict for s in shared], ["dual"])

    def test_each_copy_is_counted_once_and_never_as_a_template(self):
        branch = "· intro x hx\n  apply foo\n  exact bar x hx rfl\n"
        analysis = analyze_proof(body("refine ⟨?_, ?_, ?_⟩\n" + branch * 3))
        shared = analysis.shared_subproofs
        self.assertEqual(len(shared), 2)
        self.assertEqual({s.first_line for s in shared}, {3})
        self.assertEqual({s.second_line for s in shared}, {6, 9})
        self.assertEqual(
            analysis.summary()["cut_introduction_tokens"],
            sum(s.saving_tokens for s in shared),
        )


class AutomationTests(unittest.TestCase):
    def test_context_counts_named_facts_and_branch_binders(self):
        calls = analyze_proof(body("""
                have h₁ : P := p
                have h₂ : Q ∨ R := q
                cases h₂ with
                | inl a => simp_all
                | inr b => grind only [foo]
                omega
                """)).automation
        self.assertEqual(
            [(c.kind, c.tactic, c.context_size) for c in calls],
            [(SATURATION, "simp_all", 3), ("decision", "omega", 2)],
        )

    def test_inline_tactic_proof_of_a_fact_is_seen(self):
        calls = analyze_proof(body("have h : P := by simp_all\nexact h")).automation
        self.assertEqual([(c.kind, c.context_size) for c in calls], [(SATURATION, 0)])


if __name__ == "__main__":
    unittest.main()
