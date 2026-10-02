"""Candidate validation and the arena's published proof-length convention.

The public tokenizer is mirrored, including its unusual operator grouping.
Comments use a nested, literal-aware scanner. Statement boundaries come from
the dataset, never from searching for the first ``:=`` in a declaration.
"""

from __future__ import annotations

import math
import re
from typing import Any


MAX_PROOF_BYTES = 256 * 1024
TOKENIZER_SOURCE = (
    "https://github.com/delta-lab-ai/lean-refactor/blob/"
    "9c98a3a097e53724e35b2a2e7fe316c331efa20a/"
    "lean_refactor/cc_agent/scripts/proof_utils.py"
)
_OPERATORS = (
    ":=", "!=", "&&", "-.", "->", "←", "..", "...", "::", ":>",
    "<;>", ";;", "==", "||", "=>", "<=", ">=", "⁻¹", "?_",
)

# The arena intake's forbidden patterns, applied to uncommented input. Like the
# arena, these also reject matching text inside literals: this intentionally
# conservative check is not a Lean parser or an operating-system sandbox.
_FORBIDDEN_PATTERNS = (
    ("#eval", r"#\s*eval\b"),
    ("#reduce", r"#\s*reduce\b"),
    ("IO.", r"\bIO\."),
    ("unsafe declaration", r"\bunsafe\s+(def|fun|theorem|lemma)\b"),
    ("extern", r"\bextern\b"),
    ("initialize", r"\binitialize\b"),
    ("implemented_by", r"@\[\s*implemented[_]?[Bb]y\b"),
    ("extern attribute", r"@\[\s*extern\b"),
    ("sorry", r"\bsorry\b"),
    ("sorryAx", r"\bsorryAx\b"),
    ("admit", r"\badmit\b"),
    ("axiom", r"\baxiom\b"),
    ("native_decide", r"\bnative_decide\b"),
    ("ofReduceBool", r"\bofReduceBool\b"),
    ("ofReduceNat", r"\bofReduceNat\b"),
    ("run_cmd", r"\brun_cmd\b"),
    ("run_elab", r"\brun_elab\b"),
    ("#exit", r"#\s*exit\b"),
    ("#count_heartbeats", r"#\s*count_heartbeats\b"),
    ("attribute command", r"(?m)^\s*attribute\b"),
    ("syntax extension", r"\b(macro|macro_rules|elab|elab_rules|notation|syntax)\b"),
    ("deriving instance", r"\bderiving\s+instance\b"),
    ("auxiliary declaration", r"(?m)^\s*(def|abbrev|instance|structure|inductive|class|opaque)\b"),
)
_COMPILED_FORBIDDEN = tuple((name, re.compile(pattern)) for name, pattern in _FORBIDDEN_PATTERNS)

# Stricter local guard: only a proof term may follow the fixed statement. Banning
# these words throughout the body also catches same-line command injection and
# namespace escapes. This can reject legitimate uses of reserved words in
# quoted names or strings; return the explicit reason instead of silently
# accepting unsupported input. Local `let`, `have`, `calc`, and `match` work.
_COMMAND_WORDS = re.compile(
    r"\b(theorem|lemma|example|def|abbrev|instance|structure|inductive|class|opaque|"
    r"namespace|section|end|import|prelude|set_option|attribute|open|export|"
    r"universe|universes|variable|variables|include|omit|mutual|noncomputable|"
    r"unsafe|initialize|builtin_initialize|register_option|declare_syntax_cat)\b"
)
_HASH_COMMAND = re.compile(r"#\s*[A-Za-z_]\w*")
_RAW_STRING = re.compile(r'r(#+)?"')
_CHAR_LITERAL = re.compile(r"'(?:\\(?:u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)|[^'\\\n])'")


def _scan_comments(text: str, *, mask_literals: bool = False) -> str:
    """Replace nested Lean comments with whitespace, preserving line boundaries.

    Ordinary/raw strings, character literals, and quoted identifiers retain
    their contents. Reject unterminated comments and literals instead of hiding
    trailing code from the validation scan.
    """
    result: list[str] = []
    index, size = 0, len(text)

    def literal(value: str) -> str:
        return "".join("\n" if char == "\n" else " " for char in value) if mask_literals else value

    while index < size:
        if text.startswith("/-", index):
            depth, cursor = 1, index + 2
            while cursor < size and depth:
                if text.startswith("/-", cursor):
                    depth += 1
                    cursor += 2
                elif text.startswith("-/", cursor):
                    depth -= 1
                    cursor += 2
                else:
                    cursor += 1
            if depth:
                raise ValueError("Unterminated Lean block comment")
            result.append(" " + "\n" * text[index:cursor].count("\n"))
            index = cursor
            continue
        if text.startswith("--", index):
            cursor = text.find("\n", index + 2)
            index = size if cursor < 0 else cursor
            continue
        # Lean's raw strings are r"...", r#"..."#, etc.
        raw = _RAW_STRING.match(text, index) if text[index] == "r" else None
        if raw:
            terminator = '"' + (raw.group(1) or "")
            cursor = text.find(terminator, raw.end())
            if cursor < 0:
                raise ValueError("Unterminated Lean raw string")
            cursor += len(terminator)
            result.append(literal(text[index:cursor]))
            index = cursor
            continue
        if text[index] == '"':
            cursor = index + 1
            while cursor < size:
                if text[cursor] == "\\":
                    cursor += 2
                elif text[cursor] == '"':
                    cursor += 1
                    break
                else:
                    cursor += 1
            else:
                raise ValueError("Unterminated Lean string literal")
            result.append(literal(text[index:cursor]))
            index = cursor
            continue
        if text[index] == "«":
            cursor = text.find("»", index + 1)
            if cursor < 0:
                raise ValueError("Unterminated Lean quoted identifier")
            result.append(literal(text[index:cursor + 1]))
            index = cursor + 1
            continue
        if text[index] == "'":
            char = _CHAR_LITERAL.match(text, index)
            if char:
                result.append(literal(char.group()))
                index = char.end()
                continue
        result.append(text[index])
        index += 1
    return "".join(result)


