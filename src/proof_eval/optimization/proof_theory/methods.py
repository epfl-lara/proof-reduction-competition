"""Registry of Lean-free proposal methods for the deterministic engine.

Each method maps a proof body to edit groups and names the engine's selection
policy. `joint_then_first` suits near-equivalent rewrites, which are first
tried together; `first_improvement` suits speculative candidates (deletions,
collapses, relaxations), which are tried one at a time in the given order.
"""

from __future__ import annotations

from typing import Any, Callable

from proof_eval.optimization.proof_theory.collapse import collapse_groups
from proof_eval.optimization.proof_theory.consolidate import (
    merge_groups,
    relax_groups,
)
from proof_eval.optimization.proof_theory.deletion import deletion_groups
from proof_eval.optimization.proof_theory.rewrites import (
    body_groups,
    declaration_groups,
    joint_group,
)
from proof_eval.optimization.proof_theory.tree import parse
from proof_eval.optimization.syntax import Edit, apply_edits
from proof_eval.optimization.token_golf import body_golf_groups
from proof_eval.verification.backend import _masked_comments
from proof_eval.verification.metrics import validate_candidate

Finder = Callable[[str], list[list[Edit]]]


def _on_tree(function) -> Finder:
    def finder(body: str) -> list[list[Edit]]:
        text = _masked_comments(body)
        return function(parse(text), text)

    return finder


METHODS: dict[str, tuple[Finder, str]] = {
    "proof_theory": (body_groups, "joint_then_first"),
    "golf": (body_golf_groups, "joint_then_first"),
    "collapse": (_on_tree(collapse_groups), "first_improvement"),
    "delete": (_on_tree(deletion_groups), "first_improvement"),
    "consolidate": (
        lambda body: merge_groups(parse(_masked_comments(body))),
        "joint_then_first",
    ),
    "relax": (lambda body: relax_groups(_masked_comments(body)), "first_improvement"),
}


def _valid(row: dict[str, Any], code: str) -> bool:
    try:
        validate_candidate(row, code)
    except ValueError:
        return False
    return True


def discover(
    method: str, row: dict[str, Any], code: str
) -> tuple[list[list[Edit]], str]:
    """Declaration-offset edit groups and the engine policy for `method`.

    Groups whose result fails declaration validation (for example, an edit that
    split a multi-line term the indentation parser misread) are dropped here,
    before they cost an engine trial.
    """
    finder, policy = METHODS[method]
    groups = [
        group
        for group in declaration_groups(row, code, finder)
        if _valid(row, apply_edits(code, group))
    ]
    if policy == "joint_then_first" and len(groups) > 1:
        groups.insert(0, joint_group(groups))
    return groups, policy
