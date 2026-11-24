"""Deterministic local-fact proposals from Lean's parsed syntax spans.

The exported functions return *alternative* edits on one unchanged incumbent.
Edits may overlap (nested wrappers, aliases enclosing later declarations).
Disjoint edits can also interact through Lean's local context, so a caller may
try a joint candidate but must compile and score it independently. None of the
textual hints here establishes that a fact is unused or semantically identical.
Whole-declaration verification, on every required version, remains mandatory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from proof_eval.optimization.syntax import Edit
from proof_eval.verification.backend import _masked_comments
from proof_eval.verification.metrics import _scan_comments

_BINDINGS = {"Lean.Parser.Tactic.tacticHave__", "Lean.Parser.Tactic.tacticLet__"}
_IDENT = re.compile(r"(?:«[^»]+»|[\w']+)")
_CHAR = re.compile(r"'(?:\\(?:u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)|[^'\\\n])'")


def _identifiers(text):
    """Character spans of identifier-like tokens, excluding comments/literals.

    This is used only for proposal ordering and alias replacement; it is not a
    Lean name resolver. Quoted identifiers are retained as complete tokens.
    """
    masked = _masked_comments(text)
    i = 0
    while i < len(masked):
        raw = re.match(r'r(#+)?"', masked[i:]) if masked[i] == "r" else None
        if raw:
            terminator = '"' + (raw.group(1) or "")
            stop = masked.find(terminator, i + raw.end())
            i = len(masked) if stop < 0 else stop + len(terminator)
            continue
        if masked[i] == '"':
            i += 1
            while i < len(masked):
                if masked[i] == "\\":
                    i += 2
                elif masked[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            continue
        if masked[i] == "'" and (char := _CHAR.match(masked, i)):
            i = char.end()
            continue
        match = _IDENT.match(masked, i)
        if match:
            yield match.start(), match.end(), match.group()
            i = match.end()
        else:
            i += 1


def _normalized(text):
    return re.sub(r"\s+", " ", _scan_comments(text)).strip()


@dataclass(frozen=True)
class _Binding:
    node: dict
    name: str
    rhs_start: int
    rhs_end: int
    rhs_node: dict | None
    type_text: str
    scope: dict


def _bindings(code, analysis):
    nodes = analysis["nodes"]
    by_path = {tuple(node["path"]): node for node in nodes}
    out = []
    for node in nodes:
        if node["kind"] not in _BINDINGS:
            continue
        path = tuple(node["path"])
        declaration = by_path.get(path + (2, 0))
        if not declaration or declaration["kind"] != "Lean.Parser.Term.letIdDecl":
            continue  # Patterns, anonymous have, and unsupported parser shapes.
        base = tuple(declaration["path"])
        name_node = by_path.get(base + (0,))
        if not name_node or name_node["kind"] != "Lean.Parser.Term.letId":
            continue
        name = code[name_node["start"] : name_node["end"]]
        if not _IDENT.fullmatch(name) or name == "_":
            continue
        # Parameterized local definitions need lambda/binder handling. Leave
        # them to a separate transformation rather than drop their parameters.
        binders = by_path.get(base + (1,))
        if binders and _normalized(code[binders["start"] : binders["end"]]):
            continue
        type_node = by_path.get(base + (2,))
        type_end = type_node["end"] if type_node else name_node["end"]
        rhs_node = by_path.get(base + (4,))
        rhs_end = declaration["end"]
        if rhs_node:
            rhs_start = rhs_node["start"]
        else:
            # Atomic terms have no syntax children and are omitted by the
            # observer. The type's AST span tells us where their := begins.
            between = _masked_comments(code[type_end:rhs_end])
            match = re.match(r"\s*:=\s*", between)
            if not match:
                continue
            rhs_start = type_end + match.end()
        if _normalized(code[type_end:rhs_start]) != ":=":
            continue
        scope = by_path.get(path[:-1])
        if not scope or scope["kind"] != "null":
            # A binding used directly as a combinator operand has a different
            # deletion/scope grammar; it is deliberately omitted here.
            continue
        out.append(
            _Binding(
                node,
                name,
                rhs_start,
                rhs_end,
                rhs_node,
                _normalized(code[name_node["end"] : type_end]),
                scope,
            )
        )
    return sorted(
        out, key=lambda binding: (binding.node["start"], -binding.node["end"])
    )


def _delete_span(code, start, stop, scope_end):
    """Consume an adjacent semicolon when deleting a tactic-sequence entry."""
    after = _masked_comments(code[stop:scope_end])
    match = re.match(r"[ \t]*;(?!=|;)", after)
    if match:
        stop += match.end()
    else:
        before = _masked_comments(code[:start])
        match = re.search(r"(?<![;<]);[ \t]*$", before)
        if match:
            start = match.start()
    return start, stop


def _reindent(code, start, stop, target_column):
    """Move an AST-delimited tactic sequence without guessing its endpoint."""
    line_start = code.rfind("\n", 0, start) + 1
    prefix = code[line_start:start]
    # Inline bodies can contain later indented tactics; retain their layout by
    # using `exact (by ...)` instead of guessing which column is significant.
    if prefix.strip():
        return None
    delta = len(prefix) - target_column
    lines = code[start:stop].splitlines(keepends=True)
    result = lines[:1]
    for line in lines[1:]:
        whitespace = len(line) - len(line.lstrip(" "))
        if delta >= 0:
            result.append(line[min(delta, whitespace) :])
        else:
            result.append(" " * -delta + line)
    return "".join(result)


def wrappers(code, analysis):
    """Contract adjacent `have/let h := rhs; exact h`, including nested scopes.

    A `by` RHS becomes its parsed tactic sequence with adjusted indentation.
    Other RHS terms become `exact rhs`. Parameterized bindings and nonadjacent
    uses are omitted. Type-directed elaboration can change, so certification is
    essential even when the source-level contraction looks obvious.
    """
    nodes = analysis["nodes"]
    edits = []
    for binding in _bindings(code, analysis):
        node = binding.node
        siblings = [
            n
            for n in nodes
            if n["kind"] == "Lean.Parser.Tactic.exact"
            and n["path"][:-1] == node["path"][:-1]
            and n["start"] >= node["end"]
        ]
        if not siblings:
            continue
        following = min(siblings, key=lambda n: n["start"])
        gap = _normalized(code[node["end"] : following["start"]])
        if (
            gap not in {"", ";"}
            or _normalized(code[following["start"] : following["end"]])
            != "exact " + binding.name
        ):
            continue
        rhs = code[binding.rhs_start : binding.rhs_end]
        replacement = "exact " + rhs
        if binding.rhs_node and binding.rhs_node["kind"] == "Lean.Parser.Term.byTactic":
            path = binding.rhs_node["path"]
            sequence = next(
                (
                    n
                    for n in nodes
                    if n["path"] == path + [1]
                    and n["kind"] == "Lean.Parser.Tactic.tacticSeq"
                ),
                None,
            )
            if sequence:
                column = node["start"] - (code.rfind("\n", 0, node["start"]) + 1)
                flattened = _reindent(code, sequence["start"], sequence["end"], column)
                if flattened is not None:
                    replacement = flattened
        edits.append(
            Edit(
                node["start"],
                following["end"],
                replacement,
                "contract_return_wrapper:" + binding.name,
            )
        )
    return sorted(set(edits), key=lambda e: (e.start, -e.end, e.replacement))


def local_fact_deletions(code, analysis):
    """Propose each local have/let deletion; rank textual nonreferences first.

    Textual nonreference is a search-order hint only: omega, simp_all, typeclass
    search, and other tactics can consume unnamed facts implicitly. Conversely,
    deleting a named fact can still work after context-dependent elaboration.
    Each edit must therefore be checked, even when its reason says nonreference.
    """
    proposals = []
    for binding in _bindings(code, analysis):
        node = binding.node
        tail = code[node["end"] : binding.scope["end"]]
        referenced = any(name == binding.name for _, _, name in _identifiers(tail))
        start, stop = _delete_span(
            code, node["start"], node["end"], binding.scope["end"]
        )
        reason = (
            "delete_local_fact:"
            + ("text_reference:" if referenced else "text_nonreference:")
            + binding.name
        )
        proposals.append((referenced, Edit(start, stop, "", reason)))
    return [
        edit
        for _, edit in sorted(
            proposals,
            key=lambda item: (item[0], -(item[1].end - item[1].start), item[1].start),
        )
    ]


def fact_reuse(code, analysis):
    """Reuse earlier same-scope facts, or contract simple identifier aliases.

    Reuse considers exact normalized explicit types, and exact RHSs with equal
    type annotations. It never assumes equality just because two tactics use
    the same text with different goals. Alias replacement respects token and
    comment/literal boundaries but is not name resolution; Lean must validate
    possible shadowing, context changes, and dependent elaboration afterwards.
    """
    bindings = _bindings(code, analysis)
    edits = []
    for i, binding in enumerate(bindings):
        rhs = code[binding.rhs_start : binding.rhs_end]
        rhs_normal = _normalized(rhs)
        for prior in bindings[:i]:
            if (
                prior.node["end"] > binding.node["start"]
                or prior.scope["path"] != binding.scope["path"]
                or prior.name == binding.name
            ):
                continue
            same_type = bool(binding.type_text) and binding.type_text == prior.type_text
            same_rhs = (
                binding.type_text == prior.type_text
                and rhs_normal == _normalized(code[prior.rhs_start : prior.rhs_end])
            )
            if (same_type or same_rhs) and rhs_normal != prior.name:
                edits.append(
                    Edit(
                        binding.rhs_start,
                        binding.rhs_end,
                        prior.name,
                        "reuse_local_fact:" + prior.name + "->" + binding.name,
                    )
                )
        if _IDENT.fullmatch(rhs_normal) and rhs_normal != binding.name:
            start, stop = _delete_span(
                code, binding.node["start"], binding.node["end"], binding.scope["end"]
            )
            tail = code[stop : binding.scope["end"]]
            uses = [
                (a, b)
                for a, b, name in _identifiers(tail)
                if name == binding.name and (a == 0 or tail[a - 1] != ".")
            ]
            if uses:
                for a, b in reversed(uses):
                    tail = tail[:a] + rhs_normal + tail[b:]
                edits.append(
                    Edit(
                        start,
                        binding.scope["end"],
                        tail,
                        "contract_local_alias:" + binding.name + "->" + rhs_normal,
                    )
                )
    return sorted(set(edits), key=lambda e: (e.start, -e.end, e.reason, e.replacement))
