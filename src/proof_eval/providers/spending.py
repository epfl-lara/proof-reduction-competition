"""Native spend guards; sampling defaults stay unchanged.

Both CLIs check spending between upstream responses. A response already in
flight may overshoot, so these guards do not certify a hard invoice ceiling.
Codex charges all prefill conservatively, including cached input.
"""

from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal
from math import isfinite

from .costs import RATES, TIERS, CostConfig


def native_cost_guard(provider: str, config: CostConfig, remaining_usd: float) -> dict:
    if (
        type(remaining_usd) not in (float, int)
        or not isfinite(remaining_usd)
        or remaining_usd <= 0
    ):
        raise ValueError("Remaining cost budget must be positive and finite")
    if provider == "claude":
        return {"kind": "native_usd", "remaining_usd": remaining_usd}
    if provider != "codex" or config.model not in RATES:
        raise ValueError("Native cost tracking is unavailable for this provider/model")
    multiplier = Decimal(str(TIERS[config.service_tier])) * (
        Decimal("1.1") if config.regional_processing else 1
    )
    rates = RATES[config.model]
    # Conservative across cache writes and both context bands. Accounting in
    # result.json still uses the frozen, explicit API-equivalent assumptions.
    prefill = max(Decimal(str(rate)) for rate in rates[:3]) * multiplier * 2
    sampling = Decimal(str(rates[3])) * multiplier * Decimal("1.5")
    tokens = int(
        (Decimal(str(remaining_usd)) * 1000000 / sampling).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    return {
        "kind": "native_weighted_tokens",
        "remaining_usd": remaining_usd,
        "limit_tokens": tokens,
        "prefill_token_weight": float(prefill / sampling),
        "sampling_token_weight": 1.0,
        "reminder_at_remaining_tokens": [max(1, tokens // 10)],
        "pricing": "conservative_cache_write_and_long_context",
    }


def codex_budget_settings(guard: dict | None) -> dict:
    if guard is None:
        return {}
    if guard["kind"] != "native_weighted_tokens":
        raise ValueError("Expected the native Codex weighted-token guard")
    if guard["limit_tokens"] <= 0:
        raise ValueError("Remaining cost budget cannot fund an output token")
    return {
        "features.rollout_budget.enabled": True,
        **{
            "features.rollout_budget." + field: guard[field]
            for field in (
                "limit_tokens",
                "prefill_token_weight",
                "sampling_token_weight",
                "reminder_at_remaining_tokens",
            )
        },
    }


def native_cost_stop(provider: str, events: list[dict], guard: dict | None) -> bool:
    """Recognize an explicit native limit, never a generic failed request."""
    if guard is None:
        return False
    if provider == "codex":
        failures = [e for e in events if e.get("type") in ("error", "turn.failed")]
        return bool(failures) and all(
            (e.get("message") or e.get("error", {}).get("message"))
            == "shared rollout token budget exhausted"
            for e in failures
        )
    if provider == "claude":
        terminal = [e for e in events if e.get("type") == "result"]
        return (
            len(terminal) == 1 and terminal[0].get("subtype") == "error_max_budget_usd"
        )
    return False
