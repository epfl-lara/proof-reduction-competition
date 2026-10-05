"""Deterministic, syntax-bounded deletion proposals for tactic argument lists.

These are proposals, not equivalence claims. Callers must elaborate the whole
edited proof and compare the competition score on all requested versions.
In particular, a shorter lemma list can make a simplifier or arithmetic tactic
slower. After accepting a proposal, obtain fresh syntax before editing again.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from proof_eval.optimization.syntax import Edit

TACTIC_FAMILIES = {
    "Lean.Parser.Tactic.simp": "simp",
    "Lean.Parser.Tactic.simpAll": "simp",
    "Lean.Parser.Tactic.dsimp": "simp",
    "Mathlib.Tactic.linarith": "arithmetic",
    "Mathlib.Tactic.nlinarith": "arithmetic",
    "Lean.Parser.Tactic.rwSeq": "rewrite",
    "Lean.Parser.Tactic.rewriteSeq": "rewrite",
}
FAMILIES = ("simp", "arithmetic", "rewrite")


@dataclass(frozen=True)
class ListSite:
    """A tactic list, with one character span per top-level argument.

    Argument spans retain their own whitespace and comments. Only commas
    between arguments are reconstructed, so nested syntax and locations such
    as ``at h ⊢`` remain untouched. ``path`` identifies the compiler AST node.
    """

    family: str
    tactic: str
    start: int
    end: int
    list_start: int
    list_end: int
    elements: tuple[tuple[int, int], ...]
    path: tuple[int, ...]

    def record(self):
        return asdict(self)

    def remove(self, code, first, stop):
        """Remove a nonempty contiguous range; never remove the ``only`` flag."""
        if not 0 <= first < stop <= len(self.elements):
            raise ValueError("Invalid argument deletion range")
        kept = [
            code[a:b] for i, (a, b) in enumerate(self.elements) if not first <= i < stop
        ]
        return Edit(
            self.list_start,
            self.list_end,
            "[" + ",".join(kept) + "]",
            f"{self.family}_list_remove:{first}:{stop}",
        )

    def alternatives(self, code):
        return [
            self.remove(code, first, stop)
            for first, stop in deletion_chunks(len(self.elements))
        ]


def deletion_chunks(size):
    """Whole list, successively halved partitions, then every singleton.

    This is a finite proposal schedule for delta debugging, not an assertion
    that all contiguous subsets or a globally minimal argument set are tried.
    """
    if size < 0:
        raise ValueError("List size must be nonnegative")
    seen = set()
    pieces = 1
    while size and pieces < 2 * size:
        for i in range(min(pieces, size)):
            first, stop = i * size // min(pieces, size), (i + 1) * size // min(
                pieces, size
            )
            if (first, stop) not in seen:
                seen.add((first, stop))
                yield first, stop
        if pieces >= size:
            break
        pieces *= 2


def _argument_spans(code, start, stop, protected):
    """Find list commas outside direct argument AST nodes and lexical trivia.

    The syntax observer omits identifier atoms. It does retain compound terms,
    including ``∀ x, P x``, lambdas and nested lists; skip those entire spans.
    Therefore commas inside a term cannot be mistaken for list separators.
    The small lexer handles comments and quoted atoms in the remaining gaps.
    Malformed or unrecognized bracket structure yields no proposals.
    """
    protected = sorted(set(protected))
    if any(a < start or b > stop or a >= b for a, b in protected):
        return None
    if any(b > c for (_, b), (c, _) in zip(protected, protected[1:])):
        return None
    protected_by_start = dict(protected)
    delimiters = []
    pos = start
    while pos < stop:
        if pos in protected_by_start:
            pos = protected_by_start[pos]
            continue
        if code.startswith("--", pos):
            newline = code.find("\n", pos + 2, stop)
            pos = stop if newline == -1 else newline + 1
        elif code.startswith("/-", pos):
            depth = 1
            pos += 2
            while pos < stop and depth:
                if code.startswith("/-", pos):
                    depth += 1
                    pos += 2
                elif code.startswith("-/", pos):
                    depth -= 1
                    pos += 2
                else:
                    pos += 1
            if depth:
                return None
        elif code[pos] == "«":
            closing = code.find("»", pos + 1, stop)
            if closing == -1:
                return None
            pos = closing + 1
        elif code[pos] == '"':
            pos += 1
            while pos < stop and code[pos] != '"':
                pos += 2 if code[pos] == "\\" else 1
            if pos >= stop:
                return None
            pos += 1
        elif code[pos] in "()[]{}⟨⟩":
            # Nontrivial terms should have a direct child AST span. Avoid
            # guessing if a future parser changes the shape of that node.
            return None
        elif code[pos] == ",":
            delimiters.append(pos)
            pos += 1
        else:
            pos += 1
    bounds = [start] + [p + 1 for p in delimiters]
    ends = delimiters + [stop]
    spans = tuple(zip(bounds, ends))
    if any(not code[a:b].strip() for a, b in spans):
        return None
    return spans


def list_sites(code, analysis, families=FAMILIES):
    """Locate supported tactic lists using the compiler's original AST.

    Simplifier lists require an explicit ``only`` flag: changing an unrestricted
    simp database belongs in the preceding explicit-simplifier experiment.
    Arithmetic lists retain their existing ``only`` flag, if present. Rewrite
    lists are separately selectable because lemma order affects their meaning.
    """
    families = set(families)
    if not families <= set(FAMILIES):
        raise ValueError(f"Unknown list families: {sorted(families - set(FAMILIES))}")
    nodes = analysis["nodes"]
    children = {}
    for node in nodes:
        children.setdefault(tuple(node["path"][:-1]), []).append(node)
    sites = []
    seen = set()
    for tactic in nodes:
        family = TACTIC_FAMILIES.get(tactic["kind"])
        if family not in families:
            continue
        path = tuple(tactic["path"])
        direct = children.get(path, [])
        if family == "simp" and not any(
            code[n["start"] : n["end"]] == "only" for n in direct
        ):
            continue
        # simp/rw lists are direct children. Linarith stores an optional list
        # one level below its linarithArgsRest child. Deeper term lists are not
        # tactic arguments and must not become independent minimization sites.
        possible = list(direct)
        if family == "arithmetic":
            possible += [
                n
                for parent in direct
                if parent["kind"] == "Mathlib.Tactic.linarithArgsRest"
                for n in children.get(tuple(parent["path"]), [])
            ]
        for container in possible:
            first, stop = container["start"], container["end"]
            if (
                not 0 <= first < stop <= len(code)
                or code[first:stop][:1] != "["
                or code[stop - 1] != "]"
            ):
                continue
            container_path = tuple(container["path"])
            content = [
                n
                for n in children.get(container_path, [])
                if n["path"][-1] == 1
                and n["kind"] == "null"
                and first < n["start"] <= n["end"] < stop
            ]
            if len(content) != 1:
                continue
            entries = children.get(tuple(content[0]["path"]), [])
            spans = _argument_spans(
                code, first + 1, stop - 1, [(n["start"], n["end"]) for n in entries]
            )
            if not spans:
                continue
            # Observer child indices include interleaved comma atoms. Check
            # every retained argument against its parser-provided list index.
            # This also rejects unsupported parser shapes conservatively.
            if any(
                n["path"][-1] % 2
                or n["path"][-1] // 2 >= len(spans)
                or not (
                    spans[n["path"][-1] // 2][0]
                    <= n["start"]
                    < n["end"]
                    <= spans[n["path"][-1] // 2][1]
                )
                for n in entries
            ):
                continue
            if (first, stop) in seen:
                continue
            seen.add((first, stop))
            name = re.match(r"\w+", code[tactic["start"] : tactic["end"]])
            sites.append(
                ListSite(
                    family,
                    name.group() if name else tactic["kind"],
                    tactic["start"],
                    tactic["end"],
                    first,
                    stop,
                    spans,
                    container_path,
                )
            )
    return sorted(sites, key=lambda site: (site.list_start, site.list_end))


def minimization_groups(code, analysis, families=FAMILIES, *, prioritize_unused=True):
    """Return alternative singleton edit groups, fairly interleaved by site.

    Alternatives from the same list overlap and MUST NOT be applied jointly.
    Trying each group's edit against the same incumbent, then choosing the
    highest fully verified score, avoids conflating syntax size with reward.
    By default, exact members named by unused-simp-argument warnings precede
    the interleaved schedule; they still require verification and scoring.
    """
    sites = list_sites(code, analysis, families)
    priority = []
    if prioritize_unused:
        for site in sites:
            for i, (start, stop) in enumerate(site.elements):
                if any(
                    m.get("kind") == "linter.unusedSimpArgs"
                    and start <= m.get("start", -1) < m.get("end", -1) <= stop
                    for m in analysis.get("messages", [])
                ):
                    priority.append(site.remove(code, i, i + 1))
    alternatives = [site.alternatives(code) for site in sites]
    ordered = priority + [
        edits[i]
        for i in range(max(map(len, alternatives), default=0))
        for edits in alternatives
        if i < len(edits)
    ]
    # An unused-argument warning only changes trial order. It never licenses
    # acceptance without the same full verification and scoring as other edits.
    return [[edit] for edit in dict.fromkeys(ordered)]
