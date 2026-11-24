"""Native spend guards; sampling defaults stay unchanged.

Both CLIs check spending between upstream responses. A response already in
flight may overshoot, so these guards do not certify a hard invoice ceiling.
Codex charges all prefill conservatively, including cached input.
"""

from __future__ import annotations

from dataclasses import asdict
from decimal import ROUND_FLOOR, Decimal
from math import isfinite

from .costs import GEMINI_MODEL, RATES, TIERS, CostConfig, rate_card
from .retries import reconnect_notice

NATIVE_COST_GUARD_VERSION = 2


def native_cost_guard(
    provider: str,
    config: CostConfig,
    remaining_usd: float,
    *,
    version: int = NATIVE_COST_GUARD_VERSION,
) -> dict:
    """Build a spend guard; version 1 preserves historical audit arithmetic."""
    if type(version) is not int or version not in (1, NATIVE_COST_GUARD_VERSION):
        raise ValueError("Unsupported native cost guard version")
    if (
        type(remaining_usd) not in (float, int)
        or not isfinite(remaining_usd)
        or remaining_usd <= 0
    ):
        raise ValueError("Remaining cost budget must be positive and finite")
    if provider == "claude":
        return {"kind": "native_usd", "remaining_usd": remaining_usd}
    if provider == "agy" and config.model == GEMINI_MODEL:
        return {
            "kind": "host_stream_usd",
            "remaining_usd": remaining_usd,
            "configuration": asdict(config),
            "rate_card": rate_card("agy"),
            "pricing": "standard_gemini_api_equivalent",
        }
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
        # Native reminders must be positive and strictly below the limit.
        # A one-token guard still enforces spending, without a reminder.
        "reminder_at_remaining_tokens": (
            [max(1, tokens // 10)] if version == 1 or tokens > 1 else []
        ),
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
        failures = [
            e
            for e in events
            if e.get("type") in ("error", "turn.failed") and not reconnect_notice(e)
        ]
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
