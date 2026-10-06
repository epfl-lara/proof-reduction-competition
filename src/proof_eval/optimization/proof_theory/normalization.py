"""Normalization rewrites: remove detours and inline single-use cuts.

`by exact t` becomes `t`; `fun x => f x` becomes `f`; `intro x; exact f x`
becomes `exact f`; a final `apply f; exact t` becomes `exact f t`. A `have`
proved by a term and mentioned once later is inlined at that mention.
Elaboration order and expected types change in every case, so each rewrite is
only a candidate for whole-declaration checks.
"""

from __future__ import annotations

import re

from proof_eval.optimization.proof_theory.cuts import CUT, binding
from proof_eval.optimization.proof_theory.spans import (
    HOLE,
    closing_term,
    delete_step,
    is_bullet,
    parenthesize,
    replace_steps,
    single_line,
    token_spans,
)
from proof_eval.optimization.proof_theory.tree import Step
from proof_eval.optimization.syntax import Edit

_BY_EXACT = re.compile(r"(?:\(|:=)[ \t]*(by[ \t]+exact[ \t]+)(?=\S)")
_FUN_ETA = re.compile(
    r"\bfun\s+([\w']+)\s*=>\s*([\w.']+)\s+\1(?![\w'.])(?=\s*(?:[),]|$))", re.M
)


def _owner(root: Step, offset: int) -> Step | None:
    """The innermost step whose own text contains `offset`."""
    owner = None
    for step in root.walk():
        if step is not root and step.start <= offset < step.end:
            owner = step
    return owner


def by_exact_groups(root: Step, body: str) -> list[list[Edit]]:
    groups = []
    top = root.children
    if len(top) == 1 and body.lstrip().startswith("by") and not top[0].children:
        term = re.fullmatch(r"exact\s+(.+)", top[0].tactic, re.S)
        if term:
            groups.append([Edit(0, len(body), term.group(1).strip(), "by_exact")])
    for match in _BY_EXACT.finditer(body):
        owner = _owner(root, match.start(1))
        if owner is None or ";" in body[match.end(1) : owner.end].split("\n")[0]:
            continue  # `by exact p; tac` or `<;>`: the block has more tactics.
        if match.group().startswith(":=") and owner.children:
            continue
        groups.append([Edit(match.start(1), match.end(1), "", "by_exact")])
    return groups


def fun_eta_groups(body: str) -> list[list[Edit]]:
    return [
        [Edit(m.start(), m.end(), m.group(2), "fun_eta")]
        for m in _FUN_ETA.finditer(body)
    ]


def _adjacent(first: Step, second: Step, last: bool) -> Edit | None:
    if is_bullet(first) or not (single_line(first) and single_line(second)):
        return None
    a, b = first.tactic.strip(), second.tactic.strip()
    intro = re.fullmatch(r"intros?\s+([\w']+)", a)
    applied = re.fullmatch(r"exact\s+(.+?)\s+([\w']+)", b)
    if intro and applied and applied.group(2) == intro.group(1):
        function = applied.group(1)
        if not token_spans(function, intro.group(1)):
            return replace_steps([first, second], "exact " + function, "intro_eta")
    apply = re.fullmatch(r"apply\s+(.+)", a)
    term = closing_term(second)
    if last and apply and term and HOLE not in a and not is_bullet(second):
        replacement = f"exact {apply.group(1).strip()} {parenthesize(term)}"
        return replace_steps([first, second], replacement, "apply_exact")
    return None


def adjacent_groups(root: Step) -> list[list[Edit]]:
    groups = []
    for parent in root.walk():
        children = parent.children
        for first, second in zip(children, children[1:]):
            edit = _adjacent(first, second, second is children[-1])
            if edit:
                groups.append([edit])
    return groups


def _inline(parent: Step, index: int, body: str) -> list[Edit] | None:
    step = parent.children[index]
    match = CUT.match(step.tactic)
    if not match or match.group(1) != "have" or not single_line(step):
        return None
    names, _, proof = binding("have", step.tactic[match.end() :])
    proof = proof.strip()
    if len(names) != 1 or not proof or re.match(r"by\b", proof):
        return None
    later = parent.children[index + 1 :]
    if not later:
        return None
    start, stop = later[0].start, later[-1].stop()
    uses = token_spans(body[start:stop], names[0])
    if len(uses) != 1:
        return None
    a, b = uses[0]
    return [
        delete_step(body, step, "inline_linear_cut:" + names[0]),
        Edit(start + a, start + b, parenthesize(proof), "inline_linear_cut"),
    ]


def inline_groups(root: Step, body: str) -> list[list[Edit]]:
    groups = []
    for parent in root.walk():
        for index in range(len(parent.children)):
            edits = _inline(parent, index, body)
            if edits:
                groups.append(edits)
    return groups
