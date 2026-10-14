"""Deletion candidates: steps, combinator tails and `try` wrappers.

The linter-based method only removes tactics Lean reports as unused. Many
other steps are redundant after later automation (`simp at h` before
`simp_all`, a rewrite that a closing tactic would also find). This module
proposes deleting each non-final, non-binding step, the tail of `A <;> B`, and
the `try` around a step. Deletion of the final step of a block, of branches and
of binding or goal-shaping steps is never proposed, since Lean would reject it.
Candidates are ordered by tokens saved; Lean decides which are valid.
"""

from __future__ import annotations

import re

from proof_eval.optimization.proof_theory.spans import delete_step, is_bullet
from proof_eval.optimization.proof_theory.tree import (
    CASE_HEADER,
    Step,
    blocks,
    find_top,
)
from proof_eval.optimization.syntax import Edit
from proof_eval.verification.metrics import token_count

# Steps that bind names, split or shape goals, or open a branch.
_KEEP = re.compile(
    r"(?:have|haveI|let|letI|obtain|rcases|set|intro|intros|rintro|case|next|"
    r"by_cases|by_contra|induction|fun_induction|cases|refine|refine'|"
    r"constructor|use|exists|calc|show|suffices|generalize|ext|funext|"
    r"specialize|left|right|exfalso|split|split_ifs|match|conv)\b"
)
_TRY = re.compile(r"try\s+(.+)", re.S)
# Tactic names start with a lowercase ASCII letter; term continuation lines of a
# multi-line expression (operators, brackets, `ι ...`) never qualify.
_TACTIC = re.compile(r"[a-z]")


def _deletable(step: Step) -> bool:
    return bool(_TACTIC.match(step.tactic)) and not (
        is_bullet(step) or CASE_HEADER.match(step.text) or _KEEP.match(step.tactic)
    )


def _tail_edit(body: str, step: Step) -> Edit | None:
    """Drop the last top-level `<;> B` of a one-line step."""
    if step.children or "\n" in step.text:
        return None
    text = body[step.start : step.end]
    cut, offset = -1, 0
    while True:
        found = find_top(text[offset:], "<;>")
        if found < 0:
            break
        cut, offset = offset + found, offset + found + 3
    if cut <= 0 or not text[:cut].strip():
        return None
    start = step.start + len(text[:cut].rstrip())
    return Edit(start, step.end, "", "delete_combinator_tail")


def deletion_groups(root: Step, body: str) -> list[list[Edit]]:
    scored = []
    for children in blocks(root):
        for index, step in enumerate(children):
            last = index == len(children) - 1
            if not last and len(children) > 1 and _deletable(step):
                edit = delete_step(body, step, "delete_step:" + step.head)
                scored.append((token_count(body[step.start : step.stop()]), [edit]))
            tail = _tail_edit(body, step)
            if tail is not None:
                saved = token_count(body[tail.start : tail.end])
                scored.append((saved, [tail]))
            wrapped = _TRY.fullmatch(step.tactic.strip())
            if wrapped and not step.children and "\n" not in step.text:
                inner = wrapped.group(1).strip()
                if inner.startswith("("):
                    continue
                edit = Edit(step.start, step.end, inner, "unwrap_try")
                if is_bullet(step):
                    edit = Edit(step.start, step.end, "· " + inner, "unwrap_try")
                scored.append((1, [edit]))
    scored.sort(key=lambda item: (-item[0], item[1][0].start))
    return [group for _, group in scored]
