"""Safety boundaries for syntax-guided local-fact transformations."""
import unittest

from proof_eval.structural import fact_reuse, local_fact_deletions, wrappers


def node(kind, path, start, end):
    return {"kind": kind, "path": path, "start": start, "end": end}


class SyntaxFixture:
    """Minimal observer nodes matching Lean 4's actual have/let parser shape.

    Endpoints are supplied explicitly: this helper deliberately does not parse
    indentation, identify proof boundaries, or implement any transformations.
    """
    def __init__(self, code):
        self.code = code
        self.nodes = [node("null", [0], 0, len(code))]

    def binding(self, name, rhs, *, keyword="have", type_text="", ordinal=0,
                scope=None, occurrence=0, body=None, parameterized=False):
        start = -1
        for _ in range(occurrence + 1):
            start = self.code.index(keyword + " " + name, start + 1)
        rhs_start = self.code.index(":=", start) + 2
        while self.code[rhs_start].isspace():
            rhs_start += 1
        assert self.code[rhs_start:rhs_start + len(rhs)] == rhs
        end = rhs_start + len(rhs)
        path = (scope or [0]) + [ordinal]
        base = path + [2, 0]
        name_start = start + len(keyword) + 1
        name_end = name_start + len(name)
        self.nodes.extend([
            node("Lean.Parser.Tactic.tacticHave__" if keyword == "have" else "Lean.Parser.Tactic.tacticLet__", path, start, end),
            node("Lean.Parser.Term.letIdDecl", base, name_start, end),
            node("Lean.Parser.Term.letId", base + [0], name_start, name_end),
        ])
        if type_text:
            type_start = self.code.index(type_text, name_end)
            self.nodes.append(node("null", base + [2], type_start, type_start + len(type_text)))
        if parameterized:
            left = self.code.index("(", name_end)
            right = self.code.index(")", left) + 1
            self.nodes.append(node("null", base + [1], left, right))
        if rhs.startswith("by"):
            self.nodes.append(node("Lean.Parser.Term.byTactic", base + [4], rhs_start, end))
            if body is not None:
                begin = self.code.index(body, rhs_start)
                self.nodes.append(node("Lean.Parser.Tactic.tacticSeq", base + [4, 1], begin, begin + len(body)))
        elif " " in rhs:
            self.nodes.append(node("Lean.Parser.Term.app", base + [4], rhs_start, end))
        return path

    def exact(self, text, *, scope=None, ordinal=1, occurrence=0):
        start = -1
        for _ in range(occurrence + 1):
            start = self.code.index(text, start + 1)
        self.nodes.append(node("Lean.Parser.Tactic.exact", (scope or [0]) + [ordinal], start, start + len(text)))

    @property
    def analysis(self):
        return {"nodes": self.nodes, "messages": []}


class WrapperTests(unittest.TestCase):
    def test_multiline_unicode_wrapper_keeps_statement_and_indentation(self):
        code = "theorem π : True := by\n  have α : True := by\n    have β := True.intro\n    exact β\n  exact α\n"
        f = SyntaxFixture(code)
        body = "have β := True.intro\n    exact β"
        f.binding("α", "by\n    " + body, type_text=": True", body=body)
        f.exact("exact α")
        edits = wrappers(code, f.analysis)
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0].apply(code), "theorem π : True := by\n  have β := True.intro\n  exact β\n")

    def test_comments_do_not_prevent_adjacent_contraction(self):
        code = "by have h := hp; /- comment exact other -/ exact h"
        f = SyntaxFixture(code)
        f.binding("h", "hp")
        f.exact("exact h")
        self.assertEqual(wrappers(code, f.analysis)[0].apply(code), "by exact hp")

    def test_intervening_tactic_and_applied_fact_are_not_wrappers(self):
        for ending in ("skip\n  exact h", "exact h 0"):
            code = "by\n  have h := hp\n  " + ending
            f = SyntaxFixture(code)
            f.binding("h", "hp")
            f.exact("exact h" + (" 0" if ending.endswith(" 0") else ""))
            self.assertEqual(wrappers(code, f.analysis), [])

    def test_different_scope_cannot_be_contracted(self):
        code = "by\n  have h := hp\n  constructor\n  · exact h\n  · exact h"
        f = SyntaxFixture(code)
        f.binding("h", "hp")
        f.exact("exact h", scope=[0, 7])
        self.assertEqual(wrappers(code, f.analysis), [])

    def test_nested_bullet_keeps_sibling_goal_and_bullet_prefix(self):
        code = "by\n  constructor\n  · have h := by\n      trivial\n    exact h\n  · trivial"
        f = SyntaxFixture(code)
        scope = [0, 3, 1, 0, 0]
        f.nodes.append(node("null", scope, code.index("have h"), code.index("\n  · trivial")))
        f.binding("h", "by\n      trivial", scope=scope, body="trivial")
        f.exact("exact h", scope=scope)
        self.assertEqual(wrappers(code, f.analysis)[0].apply(code), "by\n  constructor\n  · trivial\n  · trivial")

    def test_parameterized_local_fact_is_not_flattened(self):
        code = "by\n  have h (n : Nat) : n = n := by rfl\n  exact h"
        f = SyntaxFixture(code)
        f.binding("h", "by rfl", type_text=": n = n", body="rfl", parameterized=True)
        f.exact("exact h")
        self.assertEqual(wrappers(code, f.analysis), [])


