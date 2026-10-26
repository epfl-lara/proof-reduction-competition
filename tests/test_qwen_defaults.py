"""The approved local-Qwen regime is a public default, not a run wrapper."""

import pytest

from proof_eval import Evaluator
from proof_eval.harness import cli
from proof_eval.harness.config import RunConfig
from proof_eval.harness.pipeline import PipelineConfig
from proof_eval.harness.prompts import budget_suffix, tool_instructions
from proof_eval.paths import ROOT
from proof_eval.providers import lemex_local, local_profile
from proof_eval.providers.vllm_server import ServerConfig


@pytest.mark.parametrize("model", [lemex_local.MODEL, lemex_local.THINKINGCAP_MODEL])
def test_local_qwen_defaults_use_the_full_model_only_regime(model):
    model_run = RunConfig(provider="lemex-local", conditions=((model, "xhigh"),))
    workflow = PipelineConfig(model_run)
    assert model_run.problem_timeout_seconds == 28800 and model_run.workers == 10
    assert model_run.verification_timeout_seconds == 600
    assert model_run.original_measurement_policy == "prepared"
    assert model_run.max_budget_restarts == 10000
    assert not model_run.restart_history and not model_run.deterministic
    assert not workflow.cleanup_before and not workflow.cleanup_after


def test_gateway_qwen_keeps_its_shared_provider_capacity_and_gets_eight_hours():
    run = RunConfig(
        provider="lemex", conditions=(("Qwen/Qwen3.8-Flash-Next", "xhigh"),)
    )
    assert run.workers == 5 and run.problem_timeout_seconds == 28800
    assert not PipelineConfig(run).cleanup_before


def test_other_models_keep_their_cost_workers_restart_and_cleanup_policies():
    run = RunConfig()
    pipeline = PipelineConfig(run)
    assert run.budget_tracking == "cost" and run.problem_timeout_seconds is None
    assert run.workers == 5 and run.max_budget_restarts == 20
    assert pipeline.cleanup_before and pipeline.cleanup_after


def test_explicit_shorter_budgets_and_cleanup_are_preserved():
    run = RunConfig(
        provider="lemex-local",
        problem_timeout_seconds=120,
        verification_timeout_seconds=15,
        workers=2,
        max_budget_restarts=3,
    )
    pipeline = PipelineConfig(run, cleanup_before=True, cleanup_after=True)
    assert run.problem_timeout_seconds == 120 and run.verification_timeout_seconds == 15
    assert run.workers == 2 and run.max_budget_restarts == 3
    assert pipeline.cleanup_before and pipeline.cleanup_after


def test_public_evaluator_and_server_share_the_approved_defaults(tmp_path):
    evaluator = Evaluator(
        ROOT / "data/benchmark_data_warmup.jsonl", None, tmp_path / "cache"
    )
    assert evaluator.timeout == evaluator.backend.timeout == 600
    assert evaluator.version_workers == 4
    server = ServerConfig()
    assert server.mode == "mtp3" and server.max_model_len == 266400
    assert server.max_num_seqs == 10 and server.gpu_memory_utilization == 0.95
    assert server.profile == "rcp-api-flags" and server.execution_mode == "compiled"


def test_default_profile_records_the_host_verifier_deadline(tmp_path):
    local_profile.prepare(tmp_path / "profile")
    profile, _ = local_profile.load(tmp_path / "profile")
    assert profile["verification_timeout_seconds"] == 600


def test_prepared_model_prompts_report_cpu_preparation_outside_the_model_clock():
    instructions = tool_instructions(
        "score_edges",
        budget_tracking="time",
        initial_only=True,
        deterministic_enabled=False,
        prepared_original=True,
    )
    assert "without recompilation" in instructions
    assert "Original CPU preparation is outside this clock" in instructions
    assert "freshly measured" not in instructions
    suffix = budget_suffix(
        {"initial_pipeline_version": 1, "original_measurement_policy": "prepared"},
        {"timeout_seconds": 28800},
        {},
        28799,
        0,
    )
    assert "original CPU preparation is outside this clock" in suffix
    assert "including original measurement" not in suffix


@pytest.mark.parametrize("value", [0, -1, True, float("nan"), float("inf")])
def test_invalid_verifier_limits_fail_before_a_run(value):
    with pytest.raises(ValueError, match="verification_timeout_seconds"):
        RunConfig(verification_timeout_seconds=value)


@pytest.mark.parametrize("extra,cleanup", [([], False), (["--deterministic"], True)])
def test_standard_cli_resolves_qwen_defaults_without_a_wrapper(
    monkeypatch, capsys, extra, cleanup
):
    seen = []

    def capture(config):
        seen.append(config)
        return {"status": "complete"}

    monkeypatch.setattr(cli, "run_pipeline", capture)
    assert cli.main(["prepare", "--provider", "lemex-local", *extra]) == 0
    config = seen[0]
    assert config.model.problem_timeout_seconds == 28800
    assert (
        config.model.workers == 10 and config.model.verification_timeout_seconds == 600
    )
    assert config.cleanup_before is cleanup and config.cleanup_after is cleanup
    capsys.readouterr()
