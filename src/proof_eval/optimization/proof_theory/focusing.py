"""Focusing phases: runs of invertible or of committed sibling steps.

Asynchronous steps (introduction, destructuring of hypotheses, extensionality)
are invertible and never need backtracking. Synchronous steps commit to a
witness or disjunct. `constructor` is neutral and may join either run.
"""

from __future__ import annotations

import re

from proof_eval.optimization.proof_theory.records import AnalysisConfig, Phase
from proof_eval.optimization.proof_theory.tree import Step, TokenCounter, blocks

_ASYNC = re.compile(
    r"(?:intros?|rintro|ext|funext|by_contra|split_ands|and_intros)\b"
    r"|refine'?\s*⟨\s*\?_"
    r"|obtain\s*⟨[^⟩]*⟩\s*:=\s*[\w'.]+$"
    r"|rcases\s+[\w'.]+\s+with\b"
    r"|cases\s+[\w'.]+$"
)
_CHOICE = re.compile(r"(?:exists|use|left|right)\b")
_NEUTRAL = re.compile(r"constructor\b")
_CLOSING = re.compile(r"(?:exact|apply|assumption|rfl)\b")
_FAMILIES = (
    frozenset({"asynchronous", "neutral"}),
    frozenset({"choice", "neutral", "closing"}),
)


def _step_kind(step: Step) -> str:
    text = step.tactic
    if _ASYNC.match(text):
        return "asynchronous"
    if _CHOICE.match(text):
        return "choice"
    if _NEUTRAL.match(text):
        return "neutral"
    if _CLOSING.match(text):
        return "closing"
    return "other"


def _close_phase(run: list[tuple[Step, str]], tokens: TokenCounter) -> Phase | None:
    if len(run) < 2:
        return None
    kinds = {kind for _, kind in run}
    if kinds <= _FAMILIES[0] and "asynchronous" in kinds:
        label = "asynchronous"
    elif kinds <= _FAMILIES[1] and (
        "choice" in kinds or {"neutral", "closing"} <= kinds
    ):
        label = "synchronous"
    else:
        return None
    steps = tuple(step.tactic.splitlines()[0] for step, _ in run)
    return Phase(label, run[0][0].line, steps, sum(tokens(s) for s, _ in run))


def find_phases(
    root: Step, tokens: TokenCounter, config: AnalysisConfig
) -> list[Phase]:
    """Maximal runs of one phase; a large subproof step ends the run."""
    out = []
    for children in blocks(root):
        run: list[tuple[Step, str]] = []
        for step in children + [None]:
            kind = "other" if step is None else _step_kind(step)
            if step is not None and tokens(step) > config.max_phase_step_tokens:
                kind = "other"
            kinds = {k for _, k in run} | {kind}
            if kind != "other" and any(kinds <= family for family in _FAMILIES):
                run.append((step, kind))
                continue
            phase = _close_phase(run, tokens)
            if phase:
                out.append(phase)
            run = [] if kind == "other" else [(step, kind)]
    return sorted(out, key=lambda p: p.line)
