"""Explain existing scores without measuring proofs or changing selection."""

from __future__ import annotations

import math
from collections.abc import Sequence

from proof_eval.verification.feedback import all_versions_passed

COMPONENTS = {
    "length": "length_reduction_pct",
    "heartbeats": "heartbeat_reduction_pct",
    "compatibility": "compatibility_pct",
}


def _components(evaluation: dict, versions: Sequence[str]) -> dict[str, float] | None:
    if not all_versions_passed(evaluation, versions):
        return None
    scores = evaluation.get("scores", {})
    result = {}
    for name, field in COMPONENTS.items():
        value = scores.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            return None
        result[name] = float(value)
    return result


def component_deltas(
    candidate: dict, previous_best: dict, versions: Sequence[str]
) -> dict[str, float] | None:
    """Return contributions to combined-score change for two eligible proofs."""
    current = _components(candidate, versions)
    previous = _components(previous_best, versions)
    if current is None or previous is None:
        return None
    return {name: (current[name] - previous[name]) / 3 for name in COMPONENTS}


def remaining_score_loss(
    evaluation: dict, versions: Sequence[str]
) -> dict[str, float] | None:
    """Return token/heartbeat loss from the ideal zero-cost proof, not a forecast."""
    components = _components(evaluation, versions)
    if components is None:
        return None
    return {name: (100 - components[name]) / 3 for name in ("length", "heartbeats")}
