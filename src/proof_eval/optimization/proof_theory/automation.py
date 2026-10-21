"""Searching automation and the size of the local context it runs in."""

from __future__ import annotations

import re

from proof_eval.optimization.proof_theory.cuts import bound_names
from proof_eval.optimization.proof_theory.records import (
    DECISION,
    SATURATION,
    AutomationCall,
)
from proof_eval.optimization.proof_theory.tree import CASE_HEADER, Step

_SATURATION = re.compile(
    r"(?:simp_all|aesop|grind(?!\s+only)|tauto|itauto|cc|exact\?|apply\?)\b"
    r"|simp\b.*(?:\[[^\]]*\*\s*\]|\bat\s+\*)"
)
_DECISION = re.compile(
    r"(?:omega|n?linarith|norm_num|ring_nf|ring|decide|positivity|field_simp|"
    r"polyrith|norm_cast|push_cast|bound|gcongr|abel)\b"
)
_PREFIX = re.compile(r"^(?:[·.(]|try\b|all_goals\b|any_goals\b|first\b|\|)\s*")


def _classify(segment: str) -> tuple[str | None, str]:
    text = segment.strip()
    if ":= by" in text:
        text = text.split(":= by", 1)[1].strip()
    while _PREFIX.match(text):
        text = _PREFIX.sub("", text, count=1)
    if _SATURATION.match(text):
        return SATURATION, text
    if _DECISION.match(text):
        return DECISION, text
    return None, text


def find_automation(root: Step) -> list[AutomationCall]:
    """Each saturating or deciding call, with named local facts in scope.

    Branch binders (`case foo a b =>`, `| inl a =>`) count only inside their
    branch; a cut or intro counts for the steps after it.
    """
    calls = []

    def visit(steps: list[Step], context: list[str]) -> None:
        local = list(context)
        for step in steps:
            bound = bound_names(step)
            branch = step.head in {"case", "case'", "next"} or step.tactic.startswith(
                "|"
            )
            inline = local + bound if branch else local
            for segment in re.split(r"<;>|;", CASE_HEADER.sub("", step.text, count=1)):
                kind, text = _classify(segment)
                if kind:
                    calls.append(
                        AutomationCall(
                            kind, text.splitlines()[0], step.line, len(inline)
                        )
                    )
            if branch:
                visit(step.children, local + bound)
            else:
                visit(step.children, local)
                local += bound

    visit(root.children, [])
    return calls
