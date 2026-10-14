"""Detours: introductions immediately eliminated (beta and eta redexes)."""

from __future__ import annotations

import re

from proof_eval.optimization.proof_theory.records import Detour
from proof_eval.optimization.proof_theory.tree import Step, blocks

_PATTERNS = (
    ("by_exact", r"\bby\s+exact\b"),
    ("exact_by", r"\bexact\s+\(\s*by\b"),
    ("show_from", r"\bshow\b[^\n]*\bfrom\b"),
    ("fun_eta", r"\bfun\s+([\w']+)\s*=>\s*[\w.']+\s+\1(?![\w'])\s*(?=[)\n,]|$)"),
)


def _adjacent(first: Step, second: Step, last: bool) -> list[Detour]:
    """Redexes formed by two consecutive sibling steps."""
    a, b = first.tactic, second.tactic
    found = []
    bound = re.match(r"(?:have|let)\s+([^\s:(⟨]+)", a)
    if bound and b == "exact " + bound.group(1):
        found.append(Detour("have_exact", first.line, a))
    intro = re.fullmatch(r"intros?\s+([\w']+)", a)
    if intro and re.fullmatch(rf"exact\s+.+\s+{re.escape(intro.group(1))}", b):
        found.append(Detour("intro_exact_eta", first.line, a))
    if last and re.fullmatch(r"apply\s+\S+", a) and b.startswith("exact "):
        found.append(Detour("apply_exact", first.line, a))
    if a.startswith(("rw", "rewrite")) and " at " in a:
        if re.fullmatch(r"exact\s+[\w'.]+", b):
            found.append(Detour("rewrite_at_exact", first.line, a))
    return found


def find_detours(root: Step, body: str) -> list[Detour]:
    found = []
    for children in blocks(root):
        for a, b in zip(children, children[1:]):
            found.extend(_adjacent(a, b, b is children[-1]))
    for kind, pattern in _PATTERNS:
        for match in re.finditer(pattern, body):
            line = body.count("\n", 0, match.start()) + 1
            found.append(Detour(kind, line, match.group()))
    return sorted(found, key=lambda d: (d.line, d.kind))
