"""Observable routing, terminal, pricing and resume contracts for native agents."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from proof_eval.harness import agent, cli
from proof_eval.harness.config import RunConfig
from proof_eval.providers import agy, claude, codex, execution, lemex
from proof_eval.providers.costs import (
    CostConfig,
    estimate_token_cost,
    generations_cost,
    rate_card,
)


def claude_events(**changes):
    terminal = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": "theorem x : True := by trivial",
        "session_id": "session-test",
        "permission_denials": [],
        "total_cost_usd": 0.00144,
        "usage": {
            "input_tokens": 80,
            "cache_read_input_tokens": 100,
            "cache_creation_input_tokens": 20,
            "output_tokens": 50,
        },
        "modelUsage": {claude.MODEL: {"costUSD": 0.00144}},
        **changes,
    }
    return [
        {
            "type": "system",
            "subtype": "init",
            "model": claude.MODEL,
            "session_id": "session-test",
        },
        terminal,
    ]


def agy_events(**changes):
    result = {
        "conversation_id": "conv-test",
        "status": "SUCCESS",
        "response": "theorem x : True := by trivial",
        "denied_actions": [],
        "usage": {
            "input_tokens": 80,
            "output_tokens": 50,
            "thinking_tokens": 10,
            "cache_read_tokens": 20,
            "total_tokens": 150,
        },
        **changes,
    }
    return [
        {
            "event": "init",
            "conversation_id": "conv-test",
            "init": {
                "model": "gemini-3.8-flash-high",
                "cwd": "/workspace",
                "agent": "code",
                "tools": [],
                "permission_mode": "bypassPermissions",
            },
        },
        {"event": "result", "result": result},
    ]


def test_claude_normalizes_cache_counts_and_keeps_reported_cost():
    parsed = claude.parse_events(claude_events(), "", 0)
    assert parsed["status"] == "received"
    assert parsed["session_id"] == "session-test"
    assert parsed["token_usage"] == dict(
        input_tokens=200,
        cached_input_tokens=100,
        cache_write_input_tokens=20,
        output_tokens=50,
        reasoning_output_tokens=0,
    )
    parsed["provider"] = "claude"
    cost = generations_cost(CostConfig(claude.MODEL, "max"), [parsed])
    assert cost["total_usd"] == pytest.approx(0.00144)
    assert cost["basis"] == "claude_code_api_equivalent_estimate"
    independent = cost["aggregate_usage_at_opus_list_rates"]
    assert independent["total_usd"] == pytest.approx(0.00144)
    assert independent["all_requests_long_context_usd"] == independent["total_usd"]


@pytest.mark.parametrize(
    "changes",
    [
        {"is_error": True},
        {"subtype": "error_max_turns"},
        {"result": ""},
        {"session_id": None},
        {"session_id": ""},
        {"session_id": "another-session"},
    ],
)
def test_claude_terminal_errors_and_limits_are_incomplete(changes):
    parsed = claude.parse_events(claude_events(**changes), "", 0)
    assert parsed["status"] != "received"
    parsed["provider"] = "claude"
    assert generations_cost(CostConfig(claude.MODEL, "max"), [parsed])[
        "total_usd"
    ] == pytest.approx(0.00144)


def test_recoverable_tool_denials_preserve_success_usage_and_cost():
    denials = [{"tool_name": "Bash", "tool_input": {"command": "unapproved helper"}}]
    parsed = claude.parse_events(claude_events(permission_denials=denials), "", 0)
    parsed["provider"] = "claude"
    assert parsed["status"] == "received" and parsed["permission_denials"] == denials
    assert parsed["tool_outcome"] == "completed_with_denials"
    assert generations_cost(CostConfig(claude.MODEL, "max"), [parsed])[
        "total_usd"
    ] == pytest.approx(0.00144)


def test_claude_prices_reported_cache_duration_and_counts_thinking_once():
    events = claude_events()
    terminal = events[-1]
    terminal["usage"]["cache_creation"] = {
        "ephemeral_1h_input_tokens": 20,
        "ephemeral_5m_input_tokens": 0,
    }
    terminal["modelUsage"][claude.MODEL].update(outputTokens=50, thinkingTokens=35)
    terminal["total_cost_usd"] = 0.00150
    parsed = claude.parse_events(events, "", 0)
    assert parsed["usage_schema_version"] == 2
    assert parsed["cache_write_ttl_reported"] and parsed["reasoning_usage_reported"]
    assert parsed["token_usage"]["reasoning_output_tokens"] == 35
    assert parsed["token_usage"]["cache_write_1h_input_tokens"] == 20
    parsed["provider"] = "claude"
    cost = generations_cost(CostConfig(claude.MODEL, "max"), [parsed])
    assert cost["total_usd"] == pytest.approx(0.00150)
    assert cost["aggregate_usage_at_opus_list_rates"]["total_usd"] == pytest.approx(
        0.00150
    )
    legacy = claude.parse_events(events, "", 0, usage_schema_version=1)
    assert "usage_schema_version" not in legacy
    assert "cache_write_1h_input_tokens" not in legacy["token_usage"]
    assert legacy["token_usage"]["reasoning_output_tokens"] == 0
    assert not legacy["reasoning_usage_reported"]


@pytest.mark.parametrize("thinking", [True, -1, 51, None])
def test_invalid_or_missing_thinking_counter_remains_unreported(thinking):
    events = claude_events()
    events[-1]["modelUsage"][claude.MODEL].update(
        outputTokens=50, thinkingTokens=thinking
    )
    parsed = claude.parse_events(events, "", 0)
    assert not parsed["reasoning_usage_reported"]
    assert parsed["token_usage"]["reasoning_output_tokens"] == 0


def test_incomplete_auxiliary_model_usage_does_not_certify_reasoning():
    events = claude_events()
    events[-1]["modelUsage"][claude.MODEL].update(outputTokens=40, thinkingTokens=35)
    events[-1]["modelUsage"]["auxiliary"] = {"outputTokens": 10}
    parsed = claude.parse_events(events, "", 0)
    assert not parsed["reasoning_usage_reported"]


def test_inconsistent_cache_breakdown_is_preserved_but_not_used_for_pricing():
    events = claude_events()
    events[-1]["usage"]["cache_creation"] = {
        "ephemeral_1h_input_tokens": 30,
        "ephemeral_5m_input_tokens": 0,
    }
    parsed = claude.parse_events(events, "", 0)
    assert not parsed["cache_write_ttl_reported"]
    assert "cache_write_1h_input_tokens" not in parsed["token_usage"]
    assert parsed["claude_usage"] == events[-1]["usage"]


@pytest.mark.parametrize("version", [True, 0, 3, "2"])
def test_unsupported_usage_versions_are_rejected(version):
    with pytest.raises(ValueError, match="usage schema"):
        claude.parse_events(claude_events(), "", 0, usage_schema_version=version)


def test_saved_failed_claude_usage_is_audited_without_model_or_lean_calls(tmp_path):
    from proof_eval.harness.audit import _audit_claude_terminal

    events = claude_events(is_error=True, subtype="error_max_turns")
    parsed = claude.parse_events(events, "", 1)
    (tmp_path / "events.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events)
    )
    _audit_claude_terminal(tmp_path, parsed, {"model": claude.MODEL})
    parsed["cli_cost_usd"] = 0
    with pytest.raises(ValueError, match="cli_cost_usd"):
        _audit_claude_terminal(tmp_path, parsed, {"model": claude.MODEL})


def test_claude_requires_the_requested_model_and_exact_terminal_output():
    events = claude_events()
    events[0]["model"] = "claude-sonnet-5"
    assert claude.parse_events(events, "", 0)["status"] == "model_mismatch"
    with pytest.raises(ValueError, match="Saved final differs"):
        claude.parse_events(claude_events(), "another proof", 0)
    assert claude.parse_events(claude_events(), "", 1)["status"] == "transport_error"


def test_missing_claude_usage_or_cost_is_not_priced_as_zero():
    parsed = claude.parse_events(claude_events(usage={}), "", 0)
    parsed["provider"] = "claude"
    assert (
        generations_cost(CostConfig(claude.MODEL, "max"), [parsed])["total_usd"] is None
    )
    parsed = claude.parse_events(claude_events(total_cost_usd=None), "", 0)
    parsed["provider"] = "claude"
    assert (
        generations_cost(CostConfig(claude.MODEL, "max"), [parsed])["status"]
        == "unknown_cost"
    )


def test_exact_deepseek_gateway_price_remains_unknown_even_with_usage():
    usage = claude.parse_events(claude_events(), "", 0)["token_usage"]
    cost = estimate_token_cost(CostConfig(lemex.MODEL, "high"), usage)
    assert cost["status"] == "unknown_price" and cost["total_usd"] is None
    assert cost["usage"] == usage
    assert rate_card("lemex")["rates"] == {}


def test_claude_command_has_exact_model_effort_tools_and_no_bypass(tmp_path):
    argv = claude.command(
        binary="claude",
        workspace=tmp_path,
        system_file=tmp_path / "system",
        tool_file=tmp_path / "tools",
        model=claude.MODEL,
        effort="max",
        source_projects=["/pinned/source"],
    )
    assert argv[argv.index("--model") + 1] == claude.MODEL
    assert argv[argv.index("--effort") + 1] == "max"
    assert argv[argv.index("--permission-mode") + 1] == "dontAsk"
    assert "--strict-mcp-config" in argv and "--permission-prompts" in argv
    assert "Bash(python " + str(tmp_path / "tools.py") + " *)" in argv
    assert all(
        flag not in argv
        for flag in (
            "--bare",
            "--continue",
            "--dangerously-skip-permissions",
            "--fallback-model",
            "--max-budget-usd",
        )
    )
    with pytest.raises(ValueError, match="Claude condition"):
        claude.command(
            binary="claude",
            workspace=tmp_path,
            system_file=tmp_path / "system",
            tool_file=tmp_path / "tools",
            model=claude.MODEL,
            effort="high",
            source_projects=[],
        )


@pytest.mark.parametrize(
    "provider,module,model,effort",
    [
        ("codex", codex, "gpt-6.1-sol", "max"),
        ("lemex", lemex, lemex.MODEL, "high"),
        ("claude", claude, claude.MODEL, "max"),
        ("agy", agy, agy.MODEL, "high"),
    ],
)
def test_started_requests_are_not_resampled_for_any_provider(
    tmp_path, monkeypatch, provider, module, model, effort
):
    identity = {"path": "/unused/agent", "version": "test", "sha256": "test"}
    monkeypatch.setattr(module, "cli_identity", lambda: identity)

    def forbidden(*args, **kwargs):
        raise AssertionError("Started requests must not launch a new session")

    monkeypatch.setattr(execution.subprocess, "Popen", forbidden)
    (tmp_path / "request_started.json").write_text("{}")
    args = dict(
        folder=tmp_path,
        messages=[
            {"role": "system", "content": "task policy"},
            {"role": "user", "content": "proof"},
        ],
        model=model,
        effort=effort,
        mode="score_edges",
        session=SimpleNamespace(seed_code="seed"),
        context={},
        expected_cli=identity,
        instructions="tools",
        tool_service=forbidden,
    )
    result = module.generate(**args)
    assert result["status"] == "indeterminate" and module.generate(**args) == result
    assert json.loads((tmp_path / "request.json").read_text())["provider"] == provider


@pytest.mark.parametrize("provider", ["codex", "lemex", "claude", "agy"])
def test_provider_routing_and_cli_defaults(provider, monkeypatch, tmp_path):
    module = {"codex": codex, "lemex": lemex, "claude": claude, "agy": agy}[provider]
    monkeypatch.setattr(
        module,
        "generate",
        lambda **kw: {"provider": provider, "instructions": kw["instructions"]},
    )
    response = agent.generate(provider=provider, mode="score_edges")
    assert (
        response["provider"] == provider
        and "score feedback" in response["instructions"]
    )
    captured = []
    monkeypatch.setattr(
        cli,
        "run_pipeline",
        lambda cfg: captured.append(cfg.model) or {"status": "prepared"},
    )
    assert cli.main(["prepare", "--provider", provider, "--output", str(tmp_path)]) == 0
    assert captured[0].provider == provider
    assert captured[0].conditions == RunConfig(provider=provider).conditions


def test_gateway_credential_bridge_is_child_only_and_literal(tmp_path, monkeypatch):
    for key in ("LEMEX_API_KEY", "LEMEX_BASE_URL", "RCP_API_KEY", "RCP_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "export RCP_API_KEY='fake-for-test'\nexport RCP_BASE_URL='https://example.invalid/v1'\n"
    )
    child = lemex.environment(env_file)
    assert (
        child["LEMEX_API_KEY"] == "fake-for-test"
        and child["LEMEX_BASE_URL"] == "https://example.invalid/v1"
    )
    assert not any(k.startswith("RCP_") for k in child)
    import os

    assert "LEMEX_API_KEY" not in os.environ


def test_lemex_capacity_is_shared_across_concurrent_batches(tmp_path, monkeypatch):
    monkeypatch.setattr(lemex, "SLOT_DIRECTORY", tmp_path / "slots")
    release = threading.Event()
    full = threading.Event()
    counts = [0, 0]
    mutex = threading.Lock()

    def task():
        with lemex.capacity():
            with mutex:
                counts[0] += 1
                counts[1] = max(counts)
                if counts[0] == 5:
                    full.set()
            assert release.wait(5)
            with mutex:
                counts[0] -= 1

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(task) for _ in range(6)]
        assert full.wait(5)
        release.set()
        for future in futures:
            future.result()
    assert counts[1] == 5


def test_native_child_keeps_gateway_slot_after_host_releases_it(tmp_path, monkeypatch):
    monkeypatch.setattr(lemex, "SLOT_DIRECTORY", tmp_path / "slots")
    monkeypatch.setattr(lemex, "SLOT_COUNT", 1)
    with lemex.capacity() as fd:
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(10)"], pass_fds=(fd,)
        )
    entered = threading.Event()

    def acquire():
        with lemex.capacity():
            entered.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(acquire)
        try:
            assert not entered.wait(
                0.3
            ), "A live orphaned CLI must retain its admission slot"
        finally:
            child.terminate()
            child.wait(timeout=5)
        future.result(timeout=5)
    assert entered.is_set()


def test_agy_normalizes_cache_reads_into_input_and_keeps_thinking_subset():
    parsed = agy.parse_events(agy_events(), "", 0)
    assert parsed["status"] == "received"
    usage = parsed["token_usage"]
    assert usage["input_tokens"] == 100
    assert usage["cached_input_tokens"] == 20
    assert usage["cache_write_input_tokens"] == 0
    assert usage["output_tokens"] == 50
    assert usage["reasoning_output_tokens"] == 10
    assert parsed["cache_write_reported"] is False


def test_agy_uses_standard_gemini_api_rates_as_an_explicit_proxy():
    parsed = agy.parse_events(agy_events(), "", 0)
    cost = estimate_token_cost(CostConfig(agy.MODEL, "high"), parsed["token_usage"])
    assert cost["status"] == "estimated"
    assert cost["total_usd"] == pytest.approx(
        (80 * 0.75 + 20 * 0.075 + 50 * 3.75) / 1e6
    )
    assert cost["usage"] == parsed["token_usage"]
    assert rate_card("agy")["rates"][agy.MODEL]["output"] == 3.75
    assert rate_card("agy")["gateway_price_verified"] is False
    parsed["provider"] = "agy"
    assert (
        generations_cost(CostConfig(agy.MODEL, "high"), [parsed])["total_usd"]
        == cost["total_usd"]
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "ERROR"},
        {"status": "FAILED"},
        {"conversation_id": ""},
        {"response": "   "},
    ],
)
def test_agy_terminal_errors_and_limits_are_incomplete(changes):
    assert agy.parse_events(agy_events(**changes), "", 0)["status"] == "transport_error"
    assert agy.parse_events(agy_events(**changes), "", 1)["status"] == "transport_error"


def test_agy_missing_usage_is_not_priced_as_zero():
    parsed = agy.parse_events(agy_events(usage={}), "", 0)
    assert parsed["status"] == "received" and parsed["token_usage"] is None
    parsed["provider"] = "agy"
    assert (
        generations_cost(CostConfig(agy.MODEL, "high"), [parsed])["total_usd"] is None
    )


def test_agy_failed_terminal_preserves_reported_usage():
    parsed = agy.parse_events(agy_events(status="ERROR"), "", 1)
    assert parsed["status"] == "transport_error"
    assert parsed["token_usage"]["input_tokens"] == 100
    assert parsed["agy_usage"]["output_tokens"] == 50


def test_agy_denials_are_preserved_on_a_successful_terminal():
    parsed = agy.parse_events(agy_events(denied_actions=["run_command"]), "", 0)
    assert parsed["status"] == "received"
    assert parsed["denied_actions"] == ["run_command"]
    assert parsed["tool_outcome"] == "completed_with_denials"


def test_agy_rejects_contradictory_selection_but_not_missing_evidence():
    slug = agy.slug(agy.MODEL, "high")
    assert (
        agy.parse_events(agy_events(), "", 0, requested_slug=slug)["status"]
        == "received"
    )
    assert (
        agy.parse_events(agy_events(), "", 0, requested_slug="gemini-3.1-pro-high")[
            "status"
        ]
        == "model_mismatch"
    )
    events = agy_events()
    events[0]["init"].pop("model")
    parsed = agy.parse_events(events, "", 0, requested_slug=slug)
    assert parsed["status"] == "received" and parsed["actual_model"] is None


def test_agy_requires_exact_terminal_output_and_one_result():
    with pytest.raises(ValueError, match="Saved final differs"):
        agy.parse_events(agy_events(), "another proof", 0)
    doubled = agy_events() + [agy_events()[-1]]
    assert agy.parse_events(doubled, "", 0)["status"] == "transport_error"


def test_agy_slug_and_command_are_suffixed_and_inline(tmp_path):
    assert agy.slug(agy.MODEL, "high") == "gemini-3.8-flash-high"
    for effort in ("xhigh", "max"):
        with pytest.raises(ValueError):
            agy.slug(agy.MODEL, effort)
    argv = agy.command(
        binary="agy",
        workspace=tmp_path,
        prompt="MERGED POLICY AND TASK",
        model=agy.MODEL,
        effort="high",
        source_projects=["/pinned/source"],
    )
    assert argv[-1] == "-p=MERGED POLICY AND TASK"
    assert argv[argv.index("--model") + 1] == "gemini-3.8-flash-high"
    assert argv[argv.index("--output-format") + 1] == "stream-json"
    assert argv[argv.index("--agent") + 1] == "code"
    assert "--effort" not in argv
    assert "--dangerously-skip-permissions" in argv
    assert str(tmp_path) in argv
    assert "--add-dir" in argv
    with pytest.raises(ValueError, match="command-line limit"):
        agy.command(
            binary="agy",
            workspace=tmp_path,
            prompt="x" * (agy.MAX_PROMPT_BYTES + 1),
            model=agy.MODEL,
            effort="high",
            source_projects=[],
        )


def test_saved_successful_agy_terminal_reconstructs_evidence(tmp_path):
    from proof_eval.harness.audit import _audit_agy_terminal

    folder = tmp_path / "attempt_00"
    folder.mkdir()
    events = agy_events()
    request = {"model": agy.MODEL, "reasoning_effort": "high"}
    parsed = agy.parse_events(events, "", 0, requested_slug=agy.slug(agy.MODEL, "high"))
    (folder / "events.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events)
    )
    _audit_agy_terminal(folder, parsed, request)
    parsed["token_usage"]["input_tokens"] += 1
    with pytest.raises(ValueError, match="token_usage"):
        _audit_agy_terminal(folder, parsed, request)


def test_saved_failed_agy_usage_is_audited_without_model_or_lean_calls(tmp_path):
    from proof_eval.harness.audit import _audit_agy_terminal

    folder = tmp_path / "attempt_00"
    folder.mkdir()
    events = agy_events(status="ERROR")
    request = {"model": agy.MODEL, "reasoning_effort": "high"}
    parsed = agy.parse_events(events, "", 1)
    (folder / "events.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events)
    )
    _audit_agy_terminal(folder, parsed, request)
    parsed["denied_actions"] = ["run_command"]
    with pytest.raises(ValueError, match="denied_actions"):
        _audit_agy_terminal(folder, parsed, request)


def test_saved_deadline_agy_terminal_requires_supervised_stop(tmp_path):
    from proof_eval.harness.audit import _audit_agy_terminal

    folder = tmp_path / "attempt_00"
    folder.mkdir()
    (folder / "events.jsonl").write_text("")
    request = {"model": agy.MODEL, "reasoning_effort": "high"}
    generation = agy.parse_events([], "", 0)
    generation.update(status="budget_exhausted", termination="problem_deadline")
    (tmp_path / "budget_end.json").write_text(json.dumps({"exhausted": True}))
    _audit_agy_terminal(folder, generation, request)
    (tmp_path / "budget_end.json").write_text(json.dumps({"exhausted": False}))
    with pytest.raises(ValueError, match="supervised stop"):
        _audit_agy_terminal(folder, generation, request)


def test_only_one_prompt_policy_and_production_mode_remain():
    from proof_eval.paths import ROOT

    assert {p.name for p in (ROOT / "prompts").iterdir()} == {
        "refactor_system.md",
        "strategy_bank.json",
    }
    for mode in ("correctness", "score", "score_each"):
        with pytest.raises(ValueError):
            RunConfig(mode=mode)
    with pytest.raises(ValueError):
        RunConfig(provider="lemex", workers=0)


def test_unknown_price_still_validates_scope_and_budget():
    usage = claude.parse_events(claude_events(), "", 0)["token_usage"]
    for fields in ({"scope": "bad"}, {"budget_usd": -1}):
        with pytest.raises(ValueError):
            estimate_token_cost(CostConfig(lemex.MODEL, "high"), usage, **fields)
    for fields in ({"service_tier": "flex"}, {"regional_processing": True}):
        with pytest.raises(ValueError):
            CostConfig(claude.MODEL, "max", **fields)
