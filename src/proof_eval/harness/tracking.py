"""Validated opt-in restart limits and explicit host stopping decisions."""

from __future__ import annotations

from math import isfinite
from typing import Literal, Sequence

from proof_eval.providers.costs import UNPRICED_MODELS, CostConfig, generations_cost
from proof_eval.providers.registry import OPEN_MODELS
from proof_eval.providers.retries import retryable_transport_failure
from proof_eval.providers.spending import native_cost_guard

from .carryover import carried_generations

BudgetTracking = Literal["auto", "cost", "time"] | None
CLEANUP_RESERVE_SECONDS = 30.0
ATTEMPT_EVIDENCE_VERSION = 1


def resolve_budgets(
    tracking: BudgetTracking,
    timeout: float | None,
    conditions: Sequence[tuple[str, str]],
) -> tuple[BudgetTracking, float | None]:
    """Choose the track budget; an explicit timeout remains an opt-in watchdog."""
    if tracking == "auto":
        open_models = [model in OPEN_MODELS for model, _ in conditions]
        if any(open_models) and not all(open_models):
            raise ValueError("Automatic budgets require conditions from one track")
        tracking = "time" if all(open_models) else "cost"
    if timeout is None and tracking != "cost":
        timeout = 57 * 60
    return tracking, timeout


def validate_budgets(
    tracking: BudgetTracking,
    usd: float,
    restarts: int,
    timeout: float | None,
    conditions: Sequence[tuple[str, str]],
) -> None:
    if tracking not in (None, "cost", "time"):
        raise ValueError("budget_tracking must be None, 'cost', or 'time'")
    for name, value in (
        ("budget_usd_per_problem", usd),
        ("problem_timeout_seconds", timeout),
    ):
        if name == "problem_timeout_seconds" and value is None and tracking == "cost":
            continue
        if type(value) not in (int, float) or not isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be positive and finite")
    if type(restarts) is not int or restarts < 0:
        raise ValueError("max_budget_restarts must be a nonnegative integer")
    if tracking == "cost":
        for model, _ in conditions:
            if model in UNPRICED_MODELS:
                raise ValueError(
                    f"Cost budget tracking cannot track unpriced model: {model}"
                )


def attempt_cost(
    config: dict,
    model: str,
    effort: str,
    generations: list,
    *,
    name: str | None = None,
    final: bool = False,
) -> dict:
    prior = carried_generations(config, name, model, effort) if name is not None else []
    if config.get("budget_carryover") and name is None:
        raise ValueError("A theorem name is required for carried budget accounting")
    if not generations and not prior and not final:
        return {"status": "not_started", "total_usd": 0.0, "attempts": 0}
    cost = generations_cost(
        CostConfig(model, effort, **config.get("cost_assumptions", {})),
        prior + generations,
        budget_usd=config.get("budget_usd_per_problem", 3.0),
    )
    return {**cost, "carried_attempts": len(prior)} if prior else cost


def stop_decision(
    config: dict,
    generation: dict,
    cost: dict,
    *,
    unavailable: bool,
    round_number: int,
    time_remaining: float | None,
    transport_restarts_used: int = 0,
) -> dict | None:
    """Admit successful optimization restarts or bounded terminal-error recovery."""
    termination = generation.get("termination")
    if termination == "cost_limit":
        return {
            "kind": "cost_limit",
            "reason": (
                "Host stream cost guard stopped the attempt"
                if config.get("provider") == "agy"
                else "Native cost guard stopped the attempt"
            ),
        }
    if unavailable:
        return {
            "kind": "infrastructure",
            "reason": "Host verification is unavailable; no further request was sampled",
        }
    tracking = config.get("budget_tracking")
    recoverable = retryable_transport_failure(generation)
    if generation["status"] != "received" and (
        not recoverable
        or not config.get("max_transport_restarts", 0)
        or (time_remaining is None and tracking != "cost")
    ):
        return {"kind": "infrastructure", "reason": generation.get("error")}
    if generation["status"] == "received" and tracking is None:
        return {"kind": "model_final", "reason": "Agent returned a final declaration"}
    if tracking == "cost":
        total = cost.get("total_usd")
        if total is None:
            return {
                "kind": cost["status"],
                "reason": "Cumulative spending is unknown; no further request was sampled",
            }
        if total >= config.get("budget_usd_per_problem", 3.0) - 1e-12:
            return {
                "kind": "cost_limit",
                "reason": "Cumulative estimated cost reached the problem budget",
            }
        guard = native_cost_guard(
            config.get("provider", "codex"),
            CostConfig(**cost["configuration"]),
            config.get("budget_usd_per_problem", 3.0) - total,
        )
        if guard.get("limit_tokens") == 0:
            return {
                "kind": "cost_reserve",
                "reason": "Remaining estimated budget cannot fund one conservatively priced output token",
            }
    if time_remaining is not None and time_remaining <= CLEANUP_RESERVE_SECONDS:
        return {
            "kind": "cleanup_reserve",
            "reason": "Remaining whole-problem time is reserved for final cleanup",
        }
    if recoverable:
        if transport_restarts_used >= config.get("max_transport_restarts", 0):
            return {
                "kind": "transport_recovery_limit",
                "reason": "Configured terminal transport recovery limit reached",
            }
        return None
    if round_number - transport_restarts_used >= config.get("max_budget_restarts", 20):
        return {
            "kind": "restart_limit",
            "reason": "Configured restart safety limit reached",
        }
    return None
