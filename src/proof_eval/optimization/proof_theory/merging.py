"""Merge identical branches: the cheapest instance of cut introduction.

Sibling `case` branches with byte-identical bodies (up to whitespace) and the
same binders become `case a | b => …`. Identical bullets that end a block, and
so close exactly its remaining goals, become one `all_goals` block. Branches
equal only up to renaming are left to a later, Lean-checked generalization.
"""

from __future__ import annotations

import re

from proof_eval.optimization.proof_theory.spans import delete_step, is_bullet
from proof_eval.optimization.proof_theory.tree import Step, blocks
from proof_eval.optimization.syntax import Edit

_CASE = re.compile(r"case\s+([^\s|=]+)((?:\s+[^\s|=]+)*)\s*=>")


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _branch_body(body: str, step: Step, header_end: int) -> str:
    return _normalized(body[header_end : step.stop()])


def case_groups(root: Step, body: str) -> list[list[Edit]]:
    groups = []
    for children in blocks(root):
        branches: dict[tuple[str, str], list[tuple[Step, re.Match]]] = {}
        for step in children:
            match = _CASE.match(body, step.start)
            if not match or is_bullet(step):
                continue
            key = (_normalized(match.group(2)), _branch_body(body, step, match.end()))
            if key[1]:
                branches.setdefault(key, []).append((step, match))
        for same in branches.values():
            if len(same) < 2:
                continue
            first, header = same[0]
            tags = " | ".join(match.group(1) for _, match in same)
            edits = [Edit(header.start(1), header.end(1), tags, "merge_cases")]
            edits += [delete_step(body, step, "merge_cases") for step, _ in same[1:]]
            groups.append(edits)
    return groups


def _bullet_content(body: str, step: Step) -> str:
    """Bullet text after `·`, children kept at their own columns."""
    return body[step.start + 1 : step.stop()].strip()


def all_goals_groups(root: Step, body: str) -> list[list[Edit]]:
    groups = []
    for children in blocks(root):
        suffix = []
        for step in reversed(children):
            if not is_bullet(step):
                break
            suffix.insert(0, step)
        if len(suffix) < 2:
            continue
        contents = [_bullet_content(body, step) for step in suffix]
        if len({_normalized(content) for content in contents}) != 1:
            continue
        first = suffix[0]
        content = contents[0]
        if "\n" in content:
            replacement = "all_goals\n" + " " * (first.indent + 2) + content
        else:
            replacement = "all_goals " + content
        edits = [Edit(first.start, first.stop(), replacement, "merge_trailing_bullets")]
        edits += [
            delete_step(body, step, "merge_trailing_bullets") for step in suffix[1:]
        ]
        groups.append(edits)
    return groups
