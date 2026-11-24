"""Submission launch delegates to existing contracts; setup/preview never infer."""

import json
import os
import subprocess

import pytest

from proof_eval.evidence.io import read, write_json
from proof_eval.harness import submission


@pytest.fixture
def launch(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle with spaces"
    bundle.mkdir()
    write_json(bundle / "recipe.json", {"fixture": True})
    recipe = {
        "dataset": "benchmark/problems.jsonl",
        "environments": "environments.json",
        "web_search": True,
        "semantic_search": False,
        "names": ["original"],
    }
    cpu = {
        "base": "/prepared/base",
        "references": "/prepared/reference_values.jsonl",
        "identity": "frozen-setup",
    }
    monkeypatch.setattr(submission, "verify_initialization", lambda *a: (recipe, cpu))
    return bundle, tmp_path / "work with spaces", tmp_path / "new output", recipe, cpu


def test_preview_never_starts_server_or_creates_output(launch, monkeypatch):
    from proof_eval.interfaces import local

    bundle, work, output, *_ = launch
    monkeypatch.setattr(
        local, "main", lambda *a: pytest.fail("no inference in preview")
    )
    result = submission.run_submission(bundle, work, output, preview=True)
    assert result["model_calls"] == 0 and result["starts_server"] is False
    assert "--original-measurement-policy" in result["argv"]
    assert "prepared" in result["argv"]
    assert "--starting-proofs" not in result["argv"]
    assert not output.exists()


def test_missing_serving_runtime_fails_before_reference_preparation(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(submission, "verify_bundle", lambda *a: {})
    monkeypatch.setattr(submission, "_config", lambda *a: object())
    monkeypatch.setattr(
        submission,
        "setup",
        lambda *a: pytest.fail("no reference work before preflight"),
    )
    with pytest.raises(ValueError, match="separate serving environment"):
        submission.initialize(tmp_path / "bundle", tmp_path / "work")
    assert not (tmp_path / "work/setup_started.json").exists()


def test_run_forwards_the_current_hosts_admitted_reference_cache(launch):
    bundle, work, output, _, cpu = launch
    cpu["cache"] = "/current-host/private-reference-cache"
    preview = submission.run_submission(bundle, work, output, preview=True)
    argv = preview["argv"]
    assert argv[argv.index("--cache") + 1] == cpu["cache"]
    assert not output.exists()


def test_invalid_guard_fails_before_reference_preparation(tmp_path, monkeypatch):
    work = tmp_path / "work"
    serving = work / "envs/serving/bin"
    serving.mkdir(parents=True)
    for name in ("python", "vllm"):
        (serving / name).write_text("fixture")
    monkeypatch.setattr(submission, "verify_bundle", lambda *a: {})
    monkeypatch.setattr(submission, "_config", lambda *a: object())
    monkeypatch.setattr(
        submission,
        "setup",
        lambda *a: pytest.fail("no reference work before preflight"),
    )

    def invalid():
        raise ValueError("Signal scope: invalid guard")

    monkeypatch.setattr(submission.signal_scope, "configured_identity", invalid)
    with pytest.raises(ValueError, match="invalid guard"):
        submission.initialize(tmp_path / "bundle", work)
    assert not (work / "setup_started.json").exists()


def test_initialization_prepares_cpu_references_then_downloads_without_starting_gpu(
    tmp_path, monkeypatch
):
    bundle, work = tmp_path / "archive", tmp_path / "work"
    bundle.mkdir()
    write_json(bundle / "recipe.json", {"fixed": True})
    recipe = {
        "track": "open_local",
        "starting_proofs": "organizer_originals",
        "dataset": "benchmark/problems.jsonl",
        "environments": "environments.json",
        "model": submission.local_profile.MODEL,
        "revision": submission.local_profile.REVISIONS[submission.local_profile.MODEL],
        "workers": 10,
        "seconds": 28080,
        "context": 266400,
        "compaction": 222400,
        "verification_seconds": 600,
        "setup_workers": 1,
        "setup_cpus": 8,
        "proof_history": False,
        "cleanup_before": False,
        "cleanup_after": False,
        "semantic_search": False,
    }
    serving = work / "envs/serving/bin"
    serving.mkdir(parents=True)
    for name in ("python", "vllm"):
        (serving / name).write_text("fixture")
    cpu = {
        "identity": "originals-checked",
        "base": "/prepared",
        "references": "/references",
    }
    order = []

    def prepare(config):
        assert config.verification_seconds == 600
        order.append("cpu")
        return cpu

    def snapshot(python, frozen, cache, *, download):
        assert frozen["revision"] == recipe["revision"]
        order.append("download" if download else "cached-only")
        return "/pinned/model/snapshot"

    monkeypatch.setattr(submission, "verify_bundle", lambda *a: recipe)
    monkeypatch.setattr(submission, "setup", prepare)
    monkeypatch.setattr(submission, "admit_setup", lambda *a: cpu)
    monkeypatch.setattr(submission, "_snapshot", snapshot)
    monkeypatch.setattr(
        submission.signal_scope, "configured_identity", lambda: {"validated": True}
    )
    monkeypatch.setattr(
        submission.vllm_server,
        "metadata",
        lambda *a: {"versions": submission.SERVING_VERSIONS},
    )
    monkeypatch.setattr(
        submission.vllm_server,
        "ManagedServer",
        lambda *a: pytest.fail("setup must not load a model"),
    )
    assert submission.initialize(bundle, work)["status"] == "ready"
    assert order == ["cpu", "download"]
    saved = (work / "initialized.json").read_bytes()
    assert read(work / "initialized.json")["model_calls"] == 0
    assert submission.verify_initialization(bundle, work) == (recipe, cpu)
    assert order[-1] == "cached-only"
    assert submission.initialize(bundle, work)["status"] == "ready"
    assert (work / "initialized.json").read_bytes() == saved
    monkeypatch.setattr(
        submission.vllm_server, "metadata", lambda *a: {"versions": {"vllm": "wrong"}}
    )
    count = order.count("download")
    with pytest.raises(ValueError, match="Serving package versions"):
        submission.initialize(bundle, work)
    assert order.count("download") == count
    assert (work / "initialized.json").read_bytes() == saved


@pytest.mark.parametrize("suffix", ["", " /-\u2028-/"])
def test_run_audits_and_exports_full_cohort_and_restores_environment(
    launch, monkeypatch, suffix
):
    from proof_eval.harness import cli
    from proof_eval.interfaces import local

    bundle, work, output, recipe, _ = launch
    previous = os.environ.get("PROOF_SIGNAL_SCOPE_BINARY")
    calls = []

    def native(argv):
        assert os.environ["PROOF_SIGNAL_SCOPE_BINARY"] == str(
            bundle / "bin/signal-scope"
        )
        assert argv[:3] == ["run", "--profile", str(work / "profile")]
        # Policy is frozen in the local profile, not an override after `--`.
        assert "--no-proof-history" not in argv
        assert "--no-semantic-search" in argv
        candidates = output / "model/conditions/fixture/selected_candidates.jsonl"
        candidates.parent.mkdir(parents=True)
        candidates.write_text(
            json.dumps(
                {
                    "name": "original",
                    "proof": "theorem original : True := by trivial" + suffix,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        calls.append("run")
        return 0

    def audit(argv):
        assert argv == ["audit", "--output", str(output)]
        calls.append("audit")
        return 0

    monkeypatch.setattr(local, "main", native)
    monkeypatch.setattr(cli, "main", audit)
    result = submission.run_submission(bundle, work, output)
    assert result["status"] == "complete"
    assert json.loads((output / "submission.jsonl").read_text())["proof"].endswith(
        suffix
    )
    assert read(output / "optimization_finished.json")["status"] == "complete"
    assert calls == ["run", "audit"]
    assert os.environ.get("PROOF_SIGNAL_SCOPE_BINARY") == previous
    # A changed source recipe cannot resume an existing output silently.
    write_json(bundle / "recipe.json", {"changed": True})
    with pytest.raises(ValueError, match="configuration changed"):
        submission.run_submission(bundle, work, output)
    assert calls == ["run", "audit"]


@pytest.mark.parametrize("failure", ["model", "audit", "coverage"])
def test_failed_run_or_audit_never_exports_complete_submission(
    launch, monkeypatch, failure
):
    from proof_eval.harness import cli
    from proof_eval.interfaces import local

    bundle, work, output, *_ = launch

    def native(argv):
        if failure == "model":
            raise RuntimeError("native unknown result")
        candidates = output / "model/conditions/fixture/selected_candidates.jsonl"
        candidates.parent.mkdir(parents=True)
        candidates.write_text(
            json.dumps(
                {
                    "name": "wrong" if failure == "coverage" else "original",
                    "proof": "proof",
                }
            )
            + "\n"
        )
        return 0

    monkeypatch.setattr(local, "main", native)
    monkeypatch.setattr(cli, "main", lambda *a: 2 if failure == "audit" else 0)
    with pytest.raises((RuntimeError, ValueError)):
        submission.run_submission(bundle, work, output)
    finished = read(output / "optimization_finished.json")
    assert finished["status"] == "incomplete" and finished["exit_code"] != 0
    assert not (output / "submission.jsonl").exists()


def test_explicit_semantic_assets_are_forwarded_without_home_cache(launch):
    bundle, work, output, recipe, cpu = launch
    recipe.update(
        semantic_search=True,
        semantic_index="assets/index",
        embedding_model="assets/embedding",
    )
    argv = submission.optimization_arguments(bundle, work, output, recipe, cpu)
    assert argv[argv.index("--semantic-index") + 1] == str(bundle / "assets/index")
    assert argv[argv.index("--embedding-model") + 1] == str(bundle / "assets/embedding")


def test_model_download_and_offline_server_use_the_same_hub_cache(
    tmp_path, monkeypatch
):
    from proof_eval.providers.vllm_server import ServerConfig, environment

    calls = []
    monkeypatch.setattr(
        submission.subprocess,
        "check_output",
        lambda argv, **kwargs: calls.append(argv) or "/snapshot\n",
    )
    recipe = {"model": submission.local_profile.MODEL, "revision": "a" * 40}
    cache = tmp_path / "models"
    serving = ServerConfig(model_cache=str(cache))
    assert (
        submission._snapshot(tmp_path / "python", recipe, cache, download=True)
        == "/snapshot"
    )
    assert calls[-1][5] == environment(serving, tmp_path)["HF_HUB_CACHE"]
    assert calls[-1][-1] == "download"
    submission._snapshot(tmp_path / "python", recipe, cache, download=False)
    assert calls[-1][-1] == "local"


def test_harness_accepts_paired_explicit_assets_without_changing_defaults(
    tmp_path, monkeypatch
):
    from proof_eval.harness import cli
    from proof_eval.harness.semantic import SemanticSearchConfig

    seen = []
    monkeypatch.setattr(
        cli,
        "run_pipeline",
        lambda config: seen.append(config) or {"status": "prepared"},
    )
    args = ["prepare", "--output", str(tmp_path / "output")]
    assert (
        cli.main(
            [
                *args,
                "--semantic-index",
                str(tmp_path / "index"),
                "--embedding-model",
                str(tmp_path / "embedding"),
            ]
        )
        == 0
    )
    assert seen[-1].model.semantic_search == SemanticSearchConfig(
        tmp_path / "index", tmp_path / "embedding"
    )
    assert cli.main(args) == 0
    assert seen[-1].model.semantic_search is True
    assert cli.main([*args, "--semantic-index", str(tmp_path)]) == 2
    assert (
        cli.main(
            [
                *args,
                "--semantic-index",
                str(tmp_path),
                "--embedding-model",
                str(tmp_path),
                "--no-semantic-search",
            ]
        )
        == 2
    )


def test_setup_and_run_wrappers_are_quoted_and_setup_does_not_run_optimization(
    tmp_path,
):
    from proof_eval.paths import ROOT

    bundle = tmp_path / "portable bundle"
    bundle.mkdir()
    work = tmp_path / "persistent work"
    (work / "bundle").mkdir(parents=True)
    harness = work / "envs/harness/bin"
    harness.mkdir(parents=True)
    serving = work / "envs/serving/bin"
    serving.mkdir(parents=True)
    for path in (harness / "python", serving / "vllm"):
        path.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$SUBMISSION_TEST_ARGS"\n')
        path.chmod(0o755)
    args_file = tmp_path / "args"
    commands = tmp_path / "commands"
    commands.mkdir()
    for name in ("git", "lake", "lean", "elan", "taskset", "rg"):
        command = commands / name
        command.write_text("#!/bin/sh\nexit 0\n")
        command.chmod(0o755)
    env = {
        **os.environ,
        "SUBMISSION_TEST_ARGS": str(args_file),
        "PATH": str(commands) + os.pathsep + os.environ["PATH"],
    }
    output = tmp_path / "fresh output with spaces"
    for directory in (bundle, work / "bundle"):
        (directory / "toolchain-env.sh").write_bytes(
            (ROOT / "toolchain-env.sh").read_bytes()
        )
    for action in ("setup", "run", "search", "cleanup"):
        source = ROOT / f"{action}.sh"
        target = bundle / source.name
        target.write_bytes(source.read_bytes())
        argv = ["bash", str(target), str(work)]
        if action != "setup":
            argv.append(str(output))
        subprocess.run(argv, env=env, check=True, cwd=tmp_path)
        args = args_file.read_text().splitlines()
        assert args[:3] == ["-m", "proof_eval.interfaces.submission", action]
        assert args[args.index("--bundle") + 1] == str(work / "bundle")
        assert args[args.index("--work") + 1] == str(work)
        if action != "setup":
            assert args[args.index("--output") + 1] == str(output)
