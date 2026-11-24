"""Validated opt-in restart limits and explicit host stopping decisions."""

from __future__ import annotations

from dataclasses import asdict
from math import isfinite
from typing import Literal, Sequence

from proof_eval.providers.costs import (
    UNPRICED_MODELS,
    USAGE_FIELDS,
    CostConfig,
    estimate_token_cost,
    generations_cost,
    normalize_token_usage,
)
from proof_eval.providers.registry import MODEL_TIMEOUT_SECONDS, MODEL_TRACKS
from proof_eval.providers.retries import retryable_transport_failure
from proof_eval.providers.spending import native_cost_guard

from .archived_schedules import archived_generations_cost, attempt_condition
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
        try:
            open_models = [MODEL_TRACKS[model] == "open" for model, _ in conditions]
        except KeyError as error:
            raise ValueError("Unclassified model track: " + error.args[0]) from None
        if any(open_models) and not all(open_models):
            raise ValueError("Automatic budgets require conditions from one track")
        tracking = "time" if all(open_models) else "cost"
    if timeout is None and tracking != "cost":
        defaults = {
            MODEL_TIMEOUT_SECONDS.get(model, 57 * 60) for model, _ in conditions
        }
        if len(defaults) != 1:
            raise ValueError(
                "Conditions with different model time defaults require an explicit timeout"
            )
        timeout = defaults.pop()
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
    primary = CostConfig(model, effort, **config.get("cost_assumptions", {}))
    if config.get("first_attempt_condition") is not None:
        if prior:
            raise ValueError("Scheduled attempts cannot reuse another run's budget")
        configurations = [
            CostConfig(
                *attempt_condition(config, model, effort, number),
                **config.get("cost_assumptions", {}),
            )
            for number in range(len(generations))
        ]
        cost = {
            # The primary configuration prices the next (continuation) guard.
            "configuration": asdict(primary),
            **archived_generations_cost(
                configurations,
                generations,
                budget_usd=config.get("budget_usd_per_problem", 3.0),
            ),
        }
    else:
        cost = generations_cost(
            primary,
            prior + generations,
            budget_usd=config.get("budget_usd_per_problem", 3.0),
        )
    if (
        cost["status"] == "unknown_usage"
        and config.get("provider", "codex") == "codex"
        and config.get("usage_policy") == "best_effort"
    ):
        configurations = [
            CostConfig(
                *attempt_condition(config, model, effort, number),
                **config.get("cost_assumptions", {}),
            )
            for number in range(len(prior + generations))
        ]
        cost = _best_effort_cost(
            primary,
            configurations,
            prior + generations,
            cost,
            budget_usd=config.get("budget_usd_per_problem", 3.0),
        )
    return {**cost, "carried_attempts": len(prior)} if prior else cost


