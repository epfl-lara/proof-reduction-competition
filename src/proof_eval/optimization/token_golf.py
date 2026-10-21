"""Tokenizer-aware rewrites that keep a proof's meaning but cost fewer tokens.

The arena tokenizer counts every bracket, comma and `;` as a token, treats a
dotted identifier as one token, and ignores whitespace and newlines. Three
syntactic rewrites follow:

- `tac₁; tac₂` becomes two lines aligned at the first tactic's column.
- A final parenthesized argument `f a (g x)` becomes `f a $ g x`. Lean core
  defines `f $ x` as alternative syntax for `f <| x`; `<|` itself costs two
  tokens. Mathlib's style linter may warn, which does not fail compilation.
- Redundant outer parentheses after `exact`, `:=`, `⟨`, `,` and similar
  boundaries are removed.

Only plain application chains are rewritten; `$` has the lowest precedence, so
an operator before the argument could change the parse. Every group is still a
candidate that Lean must accept on every required version.
"""

from __future__ import annotations

import re
from typing import Any

from proof_eval.optimization.proof_theory.rewrites import declaration_groups
from proof_eval.optimization.syntax import Edit
from proof_eval.verification.backend import _masked_comments

_OPEN, _CLOSE = "([{⟨", ")]}⟩"
# Keywords followed by a term, and boundary tokens that start a term.
_TERM_KEYWORDS = frozenset(
    "exact apply refine refine' use exists from using specialize then else "
    "return".split()
)
_KEYWORDS = _TERM_KEYWORDS | frozenset(
    "show at with fun by if calc simp rw only have let obtain rcases intro "
    "rintro case match suffices generalize induction cases".split()
)
_WORD = re.compile(r"[@\w.'!?]+$")
_TERM_TEXT = (":=", "←")
_TACTIC_TEXT = ("=>", "<;>")
_TACTIC_START = re.compile(r"^[ \t]*(?:[·.][ \t]+)?|\bby[ \t]+|=>[ \t]+")


def _matching(text: str, start: int) -> int:
    depth = 0
    for i in range(start, len(text)):
        if text[i] in _OPEN:
            depth += 1
        elif text[i] in _CLOSE:
            depth -= 1
            if depth == 0:
                return i
    return -1


def _top_level(inner: str) -> str:
    """Characters of `inner` outside nested brackets."""
    out, depth = [], 0
    for char in inner:
        if char in _OPEN:
            depth += 1
        elif char in _CLOSE:
            depth -= 1
        elif depth == 0:
            out.append(char)
    return "".join(out)


def _plain_group(inner: str) -> bool:
    """Not a type ascription, tuple, named argument or `·` section."""
    top = _top_level(inner)
    return bool(inner.strip()) and not any(c in top for c in ":,·|")


def _ends_term(text: str, close: int) -> bool:
    """The group ends its term: a delimiter follows, or the line ends and the
    next nonblank line is not a deeper continuation."""
    after = text[close + 1 :]
    same_line = after.split("\n", 1)[0]
    if re.match(r"[ \t]*[,⟩)\]]", same_line):
        return True
    if same_line.strip():
        return False
    line_start = text.rfind("\n", 0, close) + 1
    indent = len(text[line_start:]) - len(text[line_start:].lstrip(" "))
    for line in after.split("\n")[1:]:
        if line.strip():
            return len(line) - len(line.lstrip(" ")) <= indent
    return True


def _head(text: str, open_at: int) -> tuple[int, bool] | None:
    """Walk back over application arguments to the boundary of their term.

    Returns (argument count, whether the boundary starts a term) or None when
    an operator lies in between, which could change the parse.
    """
    k, words = open_at - 1, 0
    while True:
        while k >= 0 and text[k] in " \t":
            k -= 1
        if k < 0 or text[k] == "\n":
            return words, False
        if text[k] in "[⟨(,":
            return words, True
        prefix = text[: k + 1]
        if prefix.endswith(_TERM_TEXT):
            return words, True
        if prefix.endswith(_TACTIC_TEXT):
            return words, False
        if text[k] in _CLOSE:
            closer = text[k]
            opener, depth = _OPEN[_CLOSE.index(closer)], 0
            while k >= 0:
                if text[k] == closer:
                    depth += 1
                elif text[k] == opener:
                    depth -= 1
                    if depth == 0:
                        break
                k -= 1
            if k < 0:
                return None
            k, words = k - 1, words + 1
            continue
        word = _WORD.search(text, 0, k + 1)
        if not word:
            return None
        if word.group() in _KEYWORDS:
            return words, word.group() in _TERM_KEYWORDS
        k, words = word.start() - 1, words + 1


def _dollar_and_paren_groups(text: str) -> list[list[Edit]]:
    groups = []
    for open_at, char in enumerate(text):
        if char != "(":
            continue
        close = _matching(text, open_at)
        if close < 0 or not _plain_group(text[open_at + 1 : close]):
            continue
        if not _ends_term(text, close):
            continue
        head = _head(text, open_at)
        if head is None or not head[1]:
            continue  # Unknown parse, or a tactic position such as `(tac; tac)`.
        words = head[0]
        inner = text[open_at + 1 : close].strip()
        if "\n" in inner:
            continue
        if words:
            space = "" if text[open_at - 1 : open_at] in " \t" else " "
            replacement, reason = f"{space}$ {inner}", "dollar_application"
        else:
            replacement, reason = inner, "drop_outer_parens"
        groups.append([Edit(open_at, close + 1, replacement, reason)])
    return groups


def _semicolon_groups(text: str) -> list[list[Edit]]:
    groups, offset = [], 0
    for line in text.split("\n"):
        depth, cuts = 0, []
        for i, char in enumerate(line):
            if char in _OPEN:
                depth += 1
            elif char in _CLOSE:
                depth -= 1
            elif char == ";" and depth == 0:
                if line[i - 1 : i] in ("<", ";") or line[i + 1 : i + 2] in (";", ">"):
                    continue  # Part of `<;>` or `;;`.
                cuts.append(i)
        if cuts:
            prefix = line[: cuts[0]]
            starts = [m.end() for m in _TACTIC_START.finditer(prefix)]
            column = max(starts) if starts else 0
            edits = []
            for i in cuts:
                stop = i + 1
                while stop < len(line) and line[stop] in " \t":
                    stop += 1
                edits.append(
                    Edit(
                        offset + i,
                        offset + stop,
                        "\n" + " " * column,
                        "split_semicolon",
                    )
                )
            groups.append(edits)
        offset += len(line) + 1
    return groups


def body_golf_groups(body: str) -> list[list[Edit]]:
    text = _masked_comments(body)
    return _semicolon_groups(text) + _dollar_and_paren_groups(text)


def golf_groups(row: dict[str, Any], code: str) -> list[list[Edit]]:
    """Tokenizer-aware edit groups on a full declaration matching `row`."""
    return declaration_groups(row, code, body_golf_groups)
