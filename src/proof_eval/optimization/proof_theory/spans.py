"""Body-coordinate helpers shared by the proof-theoretic rewrites.

All offsets index the proof body. Replacement text is taken from the
comment-masked body, so comments inside a rewritten span are dropped.
"""

from __future__ import annotations

import re

from proof_eval.optimization.proof_theory.tree import Step
from proof_eval.optimization.syntax import Edit

HOLE = "?_"
_CLOSE = {"(": ")", "[": "]", "{": "}", "⟨": "⟩"}
_ATOM = re.compile(r"[\w'.]+|‹_›")


def is_bullet(step: Step) -> bool:
    return step.text.lstrip().startswith(("·", "."))


def single_line(step: Step) -> bool:
    """One self-contained tactic: no children, continuation or combinators."""
    tactic = step.tactic
    return (
        not step.children
        and "\n" not in step.text
        and "<;>" not in tactic
        and ";" not in tactic
    )


def closing_term(step: Step) -> str | None:
    """The term a goal-closing step supplies, when that is syntactically clear.

    `apply f` is accepted only as a candidate: `exact f` is equivalent when `f`
    leaves no goals, which Lean must confirm.
    """
    if not single_line(step):
        return None
    tactic = step.tactic.strip()
    match = re.fullmatch(r"(?:exact|apply)\s+(.+)", tactic)
    if match:
        return match.group(1).strip()
    return {"assumption": "‹_›", "rfl": "rfl", "trivial": "trivial"}.get(tactic)


def _matching(text: str, start: int) -> int:
    """Index of the bracket closing `text[start]`, or -1."""
    depth = 0
    opener = text[start]
    for i in range(start, len(text)):
        if text[i] == opener:
            depth += 1
        elif text[i] == _CLOSE[opener]:
            depth -= 1
            if depth == 0:
                return i
    return -1


def wrapped(term: str, opener: str = "") -> bool:
    """Whether one bracket pair encloses the whole term."""
    term = term.strip()
    if not term or term[0] not in _CLOSE or (opener and term[0] != opener):
        return False
    return _matching(term, 0) == len(term) - 1


def parenthesize(term: str) -> str:
    term = term.strip()
    return term if _ATOM.fullmatch(term) or wrapped(term) else f"({term})"


def split_top(text: str, separator: str = ",") -> list[str]:
    """Split on separators outside brackets, dropping empty parts."""
    parts, depth, current = [], 0, ""
    for char in text:
        if char in _CLOSE:
            depth += 1
        elif char in _CLOSE.values():
            depth -= 1
        if char == separator and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    parts.append(current.strip())
    return [part for part in parts if part]


def fill_hole(term: str, filler: str) -> str:
    """Fill the first `?_`, parenthesizing unless the hole is a delimited slot.

    A slot sits between `⟨`/`(`/`,` and `,`/`⟩`/`)`. A final anonymous-
    constructor slot is flattened: `⟨a, ?_⟩` filled with `⟨b, c⟩` becomes
    `⟨a, b, c⟩`, which Lean reads the same way.
    """
    index = term.find(HOLE)
    if index < 0:
        raise ValueError("No hole to fill")
    before, after = term[:index].rstrip(), term[index + len(HOLE) :]
    slot = before[-1:] in {"⟨", "(", ","} and after.lstrip()[:1] in {",", "⟩", ")"}
    if not slot:
        filler = parenthesize(filler)
    elif after.lstrip().startswith("⟩") and wrapped(filler, "⟨"):
        filler = filler.strip()[1:-1].strip()
    return term[:index] + filler + after


def replace_steps(steps: list[Step], replacement: str, reason: str) -> Edit:
    """Replace consecutive sibling subtrees, keeping the first step's column."""
    return Edit(steps[0].start, steps[-1].stop(), replacement, reason)


def delete_step(body: str, step: Step, reason: str) -> Edit:
    """Delete a step's whole lines and exactly one adjacent line break."""
    start, stop = step.line_start, step.stop()
    if body[stop : stop + 1] == "\n":
        stop += 1
    elif start and body[start - 1] == "\n":
        start -= 1
    return Edit(start, stop, "", reason)


def token_spans(text: str, name: str) -> list[tuple[int, int]]:
    """Whole-identifier occurrences of `name`, excluding field projections."""
    pattern = rf"(?<![\w'.]){re.escape(name)}(?![\w'])"
    return [m.span() for m in re.finditer(pattern, text)]
