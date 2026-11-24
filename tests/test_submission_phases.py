"""Public phase boundaries and verified delivery without any model/Lean calls."""

import json
import shutil

import pytest
from test_cleanup_cohort import batch
from test_search_exploration import C, discovery
from test_solution_export import saved_model

from proof_eval.evidence.io import digest, read, write_json
from proof_eval.harness import submission_phases as phases
from proof_eval.providers import host_support

__all__ = ["batch", "discovery", "saved_model"]


@pytest.fixture
def release(saved_model, batch, tmp_path, monkeypatch):
    old_output, model, _ = saved_model
    bundle, work, output = tmp_path / "bundle", tmp_path / "work", tmp_path / "delivery"
    bundle.mkdir()
    work.mkdir()
    recipe = {
        "model": "fixture",
        "effort": "max",
        "names": ["p"],
        "seconds": 2,
        "dataset": "problems.jsonl",
        "environments": "environments.json",
        "cleanup_workers": 1,
        "cleanup_after": True,
        "semantic_search": False,
        "web_search": False,
    }
    shutil.copy2(batch["args"]["dataset"], bundle / recipe["dataset"])
    shutil.copy2(batch["args"]["environments"], bundle / recipe["environments"])
    write_json(bundle / "recipe.json", recipe)
    write_json(work / "search-profile/profile.json", {"cleanup_after": False})
    write_json(
        work / "initialized.json",
        {"search_profile_sha256": digest(work / "search-profile/profile.json")},
    )
    write_json(
        work / "preparation-finished.json", {"status": "complete", "elapsed_seconds": 1}
    )
    cpu = {
        key: str(value)
        for key, value in batch["args"].items()
        if key in ["base", "references", "cache"]
    }
    monkeypatch.setattr(phases, "verify_initialization", lambda *a: (recipe, cpu))
    monkeypatch.setattr(phases, "_config", lambda *a: object())
    # Phase tests use fake model/evaluator boundaries, including host admission.
    monkeypatch.setattr(
        host_support, "require_supported", lambda *a: {"status": "fixture"}
    )
    from proof_eval.benchmark import submission as setup
    from proof_eval.evidence import submission as bundles
    from proof_eval.harness import pipeline_reporting
    from proof_eval.interfaces import local

    monkeypatch.setattr(setup, "admit_setup", lambda *a: cpu)
    monkeypatch.setattr(bundles, "verify_bundle", lambda *a: recipe)
    monkeypatch.setattr(
        pipeline_reporting, "audit_pipeline", lambda *a: {"status": "passed"}
    )
    calls = []

    def native(argv):
        calls.append(argv)
        destination = output / "search/model"
        assert not destination.exists()
        assert "--no-semantic-search" in argv
        shutil.copytree(model, destination)
        write_json(
            destination / "run.json",
            {"status": "finished", "at": "2026-01-01T00:00:02+00:00"},
        )
        cell = next((destination / "cells").iterdir())
        write_json(
            cell / "budget_started.json",
            {
                "started_epoch": 1767225600.0,
                "deadline_epoch": 1767225602.0,
                "timeout_seconds": 2,
            },
        )
        write_json(
            cell / "result.json",
            {
                "name": "p",
                "status": "complete",
                "stop": {"kind": "time_limit"},
                "time_budget": {"exhausted": True},
            },
        )
        write_json(
            cell / "budget_end.json",
            {
                "exhausted": True,
                "work_stopped_epoch": 1767225602.0,
                "cleanup": {
                    "complete": True,
                    "freeze_complete": True,
                    "remaining_pids": [],
                },
            },
        )
        return 0

    monkeypatch.setattr(local, "main", native)
    return bundle, work, output, calls


def test_search_finishes_before_cpu_cleanup_and_never_replays(
    release, discovery, monkeypatch
):
    bundle, work, output, calls = release
    result = phases.search(bundle, work, output)
    assert result["GPU_server_stopped"] and len(calls) == 1
    assert not (output / "cleanup").exists()
    assert calls[0][calls[0].index("--output") + 1] == str(output / "search")
    assert read(output / "search-timing.json")["model_search_wall_seconds"] == 2
    assert (
        read(output / "model-timer-finished.json")["event"] == "MODEL_SEARCH_FINISHED"
    )
    assert read(output / "model-timer-finished.json")["CPU_cleanup_started"] is False
    assert phases.search(bundle, work, output) == result and len(calls) == 1
    from proof_eval.interfaces import local

    monkeypatch.setattr(
        local, "main", lambda *a: pytest.fail("CPU cleanup must not start inference")
    )
    final = phases.cleanup(bundle, work, output)
    assert final["model_calls"] == 0 and final["GPU_required"] is False
    assert final["audit"]["status"] == "passed"
    assert json.loads((output / "submission.jsonl").read_text()) == {
        "name": "p",
        "proof": C,
    }
    assert (output / "timing.json").is_file()
    assert phases.cleanup(bundle, work, output) == final
    assert phases.run(bundle, work, output) == final and len(calls) == 1


