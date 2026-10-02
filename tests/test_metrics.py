"""Contract tests for fixed references, statement boundaries, and intake guards."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from proof_eval.dataset import Dataset
from proof_eval.metrics import reduction_percent, strip_comments, token_count, validate_candidate


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "data" / "benchmark_data_warmup.jsonl"


class DatasetTests(unittest.TestCase):
    def test_official_references_load_without_recomputation(self):
        dataset = Dataset(BENCHMARK)
        self.assertEqual(len(dataset.names), 15)
        row = dataset.get("putnam_1964_a4")
        self.assertEqual(row["proof_length"], 1769)
        self.assertEqual(row["published_heartbeats"], 111476)
        row["proof_length"] = 1
        row["version_info"].clear()
        self.assertEqual(dataset.get("putnam_1964_a4")["proof_length"], 1769)
        self.assertTrue(dataset.get("putnam_1964_a4")["version_info"])
        names = dataset.names
        names.clear()
        self.assertEqual(len(dataset.names), 15)

    def test_missing_heartbeat_is_explicit_and_reference_count_is_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.jsonl"
            row = Dataset(BENCHMARK).get("putnam_1964_a4")
            row["proof_length"] = 123456
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            loaded = Dataset(path).get(row["name"])
            self.assertEqual(loaded["proof_length"], 123456)
            self.assertIsNone(loaded["published_heartbeats"])

    def test_duplicate_problem_is_rejected(self):
        row = Dataset(BENCHMARK).get("putnam_1964_a4")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.jsonl"
            path.write_text((json.dumps(row) + "\n") * 2, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate name"):
                Dataset(path)


class TokenCountTests(unittest.TestCase):
    def test_matches_all_fifteen_published_reference_lengths(self):
        dataset = Dataset(BENCHMARK)
        for name in dataset.names:
            with self.subTest(name=name):
                row = dataset.get(name)
                _, body = validate_candidate(row, row["src"])
                self.assertEqual(token_count(body), row["proof_length"])

    def test_known_tokenization_with_operator_grouping(self):
        self.assertEqual(token_count("by\n  exact Nat.add_comm a b"), 5)
        self.assertEqual(token_count("by simp <;> rfl"), 4)
        self.assertEqual(token_count("by\n  have h := a != b\n  exact h"), 9)
        self.assertEqual(token_count("\n\n -- comment only\n"), 0)

    def test_nested_comments_and_blank_lines_do_not_count(self):
        commented = "by /- outer /- inner -/ tail -/\n\n  -- noise\n  rfl"
        self.assertEqual(token_count(commented), token_count("by rfl"))
        self.assertEqual(strip_comments("foo/- x -/bar"), "foo bar")

    def test_comment_markers_in_literals_are_retained(self):
        for text in ('"-- /- hello -/"', 'r#"-- /- hello -/"#', "'\"'", "«a/-b-/»"):
            with self.subTest(text=text):
                self.assertEqual(strip_comments(text), text)
        self.assertEqual(strip_comments('"\\\"/-" -- tail'), '"\\\"/-" ')

    def test_unterminated_lexical_forms_rejected(self):
        for text in ('by /- unfinished', '"unterminated', 'r##"text"#', '«unterminated'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                strip_comments(text)


class CandidateTests(unittest.TestCase):
    row = {"statement": "theorem target : True"}

    def test_body_and_full_inputs_return_the_same_declaration(self):
        expected = "theorem target : True := by\n  trivial"
        self.assertEqual(validate_candidate(self.row, expected), (expected, "by\n  trivial"))
        self.assertEqual(validate_candidate(self.row, "by\n  trivial", "body"), (expected, "by\n  trivial"))

    def test_assignment_inside_statement_is_not_proof_boundary(self):
        row = {"statement": "theorem target : let n := 1; n = 1"}
        full, body = validate_candidate(row, row["statement"] + " := by rfl")
        self.assertEqual(body, "by rfl")
        self.assertEqual(full, row["statement"] + " := by rfl")
        real = Dataset(BENCHMARK).get("Binius.BinaryBasefold.fold_advances_evaluation_poly")
        _, body = validate_candidate(real, real["src"])
        self.assertTrue(body.startswith("by"))
        self.assertEqual(token_count(body), 1906)

    def test_changed_statements_rejected(self):
        for code in (
            "theorem target : False := by trivial",
            "theorem other : True := by trivial",
            "theorem target : True ∨ False := by trivial",
            "theorem target : True :=",
            "theorem target : True := /- empty -/",
        ):
            with self.subTest(code=code), self.assertRaises(ValueError):
                validate_candidate(self.row, code)

    def test_all_official_and_additional_commands_rejected(self):
        bad_bodies = (
            "by sorry", "by admit", "by exact sorryAx _ false", "by native_decide",
            "by exact ofReduceBool _", "by exact ofReduceNat _",
            "by run_elab pure ()", "by run_cmd pure ()", "by exact IO.println x",
            "by trivial\n#eval 1", "by trivial\n#reduce 1", "by trivial\n#exit",
            "by trivial\n#count_heartbeats in theorem t : True := by trivial",
            "by trivial\n#print axioms target", "by trivial\nnamespace X",
            "by trivial\nend X", "by trivial\nimport Mathlib",
            "by trivial\nset_option Elab.async true", "by\n  set_option maxRecDepth 1000 in trivial",
            "by trivial\nlemma other : True := by trivial",
            "by trivial theorem other : True := by trivial",
            "by trivial\nexample : True := by trivial", "by trivial\ndef foo := 1",
            "by trivial\nunsafe def foo := 1", "by trivial\naxiom foo : False",
            "by trivial\nattribute [simp] target", "by trivial\nopen X",
            "by trivial\nmacro_rules | `(foo) => `(trivial)",
            "by trivial\ninitialize x : Nat ← pure 0",
            "by trivial\n@[implemented_by foo] def x := 0",
            "by trivial\n/- misleading /- nested -/ comment -/ set_option Elab.async true",
            'by\n  let a := "/-"\n  run_elab pure ()\n  let b := "-/"\n  trivial',
        )
        for body in bad_bodies:
            with self.subTest(body=body), self.assertRaises(ValueError):
                validate_candidate(self.row, body, "body")

    def test_comments_can_mention_banned_constructs(self):
        body = "by\n  /- sorry /- #eval 1 -/ set_option Elab.async true -/\n  trivial -- theorem evil"
        self.assertEqual(validate_candidate(self.row, body, "body")[1], body)

    def test_local_proof_terms_are_supported(self):
        for body in (
            "by\n  have h : True := by trivial\n  exact h",
            "by\n  let n := 1\n  have h := (rfl : n = n)\n  trivial",
            "calc\n  True = True := rfl",
            "match True.intro with\n| h => h",
            '(by\n  let s := "(]"\n  trivial)',
            "by\n  let c := '\"'\n  trivial",
        ):
            with self.subTest(body=body):
                self.assertEqual(validate_candidate(self.row, body, "body")[1], body)

    def test_unbalanced_delimiter_escape_rejected(self):
        for body in ("by trivial)", "(by trivial", "by exact ([)]"):
            with self.subTest(body=body), self.assertRaisesRegex(ValueError, "Unbalanced"):
                validate_candidate(self.row, body, "body")

    def test_size_guard_counts_utf8_bytes(self):
        with self.assertRaisesRegex(ValueError, "size limit"):
            validate_candidate(self.row, "by /-" + "ℕ" * 90000 + "-/ trivial", "body")


class ReductionTests(unittest.TestCase):
    def test_relative_reductions_and_missing_baselines(self):
        self.assertEqual(reduction_percent(100, 25), 75.0)
        self.assertEqual(reduction_percent(100, 200), -100.0)
        self.assertEqual(reduction_percent(100, 0), 100.0)
        self.assertIsNone(reduction_percent(0, 10))
        self.assertIsNone(reduction_percent(None, 10))
        self.assertIsNone(reduction_percent(10, None))

    def test_invalid_measurements_cannot_be_rewards(self):
        for reference, candidate in ((10, -1), (-1, 10), (10, float("nan")), (float("inf"), 10), (True, 1)):
            with self.subTest(reference=reference, candidate=candidate), self.assertRaises(ValueError):
                reduction_percent(reference, candidate)


if __name__ == "__main__":
    unittest.main()
