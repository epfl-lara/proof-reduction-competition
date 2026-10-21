"""Repeated subproofs by first-order anti-unification of token sequences.

A pair whose differences are only consistent renamings, mirror names, or one
variable versus a term has a common generalization: a candidate for one local
lemma (cut introduction), a merged `case a | b`, or a symmetry argument.
"""

from __future__ import annotations

import difflib
import re

from proof_eval.optimization.proof_theory.records import AnalysisConfig, SharedSubproof
from proof_eval.optimization.proof_theory.tree import CASE_HEADER, Step, TokenCounter

# Duality pairs: two branches differing only by these names are mirror images.
DUAL_NAMES = (
    ("left", "right"),
    ("fst", "snd"),
    ("inl", "inr"),
    ("L", "R"),
    ("1", "2"),
    ("mp", "mpr"),
    ("le", "ge"),
    ("lt", "gt"),
    ("min", "max"),
    ("choiceL", "choiceR"),
    ("follow_fst", "follow_snd"),
)

_LEX = re.compile(r"[\w'.]+|[^\s\w]")
_LAYOUT = frozenset({"·", ".", ";"})
_DUAL_MAP = {**dict(DUAL_NAMES), **{b: a for a, b in DUAL_NAMES}}
_DUAL = re.compile(
    r"(?:(?<![\w'])|(?<=[._]))("
    + "|".join(sorted(map(re.escape, _DUAL_MAP), key=len, reverse=True))
    + r")(?![\w'])"
)
_SINGLE_NAME = re.compile(r"[\w']+")


def dualize(text: str) -> str:
    """Swap every dual name at once, including `.1`/`.2` and `_fst`/`_snd`."""
    return _DUAL.sub(lambda m: _DUAL_MAP[m.group(1)], text)


def classify_holes(holes: list[tuple[list[str], list[str]]]) -> list[str]:
    """Classify each anti-unification hole.

    `renaming` keeps one bijection of single names across all holes, `dual`
    swaps mirror names, `instance` maps one variable consistently to a term
    (first-order generalization), `layout` differs only by bullets/separators.
    """
    forward: dict[str, str] = {}
    backward: dict[str, str] = {}
    kinds = []
    for left, right in holes:
        a, b = " ".join(left), " ".join(right)
        single = len(left) == len(right) == 1 and all(
            _SINGLE_NAME.fullmatch(x) for x in (a, b)
        )
        if set(left + right) <= _LAYOUT:
            kinds.append("layout")
        elif (
            single
            and forward.get(a, b) == b
            and backward.get(b, a) == a
            and dualize(a) != b
        ):
            forward[a], backward[b] = b, a
            kinds.append("renaming")
        elif a and b and dualize(a) == b:
            kinds.append("dual")
        elif len(left) == 1 and _SINGLE_NAME.fullmatch(a) and forward.get(a, b) == b:
            forward[a] = b
            kinds.append("instance")
        else:
            kinds.append("structural")
    return kinds


def _verdict(kinds: list[str]) -> str:
    structural = kinds.count("structural")
    if structural:
        return f"template({structural})"
    for verdict in ("instance", "dual"):
        if verdict in kinds:
            return verdict
    return "alpha"


def anti_unify(a: list[str], b: list[str]) -> tuple[float, list, list[str]]:
    """Similarity modulo renaming, holes, and hole classes of two token lists.

    Equal-length replacements are split into aligned single-token holes, so a
    renamed binder list is a set of renamings rather than one structural hole.
    """
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    holes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and i2 - i1 == j2 - j1:
            holes.extend(([x], [y]) for x, y in zip(a[i1:i2], b[j1:j2]))
        else:
            holes.append((a[i1:i2], b[j1:j2]))
    kinds = classify_holes(holes)
    common = sum(block.size for block in matcher.get_matching_blocks())
    aligned = sum(
        len(x) for (x, y), kind in zip(holes, kinds) if kind in {"renaming", "dual"}
    )
    layout = sum(
        len(x) + len(y) for (x, y), kind in zip(holes, kinds) if kind == "layout"
    )
    total = len(a) + len(b) - layout
    return (2 * (common + aligned) / total if total else 1.0), holes, kinds


def comparable(step: Step) -> list[str]:
    """Tokens of a subproof without its case label or branch binders."""
    header = CASE_HEADER.sub("", step.text, count=1)
    return _LEX.findall("\n".join([header] + [c.subtree() for c in step.children]))


def find_shared_subproofs(
    root: Step, tokens: TokenCounter, config: AnalysisConfig
) -> list[SharedSubproof]:
    """Greedy, non-overlapping pairs of similar subproofs, largest saving first.

    A subproof may serve as the template for several copies; a copy is counted
    once and never also used as a template.
    """
    nodes = [
        step
        for step in root.walk()
        if step is not root
        and step.children
        and tokens(step) >= config.min_subproof_tokens
    ]
    lexed = {id(step): comparable(step) for step in nodes}
    spans = {id(step): set(range(step.line, step.last_line() + 1)) for step in nodes}
    candidates = []
    for i, first in enumerate(nodes):
        for second in nodes[i + 1 :]:
            if spans[id(first)] & spans[id(second)]:
                continue
            a, b = lexed[id(first)], lexed[id(second)]
            if min(len(a), len(b)) < config.min_length_ratio * max(len(a), len(b)):
                continue
            similarity, holes, kinds = anti_unify(a, b)
            if similarity < config.min_similarity:
                continue
            saving = max(tokens(second) - 2 * kinds.count("structural") - 3, 0)
            record = SharedSubproof(
                first.line,
                second.line,
                round(similarity, 6),
                _verdict(kinds),
                tuple((" ".join(x), " ".join(y)) for x, y in holes),
                saving,
            )
            candidates.append((saving, first, second, record))
    candidates.sort(key=lambda c: (-c[0], c[1].line, c[2].line))
    removed: set[int] = set()
    templates: set[int] = set()
    chosen = []
    for _, first, second, record in candidates:
        kept, copy = spans[id(first)], spans[id(second)]
        if copy & (removed | templates) or kept & removed:
            continue
        removed |= copy
        templates |= kept
        chosen.append(record)
    return chosen
