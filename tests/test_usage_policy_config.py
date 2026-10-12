"""New runs pin best-effort usage; historical and strict policies stay explicit."""

from __future__ import annotations

import pytest

from proof_eval.harness import cli
from proof_eval.harness.config import RunConfig
from proof_eval.harness.usage_policy import resolve_usage_policy


def test_new_codex_cost_runs_default_to_best_effort_without_a_deadline():
    config = RunConfig(
        conditions=(("gpt-6.1-sol", "max"),),
    )
    assert config.usage_policy == "best_effort"
    assert config.budget_tracking == "cost"
    assert config.problem_timeout_seconds is None
    assert config.workers == 5
    assert config.budget_usd_per_problem == 3.0


@pytest.mark.parametrize("provider", ["lemex", "claude", "agy"])
def test_other_provider_defaults_retain_strict_accounting(provider):
    assert RunConfig(provider=provider).usage_policy == "strict"


def test_cli_can_select_strict_accounting(monkeypatch):
    captured = []
    monkeypatch.setattr(cli, "run", lambda config: captured.append(config) or {})
    assert cli.main(["run", "--usage-policy", "strict"]) == 0
    assert captured[0].usage_policy == "strict"
    assert cli.main(["run"]) == 0
    assert captured[1].usage_policy == "best_effort"


@pytest.mark.parametrize(
    "settings",
    [
        {"usage_policy": "invalid"},
        {"provider": "claude", "usage_policy": "best_effort"},
        {"budget_tracking": "time", "usage_policy": "best_effort"},
    ],
)
def test_unsupported_best_effort_configuration_fails_before_dispatch(settings):
    with pytest.raises(ValueError, match="usage|Best-effort"):
        RunConfig(**settings)


def test_time_tracking_default_remains_strict():
    config = RunConfig(budget_tracking="time")
    assert config.usage_policy == "strict"
    assert config.problem_timeout_seconds == 3420
    assert resolve_usage_policy(None, "codex", "cost") == "best_effort"
