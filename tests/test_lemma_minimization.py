"""Argument deletion must respect Lean syntax and preserve tactic controls."""
import unittest

from proof_eval.lemma_minimization import deletion_chunks, list_sites, minimization_groups


def fixture(tactic, arguments, *, only=False, suffix="", compound_indices=()):
    """Small AST fixtures matching Lean 4's observed parser/list structure.

    Compound argument nodes have source spans, while identifier atoms do not
    appear in the optimizer's observer output. Simp/rw wrap every argument.
    """
    kinds = {"simp": "Lean.Parser.Tactic.simp", "simp_all": "Lean.Parser.Tactic.simpAll",
             "dsimp": "Lean.Parser.Tactic.dsimp", "rw": "Lean.Parser.Tactic.rwSeq",
             "linarith": "Mathlib.Tactic.linarith", "nlinarith": "Mathlib.Tactic.nlinarith"}
    prefix = "theorem α : True := by\n  "
    before = tactic + (" only" if only else "") + " "
    code = prefix + before + "[" + ", ".join(arguments) + "]" + suffix
    start, opening, closing = len(prefix), len(prefix + before), len(code) - len(suffix)
    path = [1, 0]
    nodes = [{"kind": kinds[tactic], "path": path, "start": start, "end": len(code)}]
    if only and tactic in {"simp", "simp_all", "dsimp"}:
        nodes.append({"kind": "null", "path": path + [3], "start": start + len(tactic) + 1,
                      "end": start + len(tactic) + 5})
    if tactic in {"linarith", "nlinarith"}:
        nodes.append({"kind": "Mathlib.Tactic.linarithArgsRest", "path": path + [2],
                      "start": start + len(tactic) + 1, "end": closing})
        list_path = path + [2, 2]
    else:
        list_path = path + [2 if tactic == "rw" else 4]
    nodes.append({"kind": "Lean.Parser.Tactic.rwRuleSeq" if tactic == "rw" else "null",
                  "path": list_path, "start": opening, "end": closing})
    if arguments:
        nodes.append({"kind": "null", "path": list_path + [1], "start": opening + 1,
                      "end": closing - 1})
    offset = opening + 1
    for i, argument in enumerate(arguments):
        if tactic in {"simp", "simp_all", "dsimp", "rw"} or i in compound_indices:
            kind = ("Lean.Parser.Tactic.rwRule" if tactic == "rw" else
                    "Lean.Parser.Tactic.simpLemma" if tactic in {"simp", "simp_all", "dsimp"}
                    else "Lean.Parser.Term.app")
            nodes.append({"kind": kind, "path": list_path + [1, 2 * i],
                          "start": offset, "end": offset + len(argument)})
        offset += len(argument) + 2
    return code, {"nodes": nodes, "messages": []}


