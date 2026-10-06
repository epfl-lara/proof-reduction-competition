"""Indentation-recovered tactic trees and shared text helpers.

This is not Lean's parser. A deeper line is a child step after a block opener
(`by`, `=>`, a bullet, a structural tactic); otherwise it continues the
previous step's term. Parse comment-masked text: line numbers are 1-based and
character offsets index the original body unchanged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator

from proof_eval.optimization.structural import _identifiers
from proof_eval.verification.metrics import token_count

CASE_HEADER = re.compile(r"^\s*(?:·\s*)?(?:case'?|next|\|)[^\n]*?=>\s*")

_OPENS_BLOCK = re.compile(r"(?:\bby|=>|\bdo|\bfrom|<;>)\s*$")
_BLOCK_TACTICS = frozenset(
    {
        "all_goals",
        "any_goals",
        "calc",
        "case",
        "case'",
        "cases",
        "conv",
        "first",
        "focus",
        "induction",
        "iterate",
        "match",
        "next",
        "on_goal",
        "rcases",
        "repeat",
        "repeat'",
        "try",
    }
)
_CHILD_PREFIXES = ("·", "case ", "case' ", "next", "|", "<;>")
_HEAD = re.compile(r"[A-Za-z_][\w'!?]*")


@dataclass
class Step:
    """One tactic step. `start`/`end` are body offsets of its own text.

    `line_start` is the offset of its first line, including indentation.
    """

    line: int
    indent: int
    text: str
    depth: int
    line_start: int = 0
    start: int = 0
    end: int = 0
    children: list[Step] = field(default_factory=list)

    @property
    def tactic(self) -> str:
        """Step text without a leading focusing bullet."""
        text = self.text.strip()
        if text.startswith(("·", ".")):
            text = text[1:].lstrip()
        return text

    @property
    def head(self) -> str:
        match = _HEAD.match(self.tactic)
        return match.group() if match else self.tactic[:2]

    def subtree(self) -> str:
        return "\n".join([self.text] + [child.subtree() for child in self.children])

    def walk(self) -> Iterator[Step]:
        yield self
        for child in self.children:
            yield from child.walk()

    def last_line(self) -> int:
        own = self.line + self.text.count("\n")
        return max([own] + [child.last_line() for child in self.children])

    def stop(self) -> int:
        """Body offset just after the last character of the whole subtree."""
        return max([self.end] + [child.stop() for child in self.children])


def _mask_leading_by(body: str) -> str:
    """Hide a leading `by` while preserving every line and column."""
    return re.sub(r"^\s*by\b", lambda m: re.sub(r"\S", " ", m.group()), body, count=1)


def _continues_term(parent: Step, stripped: str) -> bool:
    if stripped.startswith("<;>"):
        return True
    return not (
        _OPENS_BLOCK.search(parent.text)
        or parent.head in _BLOCK_TACTICS
        or parent.text.lstrip().startswith(("·", "."))
        or parent.children
        or stripped.startswith(_CHILD_PREFIXES)
    )


def parse(body: str) -> Step:
    """Return a synthetic root whose children are the body's top-level steps."""
    root = Step(0, -1, "", -1)
    stack = [root]
    offset = 0
    for number, raw in enumerate(_mask_leading_by(body).splitlines(True), start=1):
        line_start, offset = offset, offset + len(raw)
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        end = line_start + len(line.rstrip())
        while stack[-1] is not root and indent <= stack[-1].indent:
            stack.pop()
        parent = stack[-1]
        stripped = line.strip()
        if parent is not root and _continues_term(parent, stripped):
            parent.text += "\n" + line
            parent.end = end
            continue
        step = Step(number, indent, line, len(stack) - 1, line_start)
        step.start, step.end = line_start + indent, end
        parent.children.append(step)
        stack.append(step)
    return root


class TokenCounter:
    """Memoized arena token counts of subtrees."""

    def __init__(self):
        self._cache: dict[int, int] = {}

    def __call__(self, step: Step) -> int:
        key = id(step)
        if key not in self._cache:
            self._cache[key] = token_count(step.subtree())
        return self._cache[key]


def names(text: str) -> list[str]:
    """Identifier tokens outside comments and literals; not name resolution."""
    return [name for _, _, name in _identifiers(text)]


def find_top(text: str, token: str) -> int:
    """Index of `token` outside brackets; a bare `:` never matches `:=`."""
    depth = 0
    for i, char in enumerate(text):
        if char in "([{⟨":
            depth += 1
        elif char in ")]}⟩":
            depth -= 1
        elif depth == 0 and text.startswith(token, i):
            if token == ":" and text.startswith(":=", i):
                continue
            return i
    return -1
