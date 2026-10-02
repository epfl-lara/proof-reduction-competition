"""Transformation safety and objective tests, independent of Mathlib downloads."""
import unittest

from proof_eval.optimizer import Edit, apply_edits, deletion_edits, position_offset, score_improves, primary_upper_bound


def evaluation(length, heartbeats, compatibility, status="passed"):
    axes = [length, heartbeats, compatibility]
    return {"status": status, "scores": {"length_reduction_pct": length, "heartbeat_reduction_pct": heartbeats,
            "compatibility_pct": compatibility, "combined_pct": None if None in axes else sum(axes) / 3}}


class ObjectiveTests(unittest.TestCase):
    def test_length_gain_does_not_justify_larger_heartbeat_regression(self):
        self.assertFalse(score_improves(evaluation(0, 0, 100), evaluation(20, -30, 100)))

    def test_longer_proof_can_win_on_heartbeats(self):
        self.assertTrue(score_improves(evaluation(0, 0, 100), evaluation(-5, 40, 100)))

    def test_incomplete_compatibility_is_not_an_improvement(self):
        self.assertFalse(score_improves(evaluation(0, 0, 100), evaluation(70, 70, None)))

    def test_compatibility_loss_has_its_actual_score_cost(self):
        self.assertFalse(score_improves(evaluation(0, 0, 100), evaluation(5, 5, 50)))
        self.assertTrue(score_improves(evaluation(0, 0, 100), evaluation(70, 70, 50)))

    def test_jitter_margin_and_invalidity(self):
        self.assertFalse(score_improves(evaluation(0, 0, 100), evaluation(0, 0.01, 100)))
        self.assertFalse(score_improves(evaluation(0, 0, 100), evaluation(90, 90, 100, "failed")))

    def test_primary_bound_is_optimistic_not_a_final_score(self):
        self.assertEqual(primary_upper_bound(evaluation(30, -10, None)), 40)
        self.assertIsNone(primary_upper_bound(evaluation(30, None, None)))


class EditTests(unittest.TestCase):
    def test_unicode_positions_and_multiple_edits(self):
        code = "theorem π : True := by\n  have α := 1\n  trivial\n"
        start = position_offset(code, {"line": 2, "column": 2})
        stop = position_offset(code, {"line": 2, "column": 13})
        self.assertEqual(code[start:stop], "have α := 1")
        self.assertEqual(Edit(start, stop, "", "unused").apply(code), code.replace("have α := 1", ""))

    def test_nested_deletions_do_not_shift_later_offsets(self):
        self.assertEqual(apply_edits("abcdefghij", [Edit(1, 5, "", "outer"), Edit(2, 3, "", "inner"), Edit(7, 9, "", "later")]), "afgj")

    def test_drop_rhs_of_combinator_preserves_lhs(self):
        code = "by simp <;> omega"
        nodes = [{"kind": "Lean.Parser.Tactic.«tactic_<;>_»", "path": [0], "start": 3, "end": len(code)},
                 {"kind": "Lean.Parser.Tactic.omega", "path": [0, 2], "start": 12, "end": len(code)}]
        analysis = {"nodes": nodes, "messages": [{"kind": "linter.unreachableTactic", "start": 12, "end": len(code)}]}
        self.assertEqual(apply_edits(code, deletion_edits(code, analysis)).strip(), "by simp")

    def test_unmatched_or_unrelated_diagnostic_cannot_delete_text(self):
        self.assertEqual(deletion_edits("by rfl", {"nodes": [], "messages": [
            {"kind": "linter.unusedVariables", "start": 0, "end": 6},
            {"kind": "linter.unusedTactic", "start": 3, "end": 6}]}), [])


if __name__ == "__main__":
    unittest.main()