def test_no_cleanup_run_delivers_without_starting_cpu_cleanup(release, monkeypatch):
    bundle, work, output, calls = release
    monkeypatch.setattr(
        phases,
        "cleanup",
        lambda *a: pytest.fail("The no-cleanup option must skip CPU cleanup"),
    )
    result = phases.run(bundle, work, output, final_cleanup=False)
    assert result["submission"] == str(output / "submission.jsonl")
    assert result["cleanup_requested"] is False
    assert result["cleanup_completed"] is False
    assert result["proof_source"] == "verified_model"
    assert digest(output / "submission.jsonl") == digest(
        output / "model-submission.jsonl"
    )
    assert not (output / "cleanup-started.json").exists()
    assert read(output / "timing.json")["cleanup"]["status"] == "not_requested"
    assert (
        phases.run(bundle, work, output, final_cleanup=False) == result
        and len(calls) == 1
    )


def test_default_run_cleans_only_after_model_server_shutdown(
    release, discovery, monkeypatch
):
    bundle, work, output, calls = release
    from proof_eval.optimization import cohort

    original = cohort.run_cleanup
    cleanup_calls = []

    def cpu_only(**kwargs):
        assert len(calls) == 1
        assert read(output / "search-ready.json")["GPU_server_stopped"] is True
        assert read(output / "model-timer-finished.json")["search_completed"] is True
        assert read(output / "search-finished.json")["status"] == "complete"
        assert read(output / "submission-ready.json")["cleanup_requested"] is True
        cleanup_calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(cohort, "run_cleanup", cpu_only)
    result = phases.run(bundle, work, output)
    assert result["cleanup_requested"] and result["cleanup_completed"]
    assert result["proof_source"] == "cleaned" and result["model_calls"] == 0
    assert result["GPU_required"] is False and len(cleanup_calls) == 1
    assert phases.run(bundle, work, output) == result
    assert len(calls) == len(cleanup_calls) == 1


def test_explicit_cleanup_overrides_recipe_without_changing_search(release, discovery):
    bundle, work, output, calls = release
    recipe = read(bundle / "recipe.json")
    recipe["cleanup_after"] = False
    write_json(bundle / "recipe.json", recipe)
    result = phases.run(bundle, work, output, final_cleanup=True)
    assert result["cleanup_completed"] and len(calls) == 1
    assert read(work / "search-profile/profile.json")["cleanup_after"] is False


@pytest.mark.parametrize(
    "option,expected", [(None, None), ("--cleanup", True), ("--no-cleanup", False)]
)
def test_run_cli_forwards_cleanup_choice(release, monkeypatch, option, expected):
    from proof_eval.interfaces import submission

    bundle, work, output, _ = release
    received = []
    monkeypatch.setattr(
        phases,
        "run",
        lambda *a, **kw: received.append((a, kw)) or {"status": "fixture"},
    )
    argv = [
        "run",
        "--bundle",
        str(bundle),
        "--work",
        str(work),
        "--output",
        str(output),
    ]
    if option:
        argv.append(option)
    assert submission.main(argv) == 0
    assert received == [
        ((bundle, work, output), {"preview": False, "final_cleanup": expected})
    ]


def test_default_dry_run_starts_neither_model_nor_cleanup(release, monkeypatch):
    bundle, work, output, calls = release
    monkeypatch.setattr(
        phases, "optimization_arguments", lambda *a: ["--profile", "unused"]
    )
    monkeypatch.setattr(
        phases, "cleanup", lambda *a: pytest.fail("Dry run cannot clean up")
    )
    result = phases.run(bundle, work, output, preview=True)
    assert result["model_calls"] == 0 and result["starts_server"] is False
    assert not output.exists() and calls == []


def test_repeated_run_rejects_changed_ready_delivery_without_inference(release):
    bundle, work, output, calls = release
    phases.run(bundle, work, output, final_cleanup=False)
    (output / "submission.jsonl").write_text("changed")
    with pytest.raises(ValueError, match="delivery changed"):
        phases.run(bundle, work, output, final_cleanup=False)
    assert len(calls) == 1


def test_release_profile_uses_795_hour_budget_and_post_server_cleanup(tmp_path):
    from proof_eval.paths import ROOT
    from proof_eval.providers import local_profile

    recipe = read(ROOT / "recipe.json")
    assert recipe["seconds"] == 28620 and recipe["cleanup_after"] is True
    assert 48 * 3600 - recipe["seconds"] * 6 == 18 * 60
    work = tmp_path / "fresh-work"
    profile = phases.prepare_search_profile(ROOT, work, recipe)
    value, _ = local_profile.load(profile)
    assert value["seconds"] == 28620 and value["workers"] == 10
    assert value["proof_history"] is False
    assert value["cleanup_before"] is False and value["cleanup_after"] is False