def strip_comments(text: str) -> str:
    """Remove nested comments while preserving literals and line boundaries."""
    return _scan_comments(text)


def _check_delimiters(body: str) -> None:
    """Prevent a proof body from closing the backend's enclosing term wrapper."""
    stack: list[str] = []
    matching = {")": "(", "]": "[", "}": "{"}
    for char in _scan_comments(body, mask_literals=True):
        if char in "([{":
            stack.append(char)
        elif char in matching:
            if not stack or stack.pop() != matching[char]:
                raise ValueError("Unbalanced proof-body delimiters")
    if stack:
        raise ValueError("Unbalanced proof-body delimiters")


def token_count(body: str) -> int:
    """Count only proof-body tokens using the published arena convention."""
    cleaned = strip_comments(body).strip()
    count = 0
    for line in cleaned.splitlines():
        if not line.strip():
            continue
        tokens: list[str] = []
        token = ""
        for char in line:
            if char == " ":
                if token:
                    tokens.append(token)
                    token = ""
            elif char.isalnum() or char in "._'":
                token += char
            else:
                if token:
                    tokens.append(token)
                    token = ""
                tokens.append(char)
        if token:
            tokens.append(token)
        tokenized = " ".join(tokens)
        for operator in _OPERATORS:
            tokenized = tokenized.replace(" ".join(operator), operator)
        count += len(tokenized.split(" "))
    return count


def validate_candidate(
    row: dict[str, Any], code: str, input_kind: str = "declaration",
) -> tuple[str, str]:
    """Return ``(full_declaration, body)`` or raise a clear ``ValueError``.

    Full declarations must preserve the exact dataset statement. Body input is
    attached to that statement. The original ``src`` is never token-counted or
    compiled here. This validator deliberately disallows command keywords even
    inside literals; it does not claim to sandbox arbitrary Lean elaborators.
    """
    if input_kind not in ("declaration", "body"):
        raise ValueError("input_kind must be 'declaration' or 'body'")
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Candidate code must be a nonempty string")
    if len(code.encode("utf-8")) > MAX_PROOF_BYTES:
        raise ValueError("Candidate exceeds the 256 KiB size limit")
    statement = row.get("statement")
    if not isinstance(statement, str) or not statement.strip():
        raise ValueError("Benchmark row has no statement")
    code = code.strip()
    if input_kind == "declaration":
        if not code.startswith(statement):
            raise ValueError("Candidate must preserve the exact benchmark statement")
        suffix = code[len(statement):].lstrip()
        if not suffix.startswith(":="):
            raise ValueError("Expected := immediately after the exact benchmark statement")
        body = suffix[2:].strip()
    else:
        body = code
    if not body or not strip_comments(body).strip():
        raise ValueError("Candidate proof body is empty")
    normalized = statement + " := " + body
    if len(normalized.encode("utf-8")) > MAX_PROOF_BYTES:
        raise ValueError("Full declaration exceeds the 256 KiB size limit")
    uncommented = strip_comments(normalized)
    for label, pattern in _COMPILED_FORBIDDEN:
        if pattern.search(uncommented):
            raise ValueError(f"Forbidden construct: {label}")
    uncommented_body = strip_comments(body)
    command = _COMMAND_WORDS.search(uncommented_body) or _HASH_COMMAND.search(uncommented_body)
    if command:
        raise ValueError(f"Only a proof body is accepted; forbidden command: {command.group()}")
    _check_delimiters(body)
    return normalized, body


def reduction_percent(reference: int | float | None, candidate: int | float | None) -> float | None:
    """Percent reduction; unavailable/nonpositive baselines yield ``None``.

    Zero candidate cost is a valid 100% reduction; negative reductions are
    preserved. Invalid numeric counts are rejected rather than becoming NaN in
    an agent reward or JSON result.
    """
    if reference is None or candidate is None:
        return None
    if isinstance(reference, bool) or isinstance(candidate, bool):
        raise ValueError("Metric counts must be numbers, not booleans")
    if not math.isfinite(reference) or not math.isfinite(candidate):
        raise ValueError("Metric counts must be finite")
    if reference < 0 or candidate < 0:
        raise ValueError("Metric counts cannot be negative")
    if reference == 0:
        return None
    return 100.0 * (1.0 - candidate / reference)
