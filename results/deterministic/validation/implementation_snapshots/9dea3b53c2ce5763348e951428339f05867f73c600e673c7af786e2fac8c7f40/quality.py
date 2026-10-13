"""Benchmark-shaped selection and observable source-task quality checks.

Length matching is a sampling contract, not a claim of mathematical difficulty.
Compiler and heartbeat readiness must be established separately.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from statistics import median
from typing import Any

from proof_eval.evidence.io import sha
from proof_eval.verification.metrics import (
    strip_comments,
    token_count,
    validate_candidate,
)

# These broad bands avoid fitting individual statements in a small benchmark.
TOKEN_BAND_EDGES = (500, 1000, 1500)


def token_band(tokens: int) -> int:
    """Return the published sampling band's index."""
    return sum(tokens >= edge for edge in TOKEN_BAND_EDGES)


@dataclass(frozen=True)
class QualityConfig:
    """Minimum source proof size and diversity limits for a task release."""

    min_tokens: int = 222
    max_tokens: int = 5000
    min_proof_lines: int = 47
    max_per_file: int = 8
    max_per_group: int = 32
    seed: int = 20261008


def intake_reason(row: dict[str, Any], config: QualityConfig) -> str | None:
    """Check actual proof text, denominator and obvious tautological targets.

    Contradiction lemmas with assumptions are legitimate mathematical tasks;
    they are not rejected just because their conclusion is False. This limited
    syntactic screen does not establish semantic nontriviality or correctness.
    """
    try:
        _, body = validate_candidate(row, row["src"])
    except (ValueError, KeyError) as exc:
        return f"invalid_original:{exc}"
    if token_count(body) != row["proof_length"]:
        return "incorrect_token_denominator"
    if not config.min_tokens <= row["proof_length"] <= config.max_tokens:
        return "outside_token_bounds"
    lines = sum(bool(line.strip()) for line in strip_comments(body).splitlines())
    if lines < config.min_proof_lines:
        return "too_few_proof_lines"
    # Only a single, unparenthesized identifier on each side is recognized.
    # More complicated propositions require elaboration and manual review.
    statement = strip_comments(row["statement"])
    if re.search(r":\s*True\s*$", statement):
        return "trivial_true_target"
    if re.search(r":\s*([\w.']+)\s*(?:=|↔|→|≤)\s*\1\s*$", statement):
        return "reflexive_target"
    return None


def band_targets(reference: list[dict[str, Any]], limit: int) -> list[int]:
    """Apportion a fixed cohort by the benchmark's proof-length distribution."""
    if not reference or type(limit) is not int or limit < 1:
        raise ValueError("Expected nonempty benchmark and positive integer limit")
    counts = Counter(token_band(row["proof_length"]) for row in reference)
    weights = [counts[i] * limit for i in range(len(TOKEN_BAND_EDGES) + 1)]
    targets = [weight // len(reference) for weight in weights]
    order = sorted(
        range(len(targets)), key=lambda i: (-(weights[i] % len(reference)), i)
    )
    for i in order[: limit - sum(targets)]:
        targets[i] += 1
    return targets


def select_like_benchmark(
    candidates: list[dict[str, Any]],
    reference: list[dict[str, Any]],
    *,
    limit: int,
    config: QualityConfig,
) -> list[dict[str, Any]]:
    """Match length bands while cycling sources and keeping project diversity.

    Inputs must have already passed intake. Scarce long-proof bands cause an
    explicit failure, rather than silently filling their quota with short tasks.
    Names, normalized signatures and proof content are globally unique. Task
    dictionaries are returned unchanged so existing reference identities survive.
    """
    if config.max_per_file < 1 or config.max_per_group < 1:
        raise ValueError("Diversity limits must be positive")
    targets = band_targets(reference, limit)
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        grouped[token_band(row["proof_length"]), row["source"]].append(row)
    queues = {
        key: deque(
            sorted(
                rows,
                key=lambda row: (
                    row["training_metadata"].get("task_role") == "supporting_lemma",
                    sha(f"{config.seed}:{row['training_metadata']['id']}"),
                ),
            )
        )
        for key, rows in sorted(grouped.items())
    }
    file_counts: Counter[tuple[str, str]] = Counter()
    group_counts: Counter[str] = Counter()
    names: set[str] = set()
    signatures: set[str] = set()
    contents: set[str] = set()
    selected: list[dict[str, Any]] = []
    for band in reversed(range(len(targets))):
        keys = [key for key in queues if key[0] == band]
        count = 0
        while keys and count < targets[band]:
            for key in list(keys):
                queue = queues[key]
                while queue:
                    row = queue.popleft()
                    meta = row["training_metadata"]
                    file_key = (
                        row["source"],
                        row["file_path"] or meta.get("origin_file_path", ""),
                    )
                    group = meta["split_group"]
                    group_cap = (
                        config.max_per_file
                        if row["source"] == "putnambench"
                        else config.max_per_group
                    )
                    if (
                        file_counts[file_key] >= config.max_per_file
                        or group_counts[group] >= group_cap
                        or row["name"] in names
                        or meta["signature_key"] in signatures
                        or meta["content_key"] in contents
                    ):
                        continue
                    selected.append(row)
                    file_counts[file_key] += 1
                    group_counts[group] += 1
                    names.add(row["name"])
                    signatures.add(meta["signature_key"])
                    contents.add(meta["content_key"])
                    count += 1
                    break
                if not queue:
                    keys.remove(key)
                if count == targets[band]:
                    break
        if count != targets[band]:
            raise ValueError(
                f"Insufficient distinct tasks in token band {band}: "
                f"selected {count}, required {targets[band]}"
            )
    return selected


def shape_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Report proof-body sizes, excluding statement, comments and file context."""
    tokens = [row["proof_length"] for row in rows]
    lines = [
        sum(
            bool(line.strip())
            for line in strip_comments(
                validate_candidate(row, row["src"])[1]
            ).splitlines()
        )
        for row in rows
    ]
    counts = Counter(token_band(length) for length in tokens)
    return {
        "count": len(rows),
        "proof_tokens": {
            "min": min(tokens),
            "median": median(tokens),
            "max": max(tokens),
        },
        "proof_nonempty_lines": {
            "min": min(lines),
            "median": median(lines),
            "max": max(lines),
        },
        "token_band_edges": list(TOKEN_BAND_EDGES),
        "token_band_counts": [counts[i] for i in range(len(TOKEN_BAND_EDGES) + 1)],
        "selected_by_source": dict(
            sorted(Counter(row["source"] for row in rows).items())
        ),
    }
