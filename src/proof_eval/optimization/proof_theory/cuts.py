"""Cuts: local lemmas, what they bind, and how often later steps mention them."""

from __future__ import annotations

import re

from proof_eval.optimization.proof_theory.records import Cut
from proof_eval.optimization.proof_theory.tree import Step, find_top, names
from proof_eval.verification.metrics import token_count

CUT = re.compile(r"(have|haveI|let|letI|obtain|rcases|suffices)\b")
PATTERN_KEYWORDS = frozenset({"rfl", "_", "with"})

_AMBIENT = re.compile(
    r"\b(?:simp_all|aesop|grind(?!\s+only)|n?linarith|omega|assumption|tauto|"
    r"contradiction|trivial|positivity|subst_vars|decide|cc|itauto|bound|gcongr)\b"
    r"|\[[^\]]*\*\s*\]|\bat\s+\*"
)


def binding(kind: str, rest: str) -> tuple[tuple[str, ...], str, str]:
    """Bound names, statement text and proof text of a cut's source."""
    rest = rest.strip()
    if kind == "rcases":
        target, _, pattern = rest.partition(" with ")
        bound = [n for n in names(pattern) if n not in PATTERN_KEYWORDS]
        return tuple(bound), "", target
    split = find_top(rest, ":=")
    lhs, proof = (rest, "") if split < 0 else (rest[:split], rest[split + 2 :])
    if kind == "obtain" or lhs.startswith("⟨"):
        colon = find_top(lhs, ":")
        pattern, statement = (lhs, "") if colon < 0 else (lhs[:colon], lhs[colon + 1 :])
        bound = [n for n in names(pattern) if n not in PATTERN_KEYWORDS]
        return tuple(bound), statement, proof
    match = re.match(r"[^\s:({\[⟨]+", lhs)
    name = match.group() if match else "this"
    statement = lhs[match.end() :] if match else lhs
    statement = statement.strip()
    if statement.startswith(":"):
        statement = statement[1:]
    return (name,), statement, proof


def bound_names(step: Step) -> list[str]:
    """Names a step adds to the local context: cuts, intros, branch binders."""
    text = step.tactic
    cut = CUT.match(text)
    if cut:
        return list(binding(cut.group(1), text[cut.end() :])[0])
    intro = re.match(r"r?intros?\s+(.*)", text)
    if intro:
        return [n for n in names(intro.group(1)) if n not in PATTERN_KEYWORDS]
    case = re.match(r"(?:case'?|next|\|)\s+(.*?)=>", text)
    if case:
        return [n for n in names(case.group(1))[1:] if n not in PATTERN_KEYWORDS]
    return []


def _references(bound: tuple[str, ...], later: list[Step]) -> int:
    """Count mentions in later siblings, stopping after a rebinding sibling."""
    total = 0
    for name in bound:
        for step in later:
            mentions = names(step.subtree()).count(name)
            if name == "this":
                mentions += step.subtree().count("‹")
            cut = CUT.match(step.tactic)
            if cut and name in binding(cut.group(1), step.tactic[cut.end() :])[0]:
                total += max(mentions - 1, 0)
                break
            total += mentions
    return total


def find_cuts(root: Step) -> list[Cut]:
    out = []
    for parent in root.walk():
        for k, step in enumerate(parent.children):
            match = CUT.match(step.tactic)
            if not match:
                continue
            kind = match.group(1)
            rest = "\n".join(
                [step.tactic[match.end() :]] + [c.subtree() for c in step.children]
            )
            bound, statement, proof = binding(kind, rest)
            later = parent.children[k + 1 :]
            scope = "\n".join(s.subtree() for s in later)
            out.append(
                Cut(
                    kind,
                    bound,
                    step.line,
                    token_count(statement) if statement.strip() else 0,
                    token_count(proof) if proof.strip() else 0,
                    _references(bound, later),
                    bool(_AMBIENT.search(scope)),
                    not re.match(r"\s*by\b", proof) and not step.children,
                )
            )
    return out
