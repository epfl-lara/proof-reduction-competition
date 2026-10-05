"""Cost arithmetic, missing-usage handling and pre-run scenario boundaries."""

from copy import deepcopy

import pytest

from proof_eval.providers.costs import (
    CostConfig,
    estimate_codex_cost,
    estimate_configuration,
    generations_cost,
    summarize_costs,
)

USAGE = {
    "input_tokens": 1000000,
    "cached_input_tokens": 600000,
    "cache_write_input_tokens": 100000,
    "output_tokens": 100000,
    "reasoning_output_tokens": 80000,
}


def test_disjoint_token_prices_and_reasoning_is_not_billed_twice():
    cost = estimate_codex_cost(CostConfig("gpt-6.1-sol", "max"), USAGE)
    assert cost["breakdown_usd"] == {
        "input_usd": 0.6,
        "cached_input_usd": 0.06,
        "cache_write_usd": 0.25,
        "output_usd": 1.0,
    }
    assert cost["total_usd"] == pytest.approx(1.91)
    assert cost["all_uncached_as_cache_writes_usd"] == pytest.approx(2.06)
    no_reasoning = {**USAGE, "reasoning_output_tokens": 0}
    assert (
        estimate_codex_cost(CostConfig("gpt-6.1-sol", "low"), no_reasoning)["total_usd"]
        == cost["total_usd"]
    )


def test_context_threshold_applies_to_individual_requests_not_aggregates():
    cfg = CostConfig("gpt-6.1-sol", "max")
    short = estimate_codex_cost(cfg, USAGE)
    long = estimate_codex_cost(cfg, USAGE, scope="request")
    assert short["total_usd"] == pytest.approx(1.91)
    assert long["total_usd"] == pytest.approx(0.91 * 2 + 1.5)
    assert short["all_requests_long_context_usd"] == long["total_usd"]
    boundary = {
        **USAGE,
        "input_tokens": 272000,
        "cached_input_tokens": 0,
        "cache_write_input_tokens": 0,
    }
    assert (
        estimate_codex_cost(cfg, boundary, scope="request")["configuration"][
            "context_band"
        ]
        == "short"
    )
    boundary["input_tokens"] += 1
    assert (
        estimate_codex_cost(cfg, boundary, scope="request")["configuration"][
            "context_band"
        ]
        == "long"
    )
    fast = estimate_codex_cost(
        CostConfig("gpt-6.1-sol", "max", service_tier="fast", regional_processing=True),
        USAGE,
    )
    assert fast["total_usd"] == pytest.approx(1.91 * 2 * 1.1)


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        {**USAGE, "cached_input_tokens": -1},
        {**USAGE, "input_tokens": 1},
        {**USAGE, "output_tokens": True},
        {**USAGE, "reasoning_output_tokens": 100001},
    ],
)
def test_missing_or_inconsistent_usage_is_not_zero(bad):
    cfg = CostConfig("gpt-6.1-sol", "max")
    with pytest.raises(ValueError):
        estimate_codex_cost(cfg, bad)
    cost = generations_cost(
        cfg, [{"codex_usage": USAGE}, {"status": "failed", "codex_usage": bad}]
    )
    assert cost["total_usd"] is None and cost["over_budget_at_assumed_rates"] is None
    assert cost["unknown_attempt_indices"] == [1]
    assert cost["known_usage_estimate"]["total_usd"] == pytest.approx(1.91)


def test_all_attempts_count_and_per_problem_cap_is_not_an_average():
    cfg = CostConfig("gpt-6.1-sol", "max")
    cost = generations_cost(cfg, [{"codex_usage": USAGE}, {"codex_usage": USAGE}])
    assert cost["total_usd"] == pytest.approx(3.82)
    assert cost["over_budget_at_assumed_rates"]
    small = generations_cost(cfg, [{"codex_usage": {k: 0 for k in USAGE}}])
    summary = summarize_costs(
        [{"name": "hard", "cost": cost}, {"name": "easy", "cost": small}]
    )
    assert summary["mean_observed_usd"] == pytest.approx(1.91)
    assert summary["over_budget_problems"] == ["hard"]
    assert summary["all_observed_within_cap_at_assumed_rates"] is False
    assert generations_cost(cfg, [])["total_usd"] is None
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_costs([{"name": "x", "cost": cost}, {"name": "x", "cost": cost}])