def _best_effort_cost(
    primary: CostConfig,
    configurations: Sequence[CostConfig],
    generations: Sequence[dict],
    strict_cost: dict,
    *,
    budget_usd: float,
) -> dict:
    """Price validated terminal trace estimates while preserving reported usage."""
    if not generations:
        return strict_cost
    costs = []
    reported_costs = []
    estimates = []
    unknown = []
    totals = dict.fromkeys(USAGE_FIELDS, 0)
    reported_totals = dict.fromkeys(USAGE_FIELDS, 0)
    for index, (configuration, generation) in enumerate(
        zip(configurations, generations)
    ):
        try:
            reported = normalize_token_usage(
                generation.get("token_usage", generation.get("codex_usage"))
            )
        except ValueError:
            return strict_cost
        reported_cost = estimate_token_cost(
            configuration, reported, budget_usd=budget_usd
        )
        usage = reported
        if generation.get("usage_complete") is False:
            unknown.append(index)
            trace_hash = generation.get("response_usage_sha256")
            if not (
                generation.get("response_usage_schema_version") == 2
                and generation.get("structurally_valid") is True
                and generation.get("estimated_usage_complete") is True
                and generation.get("status")
                in ("received", "transport_error", "budget_exhausted")
                and isinstance(trace_hash, str)
                and len(trace_hash) == 64
                and all(character in "0123456789abcdef" for character in trace_hash)
                and isinstance(generation.get("usage_estimates"), list)
                and generation["usage_estimates"]
            ):
                return strict_cost
            try:
                usage = normalize_token_usage(generation.get("estimated_token_usage"))
                normalize_token_usage(
                    {field: usage[field] - reported[field] for field in USAGE_FIELDS}
                )
            except ValueError:
                return strict_cost
            estimates.append(
                {
                    "attempt": index,
                    "response_usage_sha256": trace_hash,
                    "usage_estimates": generation["usage_estimates"],
                }
            )
        cost = estimate_token_cost(configuration, usage, budget_usd=budget_usd)
        if cost["total_usd"] is None or reported_cost["total_usd"] is None:
            return strict_cost
        costs.append(cost)
        reported_costs.append(reported_cost)
        for field in USAGE_FIELDS:
            totals[field] += usage[field]
            reported_totals[field] += reported[field]
    if not unknown:
        return strict_cost
    total = sum(cost["total_usd"] for cost in costs)
    reported_total = sum(cost["total_usd"] for cost in reported_costs)
    return {
        **strict_cost,
        "status": "estimated_incomplete_usage",
        "basis": "public_api_equivalent_best_effort",
        "configuration": asdict(primary),
        "configurations": [asdict(configuration) for configuration in configurations],
        "attempt_costs": costs,
        "reported_attempt_costs": reported_costs,
        "attempts": len(generations),
        "usage": totals,
        "reported_usage": reported_totals,
        "complete_usage": False,
        "total_usd": total,
        "reported_total_usd": reported_total,
        "estimated_unreported_usd": total - reported_total,
        "budget_usd": budget_usd,
        "remaining_usd_at_assumed_rates": budget_usd - total,
        "over_budget_at_assumed_rates": total > budget_usd + 1e-12,
        "unknown_attempt_indices": unknown,
        "estimated_attempt_indices": unknown,
        "usage_estimates": estimates,
        "all_uncached_as_cache_writes_usd": sum(
            cost["all_uncached_as_cache_writes_usd"] for cost in costs
        ),
        "all_requests_long_context_usd": sum(
            cost["all_requests_long_context_usd"] for cost in costs
        ),
        "assumptions": [
            "Each attempt uses the frozen rates for its scheduled model and effort.",
            "Missing native counters use the recorded per-request estimates, including explicit zero-cost assumptions for failures without partial output.",
            "Reported usage remains a lower bound; estimated spending shares the original problem budget.",
            "API-equivalent estimates are not invoices or hard cost ceilings.",
        ],
    }


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
    estimated_guard_stop = (
        termination == "cost_limit"
        and generation.get("status") == "budget_exhausted"
        and generation.get("response_usage_schema_version") == 2
        and generation.get("structurally_valid") is True
        and (
            generation.get("estimated_usage_complete") is True
            or generation.get("usage_complete") is True
        )
        and config.get("usage_policy") == "best_effort"
        and config.get("provider", "codex") == "codex"
        and config.get("budget_tracking") == "cost"
        and cost.get("total_usd") is not None
    )
    if termination == "cost_limit" and not estimated_guard_stop:
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
    if (
        generation.get("status") == "budget_exhausted"
        and termination != "cost_limit"
        and time_remaining is not None
        and time_remaining <= 0
    ):
        return {"kind": "time_limit", "reason": "Whole-problem wall deadline reached"}
    tracking = config.get("budget_tracking")
    recoverable = retryable_transport_failure(generation)
    if (
        generation["status"] != "received"
        and not estimated_guard_stop
        and (
            not recoverable
            or not config.get("max_transport_restarts", 0)
            or (time_remaining is None and tracking != "cost")
        )
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
    if time_remaining is not None and time_remaining <= config.get(
        "cleanup_reserve_seconds", CLEANUP_RESERVE_SECONDS
    ):
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