class LocalDeletionTests(unittest.TestCase):
    def test_implicit_omega_use_is_only_a_hint_never_a_certified_deletion(self):
        code = "by\n  have explicit := hp\n  have implicit := hq\n  have long_name := hr\n  exact explicit\n  omega"
        f = SyntaxFixture(code)
        f.binding("explicit", "hp", ordinal=0)
        f.binding("implicit", "hq", ordinal=2)
        f.binding("long_name", "hr", ordinal=4)
        edits = local_fact_deletions(code, f.analysis)
        self.assertEqual(len(edits), 3)
        self.assertIn("text_nonreference", edits[0].reason)
        self.assertIn("text_reference:explicit", edits[-1].reason)
        self.assertTrue(any("implicit" in e.reason for e in edits))

    def test_reference_hint_ignores_comments_strings_and_identifier_substrings(self):
        code = 'by\n  have h := hp\n  have hh := "h"\n  -- h\n  /- h /- h -/ h -/\n  exact hh'
        f = SyntaxFixture(code)
        f.binding("h", "hp")
        self.assertIn("text_nonreference:h", local_fact_deletions(code, f.analysis)[0].reason)

    def test_semicolon_is_consumed_without_damaging_neighbor(self):
        code = "by have h := hp; exact hp"
        f = SyntaxFixture(code)
        f.binding("h", "hp")
        self.assertEqual(local_fact_deletions(code, f.analysis)[0].apply(code), "by  exact hp")


class ReuseTests(unittest.TestCase):
    def test_identical_explicit_type_reuses_fact_despite_different_proofs(self):
        code = "by\n  have h₁ : True := by trivial\n  have h₂ : True := by constructor\n  exact h₂"
        f = SyntaxFixture(code)
        f.binding("h₁", "by trivial", type_text=": True")
        f.binding("h₂", "by constructor", type_text=": True", ordinal=2)
        edits = fact_reuse(code, f.analysis)
        self.assertTrue(any("have h₂ : True := h₁" in e.apply(code) for e in edits))

    def test_same_tactic_on_distinct_types_does_not_imply_same_fact(self):
        code = "by\n  have h₁ : 1 = 1 := by rfl\n  have h₂ : 2 = 2 := by rfl\n  exact h₂"
        f = SyntaxFixture(code)
        f.binding("h₁", "by rfl", type_text=": 1 = 1")
        f.binding("h₂", "by rfl", type_text=": 2 = 2", ordinal=2)
        self.assertEqual(fact_reuse(code, f.analysis), [])

    def test_identical_rhs_without_explicit_types_can_be_proposed(self):
        code = "by\n  have h₁ := Nat.zero_le 3\n  have h₂ := Nat.zero_le 3\n  exact h₂"
        f = SyntaxFixture(code)
        f.binding("h₁", "Nat.zero_le 3")
        f.binding("h₂", "Nat.zero_le 3", ordinal=2)
        self.assertTrue(any("have h₂ := h₁" in edit.apply(code) for edit in fact_reuse(code, f.analysis)))

    def test_alias_replaces_complete_identifiers_preserving_comments_literals(self):
        code = 'by\n  have h := hp\n  have hh := "h"\n  -- h is an alias\n  exact (h, hh, Namespace.h)'
        f = SyntaxFixture(code)
        f.binding("h", "hp")
        edits = fact_reuse(code, f.analysis)
        self.assertEqual(len(edits), 1)
        result = edits[0].apply(code)
        self.assertIn('have hh := "h"', result)
        self.assertIn("-- h is an alias", result)
        self.assertIn("exact (hp, hh, Namespace.h)", result)
        self.assertNotIn("have h :=", result)

    def test_duplicate_in_different_scope_is_not_reused(self):
        code = "by\n  have h₁ : True := by trivial\n  have h₂ : True := by trivial\n  exact h₂"
        f = SyntaxFixture(code)
        f.binding("h₁", "by trivial", type_text=": True")
        f.nodes.append(node("null", [9], code.index("have h₂"), len(code)))
        f.binding("h₂", "by trivial", type_text=": True", scope=[9])
        self.assertEqual(fact_reuse(code, f.analysis), [])


if __name__ == "__main__":
    unittest.main()
