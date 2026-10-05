"""Codex token-cost estimates at public API list prices (not subscription bills).

Use ``estimate_codex_cost`` on one Responses request or aggregated Codex usage;
the caller must select the context band for aggregates. Reprice saved runs with
``estimate_configuration`` before launching an unmeasured model configuration.
Reasoning effort changes usage, not the price of a token. Repricing another
model's trace is a scenario, not a prediction of the new model's usage.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from math import ceil, isfinite
from statistics import mean

RATE_CARD_DATE = "2026-10-04"
# USD per million: ordinary input, cached reads, cache writes, all output.
RATES = {
    "gpt-6.1-sol": (2.0, 0.10, 2.50, 10.0),
    "gpt-6-astra": (10.0, 1.0, 12.50, 50.0),
    "gpt-6-luna": (0.10, 0.01, 0.125, 0.50),
}
SOURCES = {
    model: "https://developers.openai.com/api/docs/models/" + model for model in RATES
}
TIERS = {"standard": 1.0, "fast": 2.0, "flex": 0.5, "batch": 0.5}
USAGE_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
)


@dataclass(frozen=True)
class CostConfig:
    model: str
    reasoning_effort: str
    service_tier: str = "standard"
    context_band: str = "short"
    regional_processing: bool = False

    def __post_init__(self):
        if self.model not in RATES:
            raise ValueError("No verified price for exact model: " + self.model)
        if self.reasoning_effort not in ("low", "medium", "high", "xhigh", "max"):
            raise ValueError("Unsupported reasoning effort")
        if self.service_tier not in TIERS or self.context_band not in ("short", "long"):
            raise ValueError("Unknown service tier or context band")
        if type(self.regional_processing) is not bool:
            raise ValueError("regional_processing must be boolean")


def rate_card():
    return {
        "verified_at": RATE_CARD_DATE,
        "currency": "USD",
        "unit": "per_million_tokens",
        "rates": {
            m: dict(zip(("input", "cached_input", "cache_write", "output"), v))
            for m, v in RATES.items()
        },
        "sources": SOURCES.copy(),
        "service_tier_multipliers": TIERS.copy(),
        "long_context_threshold_input_tokens_per_request": 272000,
        "long_context_input_multiplier": 2.0,
        "long_context_output_multiplier": 1.5,
        "regional_multiplier": 1.1,
    }


def _usage(raw):
    """Require complete counters; missing usage must never be priced as zero."""
    if not isinstance(raw, dict) or any(
        type(raw.get(k)) is not int or raw[k] < 0 for k in USAGE_FIELDS
    ):
        raise ValueError("Complete nonnegative integer Codex usage counters required")
    values = {k: raw[k] for k in USAGE_FIELDS}
    if (
        values["cached_input_tokens"] + values["cache_write_input_tokens"]
        > values["input_tokens"]
    ):
        raise ValueError("Cache counters exceed total input")
    if values["reasoning_output_tokens"] > values["output_tokens"]:
        raise ValueError("Reasoning is a subset of output tokens")
    return values


def _parts(config, usage, *, all_uncached_are_writes=False, long_context=False):
    multiplier = Decimal(str(TIERS[config.service_tier])) * (
        Decimal("1.1") if config.regional_processing else 1
    )
    prices = [Decimal(str(r)) * multiplier for r in RATES[config.model]]
    long_context = long_context or config.context_band == "long"
    if long_context:
        prices = [p * (Decimal("1.5") if i == 3 else 2) for i, p in enumerate(prices)]
    reads, writes = usage["cached_input_tokens"], usage["cache_write_input_tokens"]
    ordinary = usage["input_tokens"] - reads - writes
    if all_uncached_are_writes:
        writes += ordinary
        ordinary = 0
    counts = (ordinary, reads, writes, usage["output_tokens"])
    return {
        k: float(Decimal(n) * p / 1000000)
        for k, n, p in zip(
            ("input_usd", "cached_input_usd", "cache_write_usd", "output_usd"),
            counts,
            prices,
        )
    }


def estimate_codex_cost(
    config: CostConfig, usage: dict, *, scope="aggregate", budget_usd=3.0
):
    """Price reported tokens. For a request, infer its band from input count.

    Aggregate counts may exceed 272K through many short requests: never infer a
    long context from them. Return explicit cache-write/long-context scenarios
    because CLI totals cannot certify per-request tier, context or API replay.
    Output counters already include reasoning; do not charge it a second time.
    """
    usage = _usage(usage)
    if scope not in ("aggregate", "request"):
        raise ValueError("scope must be aggregate or request")
    if (
        not isinstance(budget_usd, (int, float))
        or not isfinite(budget_usd)
        or budget_usd <= 0
    ):
        raise ValueError("Budget must be positive and finite")
    if scope == "request":
        config = CostConfig(
            **{
                **asdict(config),
                "context_band": "long" if usage["input_tokens"] > 272000 else "short",
            }
        )
    parts = _parts(config, usage)
    total = sum(parts.values())
    return {
        "status": "estimated",
        "basis": "public_api_equivalent",
        "configuration": asdict(config),
        "rate_card_date": RATE_CARD_DATE,
        "source": SOURCES[config.model],
        "usage": usage,
        "usage_scope": scope,
        "breakdown_usd": parts,
        "total_usd": total,
        "budget_usd": budget_usd,
        "over_budget_at_assumed_rates": total > budget_usd + 1e-12,
        "remaining_usd_at_assumed_rates": budget_usd - total,
        "all_uncached_as_cache_writes_usd": sum(
            _parts(config, usage, all_uncached_are_writes=True).values()
        ),
        "all_requests_long_context_usd": sum(
            _parts(config, usage, long_context=True).values()
        ),
        "assumptions": [
            "Reasoning is included in output tokens.",
            "Local Lean checks carry no model API charge; their returned text is counted in subsequent input.",
            "Service tier and region are pricing assumptions, not verified billing metadata.",
            "For aggregates, the selected context band is an assumption for every underlying request.",
            "Codex subscription charges and future API cache-write behavior are not inferred.",
        ],
    }


def generations_cost(config: CostConfig, generations, *, budget_usd=3.0):
    """Add all attempts, including discarded proposals; expose missing usage."""
    totals = dict.fromkeys(USAGE_FIELDS, 0)
    unknown = []
    for i, generation in enumerate(generations):
        try:
            usage = _usage(generation.get("codex_usage"))
        except ValueError:
            unknown.append(i)
            continue
        for k in USAGE_FIELDS:
            totals[k] += usage[k]
    known = estimate_codex_cost(config, totals, budget_usd=budget_usd)
    if not generations or unknown:
        return {
            "status": "unknown_usage",
            "total_usd": None,
            "known_usage_estimate": known,
            "unknown_attempt_indices": unknown,
            "over_budget_at_assumed_rates": None,
        }
    return {**known, "attempts": len(generations), "unknown_attempt_indices": []}


def summarize_costs(problems, *, budget_usd=3.0):
    """Summarize named per-problem estimates. An affordable mean is not a pass."""
    problems = list(problems)
    if len({p["name"] for p in problems}) != len(problems):
        raise ValueError(
            "Duplicate problems; combine all attempts before summarizing costs"
        )
    known = [p for p in problems if p["cost"]["total_usd"] is not None]
    values = sorted(p["cost"]["total_usd"] for p in known)
    over = [p["name"] for p in known if p["cost"]["total_usd"] > budget_usd + 1e-12]
    return {
        "problems": len(problems),
        "known_cost_problems": len(known),
        "unknown_cost_problems": len(problems) - len(known),
        "total_usd": sum(values) if len(known) == len(problems) and problems else None,
        "known_subtotal_usd": sum(values),
        "mean_observed_usd": mean(values) if values else None,
        "p90_observed_usd": values[ceil(0.9 * len(values)) - 1] if values else None,
        "max_observed_usd": max(values) if values else None,
        "over_budget_problems": over,
        "budget_usd_per_problem": budget_usd,
        "all_observed_within_cap_at_assumed_rates": (
            not over if known and len(known) == len(problems) else None
        ),
    }


def estimate_configuration(config: CostConfig, saved_results, *, budget_usd=3.0):
    """Pre-run scenario: reprice saved problem traces at the target rates.

    Caller should pass one full matched source condition, not mix models or
    select cheap traces. This does not estimate a reasoning-effort multiplier.
    """
    results = list(saved_results)
    sources = sorted({(r["model"], r["effort"]) for r in results})
    if len(sources) != 1:
        raise ValueError("Use one source model/effort condition per scenario")
    problems = [
        {
            "name": r["name"],
            "cost": generations_cost(config, r["generations"], budget_usd=budget_usd),
        }
        for r in results
    ]
    return {
        "kind": "saved_usage_repricing_scenario",
        "configuration": asdict(config),
        "source_configuration": {
            "model": sources[0][0],
            "reasoning_effort": sources[0][1],
        },
        "summary": summarize_costs(problems, budget_usd=budget_usd),
        "problems": problems,
        "caveat": "Target usage is unmeasured. This reprices the source trace; it does not predict target performance or token usage.",
    }
