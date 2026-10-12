"""Budget admission from explicit terminal usage estimates; no paid calls."""

from __future__ import annotations

import pytest
import test_budget_tracking as budget_tests

from proof_eval.evidence.io import read, write_json
from proof_eval.harness import search
from proof_eval.harness.tracking import attempt_cost, stop_decision
from proof_eval.providers.costs import CostConfig, estimate_token_cost, generations_cost

tracking_run = budget_tests.tracking_run

MODEL, EFFORT = "gpt-6.1-sol", "max"
REPORTED = dict(
    input_tokens=100000,
    cached_input_tokens=90000,
    cache_write_input_tokens=0,
    output_tokens=10000,
    reasoning_output_tokens=5000,
)
MISSING = dict(
    input_tokens=1000,
    cached_input_tokens=0,
    cache_write_input_tokens=0,
    output_tokens=400,
    reasoning_output_tokens=0,
)


def config(**fields):
    return {
        "provider": "codex",
        "usage_policy": "best_effort",
        "budget_tracking": "cost",
        "budget_usd_per_problem": 3.0,
        "max_budget_restarts": 20,
        "max_transport_restarts": 2,
        **fields,
    }


def incomplete_generation(**fields):
    return {
        "status": "received",
        "provider": "codex",
        "token_usage": REPORTED.copy(),
        "usage_complete": False,
        "response_usage_schema_version": 2,
        "response_usage_sha256": "a" * 64,
        "structurally_valid": True,
        "estimated_usage_complete": True,
        "estimated_token_usage": {
            field: REPORTED[field] + MISSING[field] for field in REPORTED
        },
        "usage_estimates": [
            {
                "call_id": "native-compaction",
                "kind": "compaction",
                "basis": "request_and_response_json_characters_divided_by_four",
                "token_usage": MISSING.copy(),
            }
        ],
        **fields,
    }


def price(usage, model=MODEL):
    return estimate_token_cost(CostConfig(model, EFFORT), usage)["total_usd"]


def decision(settings, generation, cost, **fields):
    return stop_decision(
        settings,
        generation,
        cost,
        **{
            "unavailable": False,
            "round_number": 0,
            "time_remaining": None,
            **fields,
        },
    )


@pytest.mark.parametrize("policy", [None, "strict"])
def test_historical_or_strict_policy_preserves_unknown_usage(policy):
    settings = config()
    if policy is None:
        settings.pop("usage_policy")
    else:
        settings["usage_policy"] = policy
    generation = incomplete_generation()
    expected = generations_cost(CostConfig(MODEL, EFFORT), [generation])
    actual = attempt_cost(settings, MODEL, EFFORT, [generation])
    assert actual == expected
    assert decision(settings, generation, actual)["kind"] == "unknown_usage"


def test_complete_reported_cost_remains_identical():
    generation = {"status": "received", "token_usage": REPORTED}
    expected = generations_cost(CostConfig(MODEL, EFFORT), [generation])
    assert attempt_cost(config(), MODEL, EFFORT, [generation]) == expected


def test_best_effort_preserves_reported_lower_bound_and_prices_missing_usage():
    generation = incomplete_generation()
    actual = attempt_cost(config(), MODEL, EFFORT, [generation])
    assert actual["status"] == "estimated_incomplete_usage"
    assert actual["complete_usage"] is False
    assert actual["reported_usage"] == REPORTED
    assert actual["usage"] == generation["estimated_token_usage"]
    assert actual["reported_total_usd"] == pytest.approx(price(REPORTED))
    assert actual["total_usd"] == pytest.approx(price(REPORTED) + price(MISSING))
    assert actual["estimated_unreported_usd"] == pytest.approx(price(MISSING))
    assert actual["unknown_attempt_indices"] == [0]
    assert (
        actual["usage_estimates"][0]["usage_estimates"] == generation["usage_estimates"]
    )
    assert decision(config(), generation, actual) is None


def test_archived_partial_estimate_preserves_each_model_rate():
    settings = config(first_attempt_condition=["gpt-6-luna", EFFORT])
    generations = [
        {"status": "received", "token_usage": REPORTED},
        incomplete_generation(),
        {"status": "received", "token_usage": REPORTED},
    ]
    actual = attempt_cost(settings, MODEL, EFFORT, generations)
    reported = price(REPORTED, "gpt-6-luna") + 2 * price(REPORTED)
    assert actual["reported_total_usd"] == pytest.approx(reported)
    assert actual["total_usd"] == pytest.approx(reported + price(MISSING))
    assert actual["unknown_attempt_indices"] == [1]
    assert [item["model"] for item in actual["configurations"]] == [
        "gpt-6-luna",
        MODEL,
        MODEL,
    ]


@pytest.mark.parametrize(
    "fields",
    [
        {"response_usage_schema_version": 1},
        {"structurally_valid": False},
        {"estimated_usage_complete": False},
        {"status": "indeterminate"},
        {"status": "started"},
        {"response_usage_sha256": None},
        {"estimated_token_usage": {}},
        {"token_usage": None},
        {"usage_estimates": []},
    ],
)
def test_best_effort_never_admits_missing_or_unvalidated_native_evidence(fields):
    generation = incomplete_generation(**fields)
    actual = attempt_cost(config(), MODEL, EFFORT, [generation])
    assert actual["status"] == "unknown_usage" and actual["total_usd"] is None


