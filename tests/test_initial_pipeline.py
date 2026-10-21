"""Fresh original starts, private caches, hard preprocessing limits and audited search."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path

import pytest
from test_budget_tracking import fake_native
from test_budget_tracking import tracking_run as _tracking_run

from proof_eval.evidence.io import digest, read, write_json
from proof_eval.harness.audit import audit
from proof_eval.harness.budget import run_cell
from proof_eval.harness.config import RunConfig
from proof_eval.optimization import bounded
from proof_eval.verification.initial import (
    audit_measurement_attempts,
    measure_original,
    private_evaluator,
)
from proof_eval.verification.references import original_evaluation

tracking_run = _tracking_run


def fresh_backend(run, monkeypatch):
    original = original_evaluation(run.pack)
    del run.evaluator.evaluate

    def check(row, code, version, project):
        source = (
            original
            if code.strip() == row["src"].strip()
            else run.saved["selected_evaluation"]
        )
        return deepcopy(source["per_version"][version])

    monkeypatch.setattr(run.evaluator.backend, "check", check)
    return original


def test_measure_original_uses_private_cache_and_resume_does_not_remeasure(
    tracking_run, monkeypatch, tmp_path
):
    run = tracking_run(initial_pipeline=True, cleanup=False)
    fresh_backend(run, monkeypatch)
    first = private_evaluator(run.evaluator, tmp_path / "first", run.pack)
    original, evaluation = measure_original(first, tmp_path / "first", run.pack)
    assert original == run.pack["row"]["src"]
    assert all(v["cached"] is False for v in evaluation["per_version"].values())
    assert measure_original(first, tmp_path / "first", run.pack) == (
        original,
        evaluation,
    )
    second = private_evaluator(run.evaluator, tmp_path / "second", run.pack)
    assert measure_original(second, tmp_path / "second", run.pack)[1] == evaluation
    assert first.store.root != second.store.root != run.evaluator.store.root


def test_original_timeout_retry_is_fresh_recorded_and_not_repeated_on_resume(
    tracking_run, monkeypatch, tmp_path
):
    run = tracking_run(initial_pipeline=True, cleanup=False)
    original = fresh_backend(run, monkeypatch)
    version = original["primary_version"]
    calls = []

    def check(row, code, v, project):
        calls.append(v)
        if v == version and calls.count(version) == 1:
            return {
                "status": "timeout",
                "passed": False,
                "heartbeats": None,
                "diagnostics": [],
            }
        return deepcopy(original["per_version"][v])

    monkeypatch.setattr(run.evaluator.backend, "check", check)
    folder = tmp_path / "measure"
    evaluator = private_evaluator(run.evaluator, folder, run.pack)
    proof, evaluation = measure_original(evaluator, folder, run.pack, timeout_retries=1)
    assert len(calls) == 2 * len(original["per_version"])
    assert all(
        v["passed"] and not v["cached"] for v in evaluation["per_version"].values()
    )
    audit_measurement_attempts(folder, run.pack["row"], 1)
    assert read(folder / "initial_measurement.json")["selected_attempt"] == 1
    resumed = private_evaluator(run.evaluator, folder, run.pack)
    assert measure_original(resumed, folder, run.pack, timeout_retries=1) == (
        proof,
        evaluation,
    )
    assert resumed.store.root == evaluator.store.root
    assert all(
        v["cached"]
        for v in resumed.evaluate(run.pack["name"], proof)["per_version"].values()
    )
    assert len(calls) == 2 * len(original["per_version"])
    first = folder / "initial_measurements/00.json"
    changed = read(first)
    changed["evaluation"]["per_version"][version]["status"] = "failed"
    write_json(first, changed)
    result = read(folder / "initial_measurement.json")
    result["attempt_sha256"]["initial_measurements/00.json"] = digest(first)
    write_json(folder / "initial_measurement.json", result)
    with pytest.raises(ValueError, match="non-timeout"):
        audit_measurement_attempts(folder, run.pack["row"], 1)


@pytest.mark.parametrize(
    "failure,expected_attempts", [("failed", 1), ("timeout", 2), ("interrupted", 1)]
)
def test_original_retry_is_bounded_and_never_replays_unknown_or_semantic_failure(
    tracking_run, monkeypatch, tmp_path, failure, expected_attempts
):
    run = tracking_run(initial_pipeline=True, cleanup=False)
    fresh_backend(run, monkeypatch)
    calls = []

    def check(*args):
        calls.append(args[2])
        if failure == "interrupted":
            raise RuntimeError("interrupted")
        return {
            "status": failure,
            "passed": False,
            "heartbeats": None,
            "diagnostics": [],
        }

    monkeypatch.setattr(run.evaluator.backend, "check", check)
    folder = tmp_path / "measure"
    evaluator = private_evaluator(run.evaluator, folder, run.pack)
    with pytest.raises((ValueError, RuntimeError)):
        measure_original(evaluator, folder, run.pack, timeout_retries=1)
    assert (
        len(list((folder / "initial_measurements").glob("*.started.json")))
        == expected_attempts
    )
    before = len(calls)
    with pytest.raises((ValueError, RuntimeError)):
        measure_original(evaluator, folder, run.pack, timeout_retries=1)
    assert len(calls) == before


def test_whole_problem_deadline_still_covers_original_measurement_retry(
    tracking_run, monkeypatch
):
    run = tracking_run(initial_pipeline=True, cleanup=False, timeout=1, tracking="time")
    fresh_backend(run, monkeypatch)
    calls = []
    versions = len(run.pack["incumbent"]["per_version"])

    def check(*args):
        calls.append(args[2])
        if len(calls) > versions:
            time.sleep(1000)
        return {
            "status": "timeout",
            "passed": False,
            "heartbeats": None,
            "diagnostics": [],
        }

    monkeypatch.setattr(run.evaluator.backend, "check", check)

    def no_model(**kwargs):
        raise AssertionError("Model cannot start with an unmeasured original")

    result = run_cell(
        run.output,
        run.config,
        run.pack,
        run.model,
        run.effort,
        run.evaluator,
        generator=no_model,
    )
    assert result["status"] == "incomplete"
    assert result["time_budget"]["exhausted"]
    assert not result["generations"]
    assert (run.folder / "initial_measurements/01.started.json").exists()
    assert not (run.folder / "initial_measurements/01.json").exists()
    assert audit(run.output)["status"] == "passed"


def test_recorded_discovery_timeout_retains_proof_and_allows_audited_model_search(
    tracking_run, monkeypatch
):
    run = tracking_run(
        initial_pipeline=True, initial_methods=("search",), cleanup=False, usd=0.1
    )
    fresh_backend(run, monkeypatch)

    def discovery_timeout(**kwargs):
        folder = kwargs["folder"]
        stage = folder / "stages/01_search"
        write_json(
            stage / "result.json",
            {"method": "search", "stop_reason": "discovery_unavailable"},
        )
        (stage / "trials.jsonl").write_text(
            json.dumps(
                {
                    "kind": "proposal_set",
                    "discovery": {
                        "status": "discovery_timeout",
                        "diagnostics": [
                            {"kind": "discovery_process", "timed_out": True}
                        ],
                    },
                }
            )
            + "\n"
        )
        write_json(
            folder / "result.json",
            {"status": "incomplete_discovery", "incomplete_methods": ["search"]},
        )

    monkeypatch.setattr(bounded, "cleanup_proof", discovery_timeout)
    result = run_cell(
        run.output,
        run.config,
        run.pack,
        run.model,
        run.effort,
        run.evaluator,
        generator=fake_native(run),
    )
    assert result["status"] == "complete"
    assert result["initial_cleanup_status"] == "discovery_limit"
    assert result["generations"]
    assert audit(run.output)["status"] == "passed"
    path = run.folder / "initial_optimization/job/stages/01_search/trials.jsonl"
    event = json.loads(path.read_text())
    event["discovery"]["status"] = "discovery_failed"
    path.write_text(json.dumps(event) + "\n")
    with pytest.raises(ValueError, match="Discovery timeout"):
        audit(run.output)


@pytest.mark.parametrize("methods", [(), ("golf",)])
def test_original_pipeline_runs_only_before_model_and_audits(
    tracking_run, monkeypatch, methods
):
    run = tracking_run(
        initial_pipeline=True,
        initial_methods=methods,
        cleanup=False,
        usd=0.1,
        restart_history=True,
    )
    fresh_backend(run, monkeypatch)
    if methods:

        def clean(**kwargs):
            kwargs["evaluator"].evaluate(
                run.pack["name"], run.saved["selected_proof"], versions="all"
            )

        monkeypatch.setattr(bounded, "cleanup_proof", clean)
    result = run_cell(
        run.output,
        run.config,
        run.pack,
        run.model,
        run.effort,
        run.evaluator,
        generator=fake_native(run),
    )
    assert result["seed_proof"] == run.pack["row"]["src"]
    assert result["final_cleanup_status"] == "disabled"
    assert result["deterministic_calls"] == 0
    assert result["initial_cleanup_status"] == ("complete" if methods else "disabled")
    assert audit(run.output)["status"] == "passed"
    initial = run.folder / "initial_measurement.json"
    before = read(initial)
    tampered = deepcopy(before)
    next(iter(tampered["evaluation"]["per_version"].values()))["cached"] = True
    write_json(initial, tampered)
    with pytest.raises(ValueError, match="Original measurement"):
        audit(run.output)


def test_cap_kills_inflight_lean_and_retains_verified_improvement(
    tracking_run, monkeypatch, tmp_path
):
    run = tracking_run(initial_pipeline=True, cleanup=False)
    fresh_backend(run, monkeypatch)
    evaluator = private_evaluator(run.evaluator, tmp_path / "cell", run.pack)
    proof, evaluation = measure_original(evaluator, tmp_path / "cell", run.pack)
    pid_file = tmp_path / "descendant.json"

    def slow(**kwargs):
        kwargs["evaluator"].evaluate(
            run.pack["name"], run.saved["selected_proof"], versions="all"
        )
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(1000)"],
            start_new_session=True,
        )
        write_json(pid_file, {"pid": child.pid})
        time.sleep(1000)

    monkeypatch.setattr(bounded, "cleanup_proof", slow)
    started = time.monotonic()
    result = bounded.run_bounded(
        evaluator=evaluator,
        row=run.pack["row"],
        proof=proof,
        evaluation=evaluation,
        folder=tmp_path / "phase",
        methods=("golf",),
        seconds=1.0,
    )
    assert time.monotonic() - started < 3
    assert result["status"] == "time_limit"
    assert result["proof"] == run.saved["selected_proof"]
    assert result["accepted_improvements"] == 1
    pid = read(pid_file)["pid"]
    stat = Path(f"/proc/{pid}/stat")
    assert not stat.exists() or stat.read_text().rsplit(")", 1)[1].split()[0] == "Z"
    assert result == bounded.run_bounded(
        evaluator=evaluator,
        row=run.pack["row"],
        proof=proof,
        evaluation=evaluation,
        folder=tmp_path / "phase",
        methods=("golf",),
        seconds=1.0,
    )


def test_five_minute_limit_is_not_configurable_upwards():
    for seconds in (0, -1, 301, float("inf"), float("nan"), True):
        with pytest.raises(ValueError, match="300 seconds"):
            RunConfig(deterministic_seconds=seconds)
    with pytest.raises(ValueError, match="original proofs"):
        RunConfig(incumbents_from=Path("old-run"))


def test_whole_problem_deadline_during_transforms_recovers_partial_certificate(
    tracking_run, monkeypatch
):
    run = tracking_run(
        initial_pipeline=True,
        initial_methods=("golf",),
        initial_seconds=5,
        cleanup=False,
        timeout=1.0,
        tracking="time",
    )
    fresh_backend(run, monkeypatch)

    def slow(**kwargs):
        kwargs["evaluator"].evaluate(
            run.pack["name"], run.saved["selected_proof"], versions="all"
        )
        time.sleep(1000)

    monkeypatch.setattr(bounded, "cleanup_proof", slow)

    def no_model(**kwargs):
        raise AssertionError("A model must not start before the initial phase finishes")

    result = run_cell(
        run.output,
        run.config,
        run.pack,
        run.model,
        run.effort,
        run.evaluator,
        generator=no_model,
    )
    assert result["selected_proof"] == run.saved["selected_proof"]
    assert not result["generations"]
    assert result["initial_cleanup_status"] == "problem_deadline"
    assert result["time_budget"]["exhausted"]
    assert audit(run.output)["status"] == "passed"