class LemmaMinimizationTests(unittest.TestCase):
    def test_preserves_only_location_and_unicode_character_offsets(self):
        code, analysis = fixture("simp", ["hα", "Nat.add_zero", "hβ"], only=True, suffix=" at hγ ⊢")
        site, = list_sites(code, analysis)
        candidate = site.remove(code, 1, 2).apply(code)
        self.assertEqual(candidate, code.replace("[hα, Nat.add_zero, hβ]", "[hα, hβ]"))
        self.assertEqual(site.remove(code, 0, 3).apply(code), code.replace("[hα, Nat.add_zero, hβ]", "[]"))

    def test_unrestricted_simp_is_a_separate_experiment(self):
        code, analysis = fixture("simp", ["h", "rfl"])
        self.assertEqual(list_sites(code, analysis), [])

    def test_nested_term_commas_do_not_split_arguments(self):
        arguments = ["(show ∀ x, x ∈ [1, 2] → x ≤ 2 by decide)", "h", "sq_nonneg (x - y)"]
        code, analysis = fixture("nlinarith", arguments, only=True, compound_indices=(0, 2))
        site, = list_sites(code, analysis)
        self.assertEqual(len(site.elements), 3)
        self.assertEqual(site.remove(code, 1, 3).apply(code),
                         code.replace("[" + ", ".join(arguments) + "]", "[" + arguments[0] + "]"))

    def test_arithmetic_identifier_atoms_need_not_have_ast_nodes(self):
        code, analysis = fixture("linarith", ["h₁", "h₂", "mul_le_mul h₃ h₄"], compound_indices=(2,))
        site, = list_sites(code, analysis, families=("arithmetic",))
        self.assertEqual(len(site.elements), 3)
        self.assertEqual(site.remove(code, 0, 2).apply(code), code.replace("[h₁, h₂, mul_le_mul h₃ h₄]", "[ mul_le_mul h₃ h₄]"))

    def test_nested_comments_in_unobserved_gaps_remain_well_formed(self):
        code, analysis = fixture("linarith", ["h₁ /- , /- nested ] , -/ -/", "-- comma ,\n  h₂", "h₃"])
        site, = list_sites(code, analysis)
        self.assertEqual(len(site.elements), 3)
        candidate = site.remove(code, 0, 1).apply(code)
        self.assertIn("[ -- comma ,\n  h₂, h₃]", candidate)
        self.assertNotIn("nested", candidate)

    def test_quoted_identifier_comma_is_not_a_separator(self):
        code, analysis = fixture("linarith", ["«h,one»", "h₂"])
        site, = list_sites(code, analysis)
        self.assertEqual(len(site.elements), 2)
        self.assertIn("[«h,one»]", site.remove(code, 1, 2).apply(code))

    def test_rewrite_retains_order_and_reverse_direction(self):
        code, analysis = fixture("rw", ["← h₁", "foo (a, b)", "h₂"], suffix=" at h")
        site, = list_sites(code, analysis, families=("rewrite",))
        self.assertEqual(site.remove(code, 1, 2).apply(code), code.replace("[← h₁, foo (a, b), h₂]", "[← h₁, h₂]"))
        self.assertEqual(list_sites(code, analysis, families=("simp",)), [])

    def test_empty_lists_and_unsupported_shapes_produce_no_edits(self):
        code, analysis = fixture("simp", [], only=True)
        self.assertEqual(minimization_groups(code, analysis), [])
        code, analysis = fixture("linarith", ["foo (x, y)", "h"])
        self.assertEqual(list_sites(code, analysis), [])  # Missing compound AST span.

    def test_nested_lists_are_not_separate_sites(self):
        code, analysis = fixture("simp", ["show xs = [1, 2] from h", "List.length_cons"], only=True)
        parent = analysis["nodes"][-2]
        start = code.index("[1, 2]")
        analysis["nodes"].append({"kind": "null", "path": parent["path"] + [0, 1],
                                  "start": start, "end": start + len("[1, 2]")})
        self.assertEqual(len(list_sites(code, analysis)), 1)

    def test_partition_schedule_includes_all_singles_without_duplicates(self):
        for size in range(1, 20):
            chunks = list(deletion_chunks(size))
            self.assertEqual(chunks[0], (0, size))
            self.assertEqual(len(set(chunks)), len(chunks))
            self.assertTrue({(i, i + 1) for i in range(size)} <= set(chunks))
        self.assertEqual(list(deletion_chunks(0)), [])

    def test_alternatives_are_never_bundled_as_simultaneous_edits(self):
        code, analysis = fixture("simp_all", ["h₁", "h₂", "h₃"], only=True)
        groups = minimization_groups(code, analysis)
        self.assertTrue(all(len(group) == 1 for group in groups))
        self.assertIn("simp_all only []", groups[0][0].apply(code))
        self.assertEqual(len({group[0].apply(code) for group in groups}), len(groups))

    def test_invalid_family_and_deletion_ranges_rejected(self):
        code, analysis = fixture("simp", ["h"], only=True)
        site, = list_sites(code, analysis)
        for first, stop in [(-1, 1), (0, 0), (0, 2)]:
            with self.assertRaises(ValueError):
                site.remove(code, first, stop)
        with self.assertRaises(ValueError):
            list_sites(code, analysis, families=("imaginary",))

    def test_unused_argument_diagnostic_prioritizes_exact_list_member(self):
        code, analysis = fixture("simp", ["first", "redundant", "last"], only=True)
        start = code.index("redundant")
        analysis["messages"] = [{"kind": "linter.unusedSimpArgs", "start": start,
                                  "end": start + len("redundant")}]
        groups = minimization_groups(code, analysis)
        self.assertIn("[first, last]", groups[0][0].apply(code))
        self.assertIn("[]", minimization_groups(code, analysis, prioritize_unused=False)[0][0].apply(code))
        self.assertEqual(len(groups), len({g[0] for g in groups}))


if __name__ == "__main__":
    unittest.main()
