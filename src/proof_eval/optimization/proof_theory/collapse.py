"""Collapse a case split and its branches into `split <;> closer`.

A splitting step (`induction`, `cases`, `rcases`, `constructor`, `refine`, ...)
followed only by its branches (`| pat =>`, `case tag =>`, `next =>`, bullets)
becomes one step that applies a single closer to every generated goal. Closers
already used by single-line branches are tried first, most common first, then
general automation. A closer that names a branch's own binders is skipped,
since the collapsed proof no longer binds them. Each closer is one candidate;
Lean decides whether it closes every goal and whether the score improves.
"""

from __future__ import annotations

import re
from collections import Counter

from proof_eval.optimization.proof_theory.spans import is_bullet
from proof_eval.optimization.proof_theory.tree import CASE_HEADER, Step, blocks, names
from proof_eval.optimization.syntax import Edit
from proof_eval.verification.metrics import token_count

# `match` is absent on purpose: as a tactic it needs its alternatives, so
# `match x <;> tac` is not valid syntax.
SPLITTER = re.compile(
    r"(?:induction|fun_induction|cases|rcases|obtain|split|split_ifs|by_cases|"
    r"constructor|refine'?|interval_cases|fin_cases|rintro)\b"
)
FALLBACK_CLOSERS = (
    "simp_all",
    "grind",
    "aesop",
    "omega",
    "simp",
    "assumption",
    "rfl",
    "tauto",
    "decide",
    "norm_num",
    "linarith",
    "trivial",
)
MAX_CLOSERS = 6
_BRANCH = re.compile(r"^\s*(?:[·.]\s|case'?\s|next\b|\|)")
_BINDERS = re.compile(r"^\s*(?:case'?|next|\|)\s*(.*?)=>", re.S)


def _is_branch(step: Step) -> bool:
    return bool(_BRANCH.match(step.text))


def _branches(children: list[Step], index: int) -> list[Step] | None:
    """Branches of the splitter at `index`: its own alternatives or the rest."""
    step = children[index]
    if step.children:
        if all(_is_branch(child) for child in step.children):
            return step.children
        return None
    tail = children[index + 1 :]
    return tail if tail and all(_is_branch(child) for child in tail) else None


def _closer(body: str, branch: Step) -> str | None:
    """A branch's single-line closer, unless it uses the branch's binders."""
    text = body[branch.start : branch.stop()]
    header = _BINDERS.match(text)
    bound = set(names(header.group(1))[1:]) if header else set()
    if header:
        rest = text[header.end() :]
    else:
        rest = re.sub(r"^\s*[·.]\s*", "", text, count=1)
    rest = rest.strip()
    if not rest or "\n" in rest or ";" in rest or "?_" in rest:
        return None
    if bound & set(names(rest)):
        return None
    return " ".join(rest.split())


def _head(step: Step) -> str | None:
    head = re.sub(r"\s+with\s*$", "", " ".join(step.tactic.split()))
    if not head or head.endswith("<;>") or CASE_HEADER.match(step.text):
        return None
    return head


def collapse_groups(root: Step, body: str) -> list[list[Edit]]:
    groups = []
    for children in blocks(root):
        for index, step in enumerate(children):
            if _is_branch(step) and not is_bullet(step):
                continue
            if not SPLITTER.match(step.tactic):
                continue
            branches = _branches(children, index)
            head = _head(step)
            if not branches or len(branches) < 2 or head is None:
                continue
            seen = Counter(c for c in (_closer(body, b) for b in branches) if c)
            closers = [c for c, _ in seen.most_common()]
            closers += [c for c in FALLBACK_CLOSERS if c not in closers]
            stop = branches[-1].stop()
            original = token_count(body[step.start : stop])
            prefix = "· " if is_bullet(step) else ""
            for closer in closers[:MAX_CLOSERS]:
                replacement = f"{prefix}{head} <;> {closer}"
                if token_count(replacement) < original:
                    reason = "collapse_branches:" + closer
                    groups.append([Edit(step.start, stop, replacement, reason)])
    return groups
