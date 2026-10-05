"""Observable routing, terminal, pricing and resume contracts for native agents."""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from proof_eval.harness import agent, cli
from proof_eval.harness.config import RunConfig
from proof_eval.providers import claude, codex, execution, lemex
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
    return [{"type": "system", "subtype": "init", "model": claude.MODEL}, terminal]


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
        {"permission_denials": [{"tool_name": "Bash"}]},
    ],
)
def test_claude_errors_limits_and_denied_tools_are_incomplete(changes):
    assert claude.parse_events(claude_events(**changes), "", 0)["status"] != "received"


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


@pytest.mark.parametrize("provider", ["codex", "lemex", "claude"])
def test_provider_routing_and_cli_defaults(provider, monkeypatch, tmp_path):
    module = {"codex": codex, "lemex": lemex, "claude": claude}[provider]
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
        cli, "run", lambda cfg: captured.append(cfg) or {"status": "partial"}
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
    monkeypatch.setattr(lemex, "ROOT", tmp_path)
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
        RunConfig(provider="lemex", workers=6)


def test_unknown_price_still_validates_scope_and_budget():
    usage = claude.parse_events(claude_events(), "", 0)["token_usage"]
    for fields in ({"scope": "bad"}, {"budget_usd": -1}):
        with pytest.raises(ValueError):
            estimate_token_cost(CostConfig(lemex.MODEL, "high"), usage, **fields)
    for fields in ({"service_tier": "flex"}, {"regional_processing": True}):
        with pytest.raises(ValueError):
            CostConfig(claude.MODEL, "max", **fields)