def test_claude_cache_duration_prices_mixed_writes_and_all_attempts():
    cfg = CostConfig("claude-opus-5-5", "max")
    usage = {**USAGE, "cache_write_1h_input_tokens": 40000}
    cost = estimate_codex_cost(cfg, usage)
    assert cost["breakdown_usd"]["cache_write_usd"] == pytest.approx(0.62)
    assert cost["total_usd"] == pytest.approx(3.94)
    generations = [{"token_usage": usage}, {"token_usage": usage}]
    total = generations_cost(cfg, generations)
    assert total["usage"]["cache_write_1h_input_tokens"] == 80000
    assert total["total_usd"] == pytest.approx(7.88)
    missing_ttl = generations_cost(cfg, generations + [{"token_usage": USAGE}])
    assert "cache_write_1h_input_tokens" not in missing_ttl["usage"]


@pytest.mark.parametrize("value", [True, -1, 100001, None])
def test_one_hour_cache_count_must_be_a_valid_subset(value):
    with pytest.raises(ValueError, match="One-hour"):
        estimate_codex_cost(
            CostConfig("claude-opus-5-5", "max"),
            {**USAGE, "cache_write_1h_input_tokens": value},
        )


def test_repricing_has_explicit_source_and_target_without_mutating_evidence():
    traces = [
        {
            "name": "x",
            "model": "gpt-6-astra",
            "effort": "max",
            "generations": [{"codex_usage": USAGE}],
        }
    ]
    saved = deepcopy(traces)
    scenario = estimate_configuration(CostConfig("gpt-6.1-sol", "max"), traces)
    assert scenario["kind"] == "saved_usage_repricing_scenario"
    assert scenario["summary"]["mean_observed_usd"] == pytest.approx(1.91)
    assert scenario["source_configuration"]["model"] == "gpt-6-astra"
    assert scenario["configuration"]["model"] == "gpt-6.1-sol"
    assert traces == saved
    with pytest.raises(ValueError, match="one source"):
        estimate_configuration(
            CostConfig("gpt-6.1-sol", "max"), traces + [{**traces[0], "effort": "low"}]
        )
    with pytest.raises(ValueError, match="exact model"):
        CostConfig("gpt-6-sol", "max")


def test_default_harness_and_preflight_do_not_measure_or_generate(monkeypatch):
    import proof_eval.harness.configuration as configuration
    import proof_eval.harness.runner as runner

    assert configuration.DEFAULT_MODE == "score_edges"
    assert "score_each" not in configuration.RUN_MODES
    assert configuration.CONDITIONS["model_config"] == [
        ("gpt-6.1-sol", "max"),
        ("gpt-6-astra", "max"),
    ]

    def forbidden(*args, **kwargs):
        raise AssertionError("Cost estimation must not call Lean or a model")

    monkeypatch.setattr(runner, "Evaluator", forbidden)
    from proof_eval.harness import agent

    monkeypatch.setattr(agent, "generate", forbidden)
    scenarios = configuration.preflight_costs(configuration.CONDITIONS["model_config"])
    assert len(scenarios["scenarios"]) == 6
    assert all(
        s["summary"]["known_cost_problems"] == 15 for s in scenarios["scenarios"]
    )
    for model, effort in configuration.CONDITIONS["model_config"]:
        assert configuration.historical("x", model, effort) == (None, None)
        assert configuration.score_control("x", model, effort) == (None, None)
