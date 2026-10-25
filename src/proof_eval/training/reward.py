"""Reward only the host's independently checked best Arena score."""

from __future__ import annotations

import math
from dataclasses import dataclass


class UnscorableEpisode(RuntimeError):
    """Infrastructure/evidence failure; never turn it into model reward zero."""


def verified_score(evaluation: dict, required_versions: list[str]) -> float:
    if not required_versions or len(set(required_versions)) != len(required_versions):
        raise UnscorableEpisode("No unique required version set")
    if evaluation.get("status") != "passed":
        raise UnscorableEpisode("Best proof is not a passed evaluation")
    checks = evaluation.get("per_version", {})
    if set(checks) != set(required_versions):
        raise UnscorableEpisode("Missing or unexpected version verdict")
    if not all(checks[v].get("passed") is True for v in required_versions):
        raise UnscorableEpisode("Best proof did not pass every required Lean version")
    scores = evaluation.get("scores", {})
    axes = [
        scores.get(k)
        for k in (
            "length_reduction_pct",
            "heartbeat_reduction_pct",
            "compatibility_pct",
        )
    ]
    total = scores.get("combined_pct")
    if any(
        isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x)
        for x in [*axes, total]
    ):
        raise UnscorableEpisode("Undefined/non-finite Arena score")
    if not math.isclose(sum(axes) / 3, total, abs_tol=1e-8):
        raise UnscorableEpisode("Arena component/combined score mismatch")
    if not math.isclose(scores["compatibility_pct"], 100.0, abs_tol=1e-8):
        raise UnscorableEpisode("All-version best proof needs full compatibility")
    return float(total)


@dataclass
class ScorePotential:
    """Logged increments telescope to final gain. Only final gain enters GRPO."""

    original: float
    best: float
    selection_margin_pp: float = 0.05

    @classmethod
    def from_original(cls, evaluation: dict, versions: list[str]) -> "ScorePotential":
        value = verified_score(evaluation, versions)
        return cls(value, value)

    def observe_best(self, evaluation: dict, versions: list[str]) -> float:
        value = verified_score(evaluation, versions)
        if value + 1e-8 < self.best:
            raise UnscorableEpisode("Host best score regressed")
        increment = (value - self.best) / 100.0
        self.best = value
        return increment

    @property
    def reward(self) -> float:
        return (self.best - self.original) / 100.0


def validate_token_evidence(ids: list[int], logprobs: list[float]) -> None:
    if not ids or len(ids) != len(logprobs):
        raise UnscorableEpisode("Missing sampled IDs or behavior logprobs")
    if any(type(x) is not int or x < 0 for x in ids):
        raise UnscorableEpisode("Invalid sampled token IDs")
    if any(
        isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
        for x in logprobs
    ):
        raise UnscorableEpisode("Invalid behavior logprobs")
