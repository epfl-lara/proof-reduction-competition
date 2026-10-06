"""Proof-theoretic rewrite proposals as declaration-offset edit groups.

Each group is one candidate proof: its edits must be applied together. Groups
are alternatives on one unchanged incumbent and may overlap. No group is a
verified improvement; the engine compiles and scores every candidate on every
required version before accepting it.
"""

from __future__ import annotations

from typing import Any, Callable

from proof_eval.optimization.proof_theory.fusion import (
    asynchronous_groups,
    synchronous_groups,
)
from proof_eval.optimization.proof_theory.merging import all_goals_groups, case_groups
from proof_eval.optimization.proof_theory.normalization import (
    adjacent_groups,
    by_exact_groups,
    fun_eta_groups,
    inline_groups,
)
from proof_eval.optimization.proof_theory.tree import parse
from proof_eval.optimization.syntax import Edit
from proof_eval.verification.backend import _masked_comments
from proof_eval.verification.metrics import validate_candidate


def body_groups(body: str) -> list[list[Edit]]:
    """Edit groups in body offsets, ordered by position then reason."""
    text = _masked_comments(body)
    root = parse(text)
    groups = (
        synchronous_groups(root)
        + asynchronous_groups(root)
        + case_groups(root, text)
        + all_goals_groups(root, text)
        + by_exact_groups(root, text)
        + fun_eta_groups(text)
        + adjacent_groups(root)
        + inline_groups(root, text)
    )
    unique = {tuple(sorted(group, key=lambda e: e.start)): None for group in groups}
    return sorted(
        (list(group) for group in unique),
        key=lambda g: (g[0].start, g[0].reason, g[0].end),
    )


def declaration_groups(
    row: dict[str, Any], code: str, finder: Callable[[str], list[list[Edit]]]
) -> list[list[Edit]]:
    """Map body-offset groups from `finder` onto a validated full declaration."""
    _, body = validate_candidate(row, code)
    offset = code.rindex(body)
    return [
        [Edit(e.start + offset, e.end + offset, e.replacement, e.reason) for e in group]
        for group in finder(body)
    ]


def proof_theory_groups(row: dict[str, Any], code: str) -> list[list[Edit]]:
    """Edit groups on a full declaration whose statement matches `row`."""
    return declaration_groups(row, code, body_groups)


def joint_group(groups: list[list[Edit]]) -> list[Edit]:
    """Greedily combine whole groups whose edits never overlap."""
    chosen: list[Edit] = []
    for group in groups:
        if all(e.end <= c.start or c.end <= e.start for e in group for c in chosen):
            chosen.extend(group)
    return sorted(chosen, key=lambda e: e.start)