def test_estimate_cannot_reclassify_reported_input_as_cached_or_drop_counters():
    for estimated in (
        {**REPORTED, "output_tokens": REPORTED["output_tokens"] - 1},
        {**REPORTED, "cached_input_tokens": REPORTED["cached_input_tokens"] + 1},
    ):
        actual = attempt_cost(
            config(),
            MODEL,
            EFFORT,
            [incomplete_generation(estimated_token_usage=estimated)],
        )
        assert actual["total_usd"] is None


def test_best_effort_does_not_replenish_budget_after_saved_roundtrip(tmp_path):
    settings = config(budget_usd_per_problem=0.2)
    generations = [incomplete_generation(), incomplete_generation()]
    before = attempt_cost(settings, MODEL, EFFORT, generations)
    write_json(
        tmp_path / "saved.json", {"config": settings, "generations": generations}
    )
    restored = read(tmp_path / "saved.json")
    after = attempt_cost(restored["config"], MODEL, EFFORT, restored["generations"])
    assert after == before
    assert after["total_usd"] > settings["budget_usd_per_problem"]
    assert decision(settings, generations[-1], after)["kind"] == "cost_limit"


def test_terminal_transient_failure_can_recover_under_estimated_shared_budget():
    generation = incomplete_generation(
        status="transport_error",
        events_errors=[
            {"type": "turn.failed", "error": {"message": "unexpected status 503"}}
        ],
    )
    cost = attempt_cost(config(), MODEL, EFFORT, [generation])
    assert decision(config(), generation, cost) is None
    assert (
        decision(config(), generation, cost, transport_restarts_used=2)["kind"]
        == "transport_recovery_limit"
    )
    interrupted = {**generation, "estimated_usage_complete": False}
    cost = attempt_cost(config(), MODEL, EFFORT, [interrupted])
    assert decision(config(), interrupted, cost)["kind"] == "unknown_usage"


def test_estimated_usage_does_not_override_permanent_failure():
    generation = incomplete_generation(
        status="transport_error",
        events_errors=[
            {"type": "turn.failed", "error": {"message": "unexpected status 401"}}
        ],
    )
    cost = attempt_cost(config(), MODEL, EFFORT, [generation])
    assert decision(config(), generation, cost)["kind"] == "infrastructure"


def test_native_guard_exhaustion_uses_remaining_shared_estimated_budget():
    generation = incomplete_generation(
        status="budget_exhausted", termination="cost_limit"
    )
    settings = config()
    cost = attempt_cost(settings, MODEL, EFFORT, [generation])
    assert decision(settings, generation, cost) is None
    assert (
        decision(settings, generation, cost, round_number=20)["kind"] == "restart_limit"
    )
    assert (
        decision(config(budget_usd_per_problem=0.1), generation, cost)["kind"]
        == "cost_limit"
    )
    strict = config(usage_policy="strict")
    assert decision(strict, generation, cost)["kind"] == "cost_limit"
    unknown = {**cost, "total_usd": None}
    assert decision(settings, generation, unknown)["kind"] == "cost_limit"
    for changed in (
        {"status": "transport_error"},
        {"response_usage_schema_version": 1},
        {"structurally_valid": False},
        {"estimated_usage_complete": False},
    ):
        assert (
            decision(settings, {**generation, **changed}, cost)["kind"] == "cost_limit"
        )
    exact = {**generation, "usage_complete": True, "estimated_usage_complete": False}
    assert decision(settings, exact, cost) is None


def test_no_generations_and_other_providers_keep_existing_accounting():
    assert attempt_cost(config(), MODEL, EFFORT, []) == {
        "status": "not_started",
        "total_usd": 0.0,
        "attempts": 0,
    }
    actual = attempt_cost(
        config(provider="claude"), MODEL, EFFORT, [incomplete_generation()]
    )
    assert actual["total_usd"] is None and actual["status"] == "unknown_usage"


def test_search_recovers_from_terminal_estimate_and_resume_reuses_result(
    tracking_run, monkeypatch
):
    monkeypatch.setattr(search, "RECOVERY_BACKOFF_SECONDS", 0)
    run = tracking_run(usd=0.2, timeout=None, cleanup=False)
    run.config["usage_policy"] = "best_effort"
    write_json(run.output / "config.json", run.config)
    failed = budget_tests.fake_native(
        run,
        events=[{"type": "turn.failed", "error": {"message": "unexpected status 503"}}],
    )
    success = budget_tests.fake_native(run, usage=REPORTED)
    calls = []

    def generator(**arguments):
        calls.append(arguments["folder"])
        result = (failed if len(calls) == 1 else success)(**arguments)
        if len(calls) == 1:
            result.update(
                {
                    key: value
                    for key, value in incomplete_generation().items()
                    if key not in ("status", "provider")
                }
            )
            write_json(arguments["folder"] / "generation.json", result)
        return result

    result = budget_tests.run_worker(run, generator)
    assert len(calls) == 2
    assert result["status"] == "complete" and result["stop"]["kind"] == "cost_limit"
    assert result["cost"]["status"] == "estimated_incomplete_usage"
    assert result["cost"]["total_usd"] == pytest.approx(
        2 * price(REPORTED) + price(MISSING)
    )
    first, second = result["attempts"]
    assert second["cost_before"] == first["cost_after"]
    assert second["incumbent_proof"] == run.saved["selected_proof"]

    def forbidden(**arguments):
        raise AssertionError("A completed result must not dispatch another request")

    assert budget_tests.run_worker(run, forbidden) == result
