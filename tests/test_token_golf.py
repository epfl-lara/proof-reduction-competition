"""Tokenizer-aware rewrites and the opt-in final rewrite pass."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from proof_eval.optimization.engine import Budget, discovery
from proof_eval.optimization.syntax import apply_edits
from proof_eval.optimization.token_golf import body_golf_groups, golf_groups
from proof_eval.verification.metrics import token_count, validate_candidate

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "data" / "benchmark_data_warmup.jsonl"


def golfed(line):
    body = "by\n  " + line
    return [apply_edits(body, g)[5:] for g in body_golf_groups(body)]


class GolfRuleTests(unittest.TestCase):
    def test_rewrites_in_term_positions(self):
        cases = {
            "exact f a (g x)": ["exact f a $ g x"],
            "exact (h x)": ["exact h x"],
            "refine ⟨f (g x), h⟩": ["refine ⟨f $ g x, h⟩"],
            "rw [← foo (bar x)]": ["rw [← foo $ bar x]"],
            "have h : P (x) := foo (bar y)": ["have h : P (x) := foo $ bar y"],
        }
        for line, expected in cases.items():
            with self.subTest(line=line):
                self.assertEqual(golfed(line), expected)

    def test_semicolons_become_aligned_lines(self):
        self.assertEqual(golfed("simp; ring"), ["simp\n  ring"])
        self.assertEqual(golfed("· exact foo; simp"), ["· exact foo\n    simp"])
        line = "have h : P := by simp; ring"
        column = 2 + line.index("simp")  # the body indents each line by two
        self.assertEqual(
            golfed(line), ["have h : P := by simp\n" + " " * column + "ring"]
        )

    def test_parse_changing_rewrites_are_not_proposed(self):
        for line in (
            "exact a = f (g x)",
            "exact h ▸ (x y)",
            "constructor <;> (simp; ring)",
            "exact (h x).symm",
            "exact f (x : ℝ)",
            "exact f (g x) |>.1",
            "exact f (g x)\n    (h y)",
            "exact f ⟨a, b⟩ (c, d)",
        ):
            with self.subTest(line=line):
                self.assertEqual(golfed(line), [])

    def test_every_rewrite_saves_tokens_on_the_selected_proofs(self):
        sol = ROOT / (
            "results/harness/05_model_config/conditions/gpt-6.1-sol__max/"
            "selected_candidates.jsonl"
        )
        with BENCHMARK.open(encoding="utf-8") as handle:
            rows = {r["name"]: r for r in map(json.loads, handle)}
        with sol.open(encoding="utf-8") as handle:
            proofs = [json.loads(line) for line in handle]
        for item in proofs:
            row, code = rows[item["name"]], item["proof"]
            before = token_count(validate_candidate(row, code)[1])
            for group in golf_groups(row, code):
                with self.subTest(name=row["name"], reason=group[0].reason):
                    after = validate_candidate(row, apply_edits(code, group))[1]
                    self.assertLess(token_count(after), before)

    def test_engine_method_needs_no_lean_analysis(self):
        row = {"name": "t", "source": "s", "statement": "theorem t : P"}
        code = row["statement"] + " := by\n  exact f (g x)\n"
        groups, policy, evidence = discovery(None, row, code, "golf", Budget())
        self.assertEqual(policy, "joint_then_first")
        self.assertEqual(evidence["analysis_requests"], 0)
        self.assertEqual(
            [apply_edits(code, g) for g in groups],
            [row["statement"] + " := by\n  exact f $ g x\n"],
        )