def test_cleanup_rejects_active_or_changed_search(release, monkeypatch):
    bundle, work, output, calls = release
    with pytest.raises(ValueError, match="Search must finish"):
        phases.cleanup(bundle, work, output)
    assert calls == []
    phases.search(bundle, work, output)
    (output / "model-certificates.json").write_text("changed")
    with pytest.raises(ValueError, match="proof evidence changed"):
        phases.cleanup(bundle, work, output)
    assert not (output / "cleanup-started.json").exists()


def test_existing_output_is_not_overwritten_or_replayed(release):
    bundle, work, output, calls = release
    output.mkdir()
    (output / "notes.txt").write_text("preserve")
    with pytest.raises(ValueError, match="fresh output"):
        phases.search(bundle, work, output)
    assert calls == [] and (output / "notes.txt").read_text() == "preserve"


def test_trace_bookkeeping_error_keeps_valid_host_proofs(release, monkeypatch):
    bundle, work, output, _ = release
    from proof_eval.harness import pipeline_reporting

    def fail(*args):
        raise ValueError("terminal usage")

    monkeypatch.setattr(pipeline_reporting, "audit_pipeline", fail)
    result = phases.search(bundle, work, output)
    assert result["status"] == "incomplete"
    assert result["proof_delivery_completed"] is True
    assert result["diagnostics"][0]["stage"] == "trace_audit"
    assert json.loads((output / "model-submission.jsonl").read_text())["proof"] == C


def test_failed_search_preserves_proofs_but_cli_fails_and_never_replays(
    release, monkeypatch
):
    from proof_eval.interfaces import local, submission

    bundle, work, output, calls = release
    native = local.main

    def fail(argv):
        native(argv)
        model = output / "search/model"
        write_json(
            model / "run.json", {"status": "failed", "at": "2026-01-01T00:00:01+00:00"}
        )
        for cell in (model / "cells").iterdir():
            (cell / "result.json").unlink()
            (cell / "budget_end.json").unlink()
        return 2

    monkeypatch.setattr(local, "main", fail)
    monkeypatch.setattr(
        phases, "cleanup", lambda *a: pytest.fail("failed search cannot clean up")
    )
    argv = [
        "run",
        "--bundle",
        str(bundle),
        "--work",
        str(work),
        "--output",
        str(output),
    ]
    assert submission.main(argv) == 2
    ready = read(output / "submission-ready.json")
    assert ready["status"] == "incomplete" and ready["search_completed"] is False
    assert ready["proof_delivery_completed"] is True
    assert ready["outcomes"]["normal_completed"] == 0
    assert ready["outcomes"]["incomplete_names"] == ["p"]
    assert read(output / "search-finished.json")["status"] == "incomplete"
    assert json.loads((output / "submission.jsonl").read_text())["proof"] == C
    assert set(read(output / "model-certificates.json")["certificates"]) == {"p"}
    timing = read(output / "search-timing.json")
    assert list(timing["actual_problem_elapsed_seconds"].values()) == [1]
    assert submission.main(argv) == 2 and len(calls) == 1


def test_missing_full_window_result_is_incomplete_even_with_exit_zero(
    release, monkeypatch
):
    from proof_eval.interfaces import local

    bundle, work, output, _ = release
    native = local.main

    def short_window(argv):
        code = native(argv)
        cell = next((output / "search/model/cells").iterdir())
        stopped = read(cell / "budget_end.json")
        stopped["work_stopped_epoch"] -= 1
        write_json(cell / "budget_end.json", stopped)
        return code

    monkeypatch.setattr(local, "main", short_window)
    result = phases.search(bundle, work, output)
    assert (
        result["status"] == "incomplete" and result["outcomes"]["normal_completed"] == 0
    )


def test_reaped_worker_needs_its_real_native_deadline_receipt(release, monkeypatch):
    from proof_eval.harness import limits
    from proof_eval.interfaces import local

    bundle, work, output, _ = release
    local.main(["--no-semantic-search"])
    root = output / "search/model"
    cell = next((root / "cells").iterdir())
    stopped = read(cell / "budget_end.json")
    stopped.pop("cleanup")
    stopped["worker_reaped_before_deadline_recovery"] = True
    write_json(cell / "budget_end.json", stopped)
    recipe = read(bundle / "recipe.json")
    monkeypatch.setattr(limits, "native_deadline_reached", lambda p: False)
    assert phases._normal_search_outcomes(root, recipe)["normal_completed"] == 0
    monkeypatch.setattr(limits, "native_deadline_reached", lambda p: p == cell)
    assert phases._normal_search_outcomes(root, recipe)["normal_completed"] == 1
    stopped["cleanup"] = {"complete": False, "remaining_pids": [123]}
    write_json(cell / "budget_end.json", stopped)
    assert phases._normal_search_outcomes(root, recipe)["normal_completed"] == 0


