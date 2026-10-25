"""Portable profile/CLI contracts: no GPU, model requests or Lean execution."""

import json
import os
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from proof_eval.interfaces import local
from proof_eval.providers import lemex_local, local_profile
from proof_eval.providers.costs import CostConfig, estimate_token_cost, rate_card
from proof_eval.providers.registry import adapter, validate
from proof_eval.providers.vllm_server import command


@pytest.mark.parametrize("model", [lemex_local.MODEL, lemex_local.THINKINGCAP_MODEL])
def test_prepare_and_preview_pin_the_model_and_complete_regime(tmp_path, capsys, model):
    profile = tmp_path / "profile"
    assert local.main(["prepare", "--profile", str(profile), "--model", model]) == 0
    value, server = local_profile.load(profile)
    assert server.model == model
    assert value["context"] == 266400 and value["compaction"] == 222400
    assert value["seconds"] == 28800 and value["workers"] == 10
    assert value["restart_history"] is False and value["deterministic_cleanup"] is False
    validate("lemex-local", [(model, "xhigh")])
    assert adapter("lemex-local") is lemex_local
    catalog = json.loads((profile / "models.json").read_text())
    assert catalog["models"][0]["slug"] == model
    assert server.revision == local_profile.REVISIONS[model]
    assert model in command(server)
    capsys.readouterr()
    assert local.main(["serve", "--profile", str(profile), "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["argv"] == command(server)
    assert not (tmp_path / "server_manifest.json").exists()


def test_frozen_settings_and_existing_profiles_are_never_rewritten(tmp_path):
    profile = tmp_path / "profile"
    local_profile.prepare(profile)
    before = (profile / "profile.json").read_bytes()
    with pytest.raises(FileExistsError):
        local_profile.prepare(profile)
    (profile / "config.toml").write_text("model_context_window = 32000\n")
    with pytest.raises(ValueError, match="Frozen local profile changed"):
        local_profile.load(profile)
    assert (profile / "profile.json").read_bytes() == before


@pytest.mark.parametrize(
    "settings",
    [
        {"workers": 0},
        {"workers": True},
        {"seconds": 0},
        {"compaction": 300000},
        {"revision": "main"},
    ],
)
def test_bad_profiles_fail_before_creating_any_output(tmp_path, settings):
    folder = tmp_path / "bad"
    with pytest.raises(ValueError):
        local_profile.prepare(folder, **settings)
    assert not folder.exists()


@pytest.mark.parametrize(
    "forwarded",
    [
        ["--provider", "codex"],
        ["--cond", "different:model"],
        ["--deterministic"],
        ["--budget-tracking=cost"],
        ["--track-cost"],
        ["--restart-hist"],
    ],
)
def test_run_cannot_retarget_a_frozen_profile_before_startup(
    tmp_path, monkeypatch, forwarded
):
    profile = tmp_path / "profile"
    local_profile.prepare(profile)
    monkeypatch.setattr(
        local, "ManagedServer", lambda *a: pytest.fail("no server allowed")
    )
    with pytest.raises(SystemExit):
        local.main(["run", "--profile", str(profile), "--workers", "4"])
    with pytest.raises(SystemExit):
        local.main(
            [
                "run",
                "--profile",
                str(profile),
                "--output",
                str(tmp_path / "run"),
                "--plugin",
                str(tmp_path),
                "--",
                *forwarded,
            ]
        )


def test_profile_uses_explicit_cache_without_machine_specific_paths(tmp_path):
    folder = tmp_path / "profile"
    local_profile.prepare(folder, model_cache=tmp_path / "models", binary="my-vllm")
    _, server = local_profile.load(folder)
    assert (
        server.binary == "my-vllm" and Path(server.model_cache) == tmp_path / "models"
    )
    assert "/home/milikic" not in (folder / "config.toml").read_text()


def test_run_restores_host_environment_after_a_failed_harness(tmp_path, monkeypatch):
    from proof_eval.harness import cli

    profile = tmp_path / "profile"
    local_profile.prepare(profile)
    output = tmp_path / "run with spaces"
    monkeypatch.setenv("PROOF_LEMEX_LOCAL_HOME", "previous-home")
    monkeypatch.delenv("PROOF_LEMEX_LOCAL_CAPACITY_NAMESPACE", raising=False)

    @contextmanager
    def server(*args):
        yield

    @contextmanager
    def proxy(*args, **kwargs):
        yield SimpleNamespace(environment={"PROOF_CAPTURE_TEST": "private"})

    def fail(argv):
        assert argv[argv.index("--condition") + 1] == lemex_local.MODEL + ":xhigh"
        assert argv[argv.index("--problem-timeout-seconds") + 1] == "28800"
        assert "--no-deterministic" in argv
        assert " " not in os.environ["PROOF_LEMEX_LOCAL_CAPACITY_NAMESPACE"]
        assert os.environ["PROOF_CAPTURE_TEST"] == "private"
        raise RuntimeError("fixture failure")

    monkeypatch.setattr(local, "ManagedServer", server)
    monkeypatch.setattr(local, "CaptureProxy", proxy)
    monkeypatch.setattr(cli, "main", fail)
    with pytest.raises(RuntimeError, match="fixture failure"):
        local.main(
            [
                "run",
                "--profile",
                str(profile),
                "--output",
                str(output),
                "--plugin",
                str(tmp_path),
                "--",
                "--names",
                "fixture",
            ]
        )
    assert os.environ["PROOF_LEMEX_LOCAL_HOME"] == "previous-home"
    assert "PROOF_LEMEX_LOCAL_CAPACITY_NAMESPACE" not in os.environ
    assert "PROOF_CAPTURE_TEST" not in os.environ


def test_self_hosted_usage_is_unpriced_and_gateway_card_stays_separate():
    local_card = rate_card("lemex-local")
    assert lemex_local.MODEL in local_card["unpriced_models"]
    assert lemex_local.MODEL not in rate_card("lemex")["unpriced_models"]
    cost = estimate_token_cost(
        CostConfig(lemex_local.MODEL, "xhigh"),
        {
            "input_tokens": 100,
            "output_tokens": 20,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "reasoning_output_tokens": 0,
        },
    )
    assert cost["total_usd"] is None
