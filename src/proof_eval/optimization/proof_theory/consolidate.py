"""Consolidation and relaxation of rewriting steps.

Consolidation merges consecutive rewrites at the same location:
`rw [a]` then `rw [b]` becomes `rw [a, b]`, which Lean treats the same way
except that it tries `rfl` once at the end. Consecutive `simp only` lists at the
same location are merged as a candidate too, although one simp call over the
union can behave differently.

Relaxation drops an explicit lemma list: `simp only [...]` becomes `simp`,
`norm_num [...]` becomes `norm_num`, `simpa only [...] using e` becomes
`simpa using e`. This saves many tokens but usually costs heartbeats; the
combined score decides. Lists containing `*` (all hypotheses) are kept.
"""

from __future__ import annotations

import re

from proof_eval.optimization.proof_theory.spans import (
    is_bullet,
    replace_steps,
    single_line,
)
from proof_eval.optimization.proof_theory.tree import Step
from proof_eval.optimization.syntax import Edit

_REWRITE = re.compile(r"(rw|rewrite|simp_rw|simp only)\s*\[(.*)\]\s*(at\s+.+)?")
_RELAX = re.compile(
    r"\b(simp_all|simpa|simp|dsimp|norm_num|field_simp)(\s+only)?\s*\[([^\[\]]*)\]"
)


def merge_groups(root: Step) -> list[list[Edit]]:
    groups = []
    for parent in root.walk():
        children = parent.children
        for first, second in zip(children, children[1:]):
            if is_bullet(first) or is_bullet(second):
                continue
            if not (single_line(first) and single_line(second)):
                continue
            a = _REWRITE.fullmatch(first.tactic.strip())
            b = _REWRITE.fullmatch(second.tactic.strip())
            if not (a and b) or a.group(1) != b.group(1):
                continue
            if (a.group(3) or "").split() != (b.group(3) or "").split():
                continue
            if not a.group(2).strip() or not b.group(2).strip():
                continue
            merged = f"{a.group(1)} [{a.group(2).strip()}, {b.group(2).strip()}]"
            if a.group(3):
                merged += " " + " ".join(a.group(3).split())
            groups.append([replace_steps([first, second], merged, "merge_rewrites")])
    return groups


def relax_groups(body: str) -> list[list[Edit]]:
    groups = []
    for match in _RELAX.finditer(body):
        if "*" in match.group(3):
            continue
        groups.append([Edit(match.start(), match.end(), match.group(1), "relax_simp")])
    groups.sort(key=lambda g: (-(g[0].end - g[0].start), g[0].start))
    return groups