def test_global_cleanup_error_delivers_sealed_model_proofs(release, monkeypatch):
    bundle, work, output, calls = release
    phases.search(bundle, work, output)
    from proof_eval.optimization import cohort

    def fail(**kwargs):
        raise RuntimeError("cleanup worker unavailable")

    monkeypatch.setattr(cohort, "run_cleanup", fail)
    result = phases.cleanup(bundle, work, output)
    assert len(calls) == 1
    assert result["status"] == "incomplete" and result["cleanup_completed"] is False
    assert result["proof_source"] == "verified_model_fallback"
    assert result["diagnostics"][-1]["stage"] == "cleanup"
    assert json.loads((output / "submission.jsonl").read_text())["proof"] == C
    assert phases.cleanup(bundle, work, output) == result
    from proof_eval.interfaces import submission

    assert (
        submission.main(
            [
                "cleanup",
                "--bundle",
                str(bundle),
                "--work",
                str(work),
                "--output",
                str(output),
            ]
        )
        == 2
    )


def test_interrupt_preserves_model_submission_without_claiming_cleanup(
    release, monkeypatch
):
    bundle, work, output, _ = release
    phases.search(bundle, work, output)
    from proof_eval.optimization import cohort

    def interrupt(**kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(cohort, "run_cleanup", interrupt)
    with pytest.raises(KeyboardInterrupt):
        phases.cleanup(bundle, work, output)
    ready = read(output / "submission-ready.json")
    assert ready["proof_source"] == "verified_model"
    assert ready["cleanup_requested"] is True
    assert ready["cleanup_completed"] is False
    assert not (output / "cleanup-ready.json").exists()
    assert read(output / "cleanup-finished.json")["status"] == "incomplete"


def test_real_local_and_harness_cli_use_the_pipeline_model_subdirectory(
    release, saved_model, monkeypatch
):
    from contextlib import nullcontext
    from types import SimpleNamespace

    from proof_eval.harness import cli
    from proof_eval.interfaces import local

    bundle, work, output, _ = release
    from proof_eval.evidence.io import fingerprint
    from proof_eval.providers.local_profile import MODEL

    recipe, _ = phases.verify_initialization(bundle, work)
    recipe.update(model=MODEL, effort="xhigh")
    write_json(bundle / "recipe.json", recipe)
    (bundle / "integrations/vllm_ampere").mkdir(parents=True)
    # Recover the actual entry function; the fixture's native boundary is replaced.
    import importlib

    actual_main = importlib.reload(local).main
    monkeypatch.setattr(local, "ManagedServer", lambda *a: nullcontext())
    monkeypatch.setattr(
        local,
        "CaptureProxy",
        lambda *a, **kw: nullcontext(SimpleNamespace(environment={})),
    )
    monkeypatch.setattr(
        local.local_profile,
        "load",
        lambda *a: (
            {
                "model": MODEL,
                "effort": "xhigh",
                "workers": 1,
                "seconds": 28620,
                "proof_history": False,
                "cleanup_before": False,
                "cleanup_after": False,
            },
            SimpleNamespace(endpoint="http://localhost:8128"),
        ),
    )
    seen = []

    def pipeline(config):
        seen.append(config)
        assert config.cleanup_before is False and config.cleanup_after is False
        assert config.model.problem_timeout_seconds == 28620
        destination = config.model.output / "model"
        shutil.copytree(saved_model[1], destination)
        config_file = read(destination / "config.json")
        config_file["conditions"] = [[MODEL, "xhigh"]]
        write_json(destination / "config.json", config_file)
        old_cell = next((destination / "cells").iterdir())
        inp = read(old_cell / "input.json")
        inp.update(model=MODEL, effort="xhigh")
        write_json(old_cell / "input.json", inp)
        old_cell.rename(
            old_cell.parent
            / fingerprint((inp["name"], MODEL, "xhigh", config_file["mode"]))
        )
        write_json(
            destination / "run.json",
            {"status": "finished", "at": "2026-01-01T00:00:02+00:00"},
        )
        cell = next((destination / "cells").iterdir())
        write_json(
            cell / "budget_started.json",
            {"started_epoch": 1767225600.0, "timeout_seconds": 28620},
        )
        return {"status": "complete"}

    monkeypatch.setattr(cli, "run_pipeline", pipeline)
    monkeypatch.setattr(local, "main", actual_main)
    result = phases.search(bundle, work, output)
    assert len(seen) == 1 and result["problems"] == 1
    assert (output / "search/model/cells").is_dir()
    assert result["timing"]["model_search_wall_seconds"] == 2
