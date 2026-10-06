"""Focusing rewrites: fuse a phase of sibling steps into one step.

Synchronous phase: a skeleton step (`constructor`, `exists w`, `use w`,
`refine t` or `apply t` with `?_` holes) followed by steps that fill each hole
in goal order becomes one `exact` of the filled term.

Asynchronous phase: `intro … h` (or a destructuring pattern binding `h`)
followed by `obtain pat := h` / `rcases h with pat` becomes one pattern.
Consecutive `intro`s become one.

These are candidates. `constructor` may create more than two goals, `use`
can close side goals by `rfl`, and term elaboration order differs from tactic
order; Lean must check every rewrite on every required version.
"""

from __future__ import annotations

import re

from proof_eval.optimization.proof_theory.spans import (
    HOLE,
    closing_term,
    fill_hole,
    is_bullet,
    replace_steps,
    single_line,
    split_top,
    token_spans,
    wrapped,
)
from proof_eval.optimization.proof_theory.tree import Step
from proof_eval.optimization.syntax import Edit

_WITNESS = re.compile(r"(?:exists|use)\s+(.+)")
_REFINE = re.compile(r"(?:refine|apply)\s+(.+)")
_INTRO = re.compile(r"(intro|rintro)\s+(.+)")
_OBTAIN = re.compile(r"obtain\s+(.+?)\s*:=\s*([\w'.]+)")
_RCASES = re.compile(r"rcases\s+([\w'.]+)\s+with\s+(.+)")


def skeleton(step: Step) -> str | None:
    """The proof term with `?_` holes that a goal-splitting step stands for."""
    if is_bullet(step) or not single_line(step):
        return None
    tactic = step.tactic.strip()
    if tactic == "constructor":
        return "⟨?_, ?_⟩"
    witness = _WITNESS.fullmatch(tactic)
    if witness:
        return "⟨" + ", ".join(split_top(witness.group(1)) + [HOLE]) + "⟩"
    refine = _REFINE.fullmatch(tactic)
    if refine and HOLE in refine.group(1):
        return refine.group(1).strip()
    return None


def _fuse_from(children: list[Step], start: int) -> tuple[int, str] | None:
    """Fill holes left to right; return the last consumed index and the term."""
    term = skeleton(children[start])
    index = start
    while term is not None and HOLE in term and index + 1 < len(children):
        index += 1
        step = children[index]
        filler = skeleton(step) or closing_term(step)
        if filler is None:
            return None
        term = fill_hole(term, filler)
    if term is None or HOLE in term:
        return None
    return index, term


def synchronous_groups(root: Step) -> list[list[Edit]]:
    """Maximal fusions only: a run inside an earlier fused run is skipped."""
    groups = []
    for parent in root.walk():
        children = parent.children
        covered = -1
        for start in range(len(children)):
            fused = None if start <= covered else _fuse_from(children, start)
            if fused is None:
                continue
            stop, term = fused
            covered = stop
            groups.append(
                [
                    replace_steps(
                        children[start : stop + 1],
                        "exact " + term,
                        f"fuse_synchronous_phase:{stop - start + 1}",
                    )
                ]
            )
    return groups


def _pattern(text: str) -> str:
    """An rcases pattern usable as one `rintro`/`obtain` argument."""
    text = text.strip()
    return text if wrapped(text) or " " not in text else f"({text})"


def _binder(step: Step) -> tuple[str, str, str] | None:
    """(keyword, binder text, suffix) of an intro-like step."""
    if is_bullet(step) or not single_line(step):
        return None
    tactic = step.tactic.strip()
    intro = _INTRO.fullmatch(tactic)
    if intro:
        return intro.group(1), intro.group(2), ""
    obtain = _OBTAIN.fullmatch(tactic)
    if obtain and wrapped(obtain.group(1), "⟨"):
        return "obtain", obtain.group(1), " := " + obtain.group(2)
    return None


def _destructured(step: Step) -> tuple[str, str] | None:
    """(hypothesis name, pattern) of a destructuring step."""
    if is_bullet(step) or not single_line(step):
        return None
    tactic = step.tactic.strip()
    obtain = _OBTAIN.fullmatch(tactic)
    if obtain:
        return obtain.group(2), obtain.group(1)
    rcases = _RCASES.fullmatch(tactic)
    if rcases:
        return rcases.group(1), rcases.group(2)
    return None


def _fuse_pair(first: Step, second: Step) -> tuple[str, str] | None:
    binder = _binder(first)
    if binder is None:
        return None
    keyword, binders, suffix = binder
    later = _INTRO.fullmatch(second.tactic.strip()) if single_line(second) else None
    if keyword in {"intro", "rintro"} and later and not is_bullet(second):
        merged = "rintro" if "rintro" in {keyword, later.group(1)} else "intro"
        return merged + " " + binders + " " + later.group(2), "merge_intros"
    destructured = _destructured(second)
    if destructured is None:
        return None
    name, pattern = destructured
    spans = token_spans(binders, name)
    if len(spans) != 1:
        return None
    a, b = spans[0]
    replaced = binders[:a] + _pattern(pattern) + binders[b:]
    keyword = "rintro" if keyword == "intro" else keyword
    return keyword + " " + replaced + suffix, "fuse_asynchronous_phase"


def asynchronous_groups(root: Step) -> list[list[Edit]]:
    groups = []
    for parent in root.walk():
        for first, second in zip(parent.children, parent.children[1:]):
            fused = _fuse_pair(first, second)
            if fused:
                text, reason = fused
                groups.append([replace_steps([first, second], text, reason)])
    return groups
