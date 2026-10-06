"""Gemini API-equivalent accounting and native streaming budget boundaries."""

from __future__ import annotations

from copy import deepcopy

import pytest

from proof_eval.harness.config import RunConfig
from proof_eval.providers import agy
from proof_eval.providers.costs import CostConfig, estimate_token_cost, generations_cost
from proof_eval.providers.spending import native_cost_guard


def init():
    return {
        "event": "init",
        "conversation_id": "conv",
        "init": {"model": "gemini-3.8-flash-high"},
    }


def step(index, *, state="DONE", input_tokens=100, output_tokens=50, cache=20):
    return {
        "event": "step_update",
        "step_update": {
            "conversation_id": "conv",
            "step_index": index,
            "state": state,
            "step_type": "agent_response",
            "usage": {
                "input_tokens": input_tokens,
                "cache_read_tokens": cache,
                "output_tokens": output_tokens,
                "thinking_tokens": 10,
            },
        },
    }


def test_repeated_step_usage_is_replaced_and_terminal_usage_is_not_added():
    events = [init(), step(0, state="ACTIVE"), step(0), step(1)]
    observed = agy.stream_usage(events)
    assert observed["input_tokens"] == 240
    assert observed["output_tokens"] == 100
    partial = agy.parse_events(events, "", -9)
    assert partial["usage_complete"] is False
    cost = generations_cost(CostConfig(agy.MODEL, "high"), [partial])
    assert cost["status"] == "unknown_usage" and cost["total_usd"] is None
    assert cost["known_usage_estimate"]["usage"] == observed
    events.append(
        {
            "event": "result",
            "result": {
                "conversation_id": "conv",
                "status": "SUCCESS",
                "response": "proof",
                "usage": {
                    "input_tokens": 200,
                    "cache_read_tokens": 40,
                    "output_tokens": 100,
                    "thinking_tokens": 20,
                },
            },
        }
    )
    assert agy.stream_usage(events) == observed
    assert agy.parse_events(events, "", 0)["usage_complete"] is True


def test_missing_or_foreign_usage_is_not_zero_filled():
    foreign = step(0)
    foreign["step_update"]["conversation_id"] = "another"
    missing = step(0)
    del missing["step_update"]["usage"]["output_tokens"]
    assert agy.stream_usage([init(), foreign, missing]) is None
    assert agy.parse_events([init(), foreign, missing], "", -9)["token_usage"] is None


def test_gemini_does_not_inherit_codex_long_context_or_extra_reasoning_charges():
    usage = agy.token_usage(
        {
            "input_tokens": 400000,
            "cache_read_tokens": 100000,
            "output_tokens": 100000,
            "thinking_tokens": 50000,
        }
    )
    config = CostConfig(agy.MODEL, "high")
    estimate = estimate_token_cost(config, usage, scope="request")
    assert estimate["total_usd"] == pytest.approx(0.6825)
    assert estimate["all_requests_long_context_usd"] == estimate["total_usd"]
    without_thinking = deepcopy(usage)
    without_thinking["reasoning_output_tokens"] = 0
    assert (
        estimate_token_cost(config, without_thinking)["total_usd"]
        == estimate["total_usd"]
    )
    assert estimate["source"] == "https://ai.google.dev/gemini-api/docs/pricing"
    assert estimate["rate_card_date"] == "2026-10-06"


def test_cost_tracking_routes_to_the_host_monitor_with_remaining_budget():
    config = RunConfig(provider="agy", budget_tracking="cost", budget_usd_per_problem=3)
    assert config.conditions == ((agy.MODEL, "high"),)
    guard = native_cost_guard("agy", CostConfig(agy.MODEL, "high"), 1.25)
    assert guard["kind"] == "host_stream_usd" and guard["remaining_usd"] == 1.25
    assert guard["rate_card"]["gateway_price_verified"] is False
    with pytest.raises(ValueError, match="unpriced"):
        RunConfig(provider="lemex", budget_tracking="cost")
    with pytest.raises(ValueError, match="standard"):
        CostConfig(agy.MODEL, "high", service_tier="fast")
