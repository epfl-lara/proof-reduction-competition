"""Read-only identity and pricing compatibility for retired mixed-model runs."""

from __future__ import annotations

from dataclasses import asdict
from typing import Sequence

from proof_eval.providers.codex import MODELS
from proof_eval.providers.costs import CostConfig, generations_cost


def validate_archive(config: dict) -> None:
    """Validate saved schedule metadata without permitting another model call."""
    first = config.get("first_attempt_condition")
    if first is None:
        return
    if not (
        config.get("provider") == "codex"
        and config.get("mode") == "score_edges"
        and len(config["conditions"]) == 1
        and config.get("budget_tracking") == "cost"
        and isinstance(first, (tuple, list))
        and len(first) == 2
        and first[1] in MODELS.get(first[0], set())
    ):
        raise ValueError("Invalid archived mixed-model condition")


def attempt_condition(
    config: dict, model: str, effort: str, number: int
) -> tuple[str, str]:
    """Recover the expected identity for an archived request or cost estimate."""
    if number == 0 and config.get("first_attempt_condition") is not None:
        return tuple(config["first_attempt_condition"])
    return model, effort


def archived_generations_cost(
    configurations: Sequence[CostConfig],
    generations: Sequence[dict],
    *,
    budget_usd: float = 3.0,
) -> dict:
    """Reproduce the retired schedule's recorded cost schema for offline audit."""
    if len(configurations) != len(generations):
        raise ValueError("Each generation requires its archived cost configuration")
    costs = [
        generations_cost(config, [generation], budget_usd=budget_usd)
        for config, generation in zip(configurations, generations)
    ]
    unknown = [i for i, cost in enumerate(costs) if cost["total_usd"] is None]
    known = [cost.get("known_usage_estimate", cost) for cost in costs]
    known_total = sum(cost.get("total_usd") or 0.0 for cost in known)
    total = None if unknown or not costs else known_total
    return {
        "status": "unknown_usage" if total is None else "estimated",
        "basis": "public_api_equivalent",
        "configurations": [asdict(config) for config in configurations],
        "attempt_costs": costs,
        "attempts": len(costs),
        "total_usd": total,
        "budget_usd": budget_usd,
        "remaining_usd_at_assumed_rates": None if total is None else budget_usd - total,
        "over_budget_at_assumed_rates": (
            None if total is None else total > budget_usd + 1e-12
        ),
        "unknown_attempt_indices": unknown,
        "known_usage_estimate": {"total_usd": known_total},
        "all_uncached_as_cache_writes_usd": sum(
            cost.get("all_uncached_as_cache_writes_usd", 0.0) for cost in known
        ),
        "all_requests_long_context_usd": sum(
            cost.get("all_requests_long_context_usd", 0.0) for cost in known
        ),
        "assumptions": [
            "Each attempt uses the frozen rates for its scheduled model and effort.",
            "All attempts share one problem budget; missing usage remains unknown.",
            "API-equivalent estimates are not invoices or hard cost ceilings.",
        ],
    }
