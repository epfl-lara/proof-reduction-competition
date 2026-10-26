"""Whole-cohort barriers, separate workers, scoped seeds and durable phase errors."""

from dataclasses import replace
from pathlib import Path

import pytest
from test_cleanup_cohort import batch
from test_search_exploration import A, C, Evaluator, discovery

from proof_eval.evidence.io import digest, fingerprint, read, write_json
from proof_eval.evidence.proof_states import export_proof_states, freeze_proof_states
from proof_eval.harness import pipeline, pipeline_reporting
from proof_eval.harness.config import RunConfig
from proof_eval.harness.pipeline import PipelineConfig, run_pipeline
from proof_eval.optimization import cohort

__all__ = ["batch", "discovery"]


@pytest.fixture
def workflow(batch, monkeypatch):
    arguments = batch["args"]
    monkeypatch.setattr(pipeline, "ROOT", Path(arguments["output"]).parent / "runtime")
    monkeypatch.setattr(pipeline_reporting, "ROOT", pipeline.ROOT)
    monkeypatch.setattr(pipeline_reporting, "SNAPSHOTS", pipeline.ROOT / "snapshots")
    monkeypatch.setattr(cohort, "SNAPSHOTS", pipeline_reporting.SNAPSHOTS)
    calls, incomplete = [], set()

    def model_run(config):
        if config.action == "prepare":
            return {"status": "prepared"}
        calls.append(config)
        state = (
            freeze_proof_states(
                config.starting_proofs, batch["packs"], config.references
            )
            if config.starting_proofs is not None
            else None
        )
        write_json(
            config.output / "config.json",
            {
                "initial_deterministic_methods": [],
                "starting_proofs": state,
                "provider": config.provider,
                "conditions": [list(c) for c in config.conditions],
                "budget_tracking": config.budget_tracking,
                "problem_timeout_seconds": config.problem_timeout_seconds,
                "budget_usd_per_problem": config.budget_usd_per_problem,
                "names": list(batch["packs"]),
                **({"restart_history_version": 1} if config.restart_history else {}),
            },
        )
        summaries = []
        for index, (model, effort) in enumerate(config.conditions):
            complete = model not in incomplete
            proof = C if index == 0 else A
            evaluation = Evaluator().evaluate("p", proof)
            if complete:
                write_json(
                    config.output / "cells" / fingerprint(model) / "result.json",
                    {
                        "name": "p",
                        "model": model,
                        "effort": effort,
                        "status": "complete",
                        "selected_proof": proof,
                        "selected_evaluation": evaluation,
                    },
                )
            summaries.append(
                {
                    "model": model,
                    "effort": effort,
                    "complete": complete,
                    "mean_scores": (
                        evaluation["scores"] if complete else {"combined_pct": None}
                    ),
                    "mean_model_start_score": 50.0 if complete else None,
                    "mean_model_gain_pp": 10.0 if complete else None,
                }
            )
        result = {
            "status": "partial" if incomplete else "complete",
            "conditions": summaries,
        }
        write_json(config.output / "report.json", result)
        if incomplete:
            raise RuntimeError("Some cells are incomplete")
        return result

    monkeypatch.setattr(pipeline, "run_model", model_run)
    monkeypatch.setattr(pipeline, "audit_model", lambda *a: {"status": "passed"})
    monkeypatch.setattr(
        pipeline_reporting, "audit_model", lambda *a: {"status": "passed"}
    )
    config = PipelineConfig(
        model=RunConfig(
            **arguments,
            conditions=(("gpt-6.1-sol", "max"), ("gpt-6-astra", "max")),
            semantic_search=False,
            web_search=False,
        ),
        before_workers=8,
        after_workers=16,
    )
    return {"config": config, "calls": calls, "incomplete": incomplete, "batch": batch}


def test_whole_cohort_barriers_workers_and_each_models_own_final_seed(
    workflow, discovery
):
    result = run_pipeline(workflow["config"])
    output = workflow["config"].model.output
    assert result["status"] == "complete"
    assert result["wall_seconds"] > 0
    assert len(workflow["calls"]) == 1
    assert workflow["calls"][0].workers == 5
    assert workflow["calls"][0].deterministic is False
    assert workflow["calls"][0].restart_history is False
    assert read(output / "before/config.json")["workers"] == 8
    phases = result["phases"]
    assert phases["before"]["finished_epoch"] <= phases["model"]["started_epoch"]
    for item in result["conditions"]:
        key = fingerprint((item["model"], item["effort"]))
        after = read(output / "after" / key / "config.json")
        assert after["workers"] == 16
        assert (
            after["starting_proofs"]["cells"]["p"]["lineage"]["model"] == item["model"]
        )
        assert (
            phases["after_" + key]["started_epoch"] >= phases["model"]["finished_epoch"]
        )
    assert pipeline_reporting.audit_pipeline(output)["status"] == "passed"
    boundaries = {p.name: p.read_bytes() for p in (output / "phases").glob("*.json")}
    assert run_pipeline(workflow["config"]) == result
    assert len(workflow["calls"]) == 1
    assert boundaries == {
        p.name: p.read_bytes() for p in (output / "phases").glob("*.json")
    }


def test_initial_cleanup_failure_blocks_every_model_call(
    workflow, discovery, monkeypatch
):
    def failed(command, **kwargs):
        raise RuntimeError("Offline worker failure")

    monkeypatch.setattr(cohort, "run_owned_worker", failed)
    result = run_pipeline(workflow["config"])
    assert result["status"] == "incomplete"
    assert not workflow["calls"]
    assert "model" not in result["phases"]
    assert all(c["final_mean_score"] is None for c in result["conditions"])


def test_partial_model_batch_still_cleans_complete_conditions(workflow, discovery):
    workflow["incomplete"].add("gpt-6-astra")
    result = run_pipeline(workflow["config"])
    sol, astra = result["conditions"]
    assert result["status"] == "incomplete"
    assert sol["complete"] is True and astra["complete"] is False
    assert sol["selected_state"] is not None and astra["selected_state"] is None
    assert "after_" + fingerprint(("gpt-6-astra", "max")) not in result["phases"]
    prior = read(workflow["config"].model.output / "phases/before.json")
    run_pipeline(workflow["config"])
    assert read(workflow["config"].model.output / "phases/before.json") == prior


def test_timed_qwen_model_budget_starts_only_after_external_cleanup(
    workflow, discovery
):
    qwen = RunConfig(
        **workflow["batch"]["args"],
        provider="lemex",
        conditions=(("Qwen/Qwen3.8-Flash-Next", "xhigh"),),
        semantic_search=False,
        web_search=False,
    )
    result = run_pipeline(replace(workflow["config"], model=qwen))
    actual = workflow["calls"][0]
    assert actual.problem_timeout_seconds == 8 * 3600
    assert actual.workers == 5
    assert actual.starting_proofs == qwen.output / "before/state.json"
    assert actual.budget_tracking == "time" and actual.deterministic is False
    assert result["budget_scope"] == "model_phase"
    assert (
        result["phases"]["before"]["finished_epoch"]
        <= result["phases"]["model"]["started_epoch"]
    )


def test_audit_failure_cannot_be_recorded_as_success(workflow, discovery, monkeypatch):
    def fail_audit(*args):
        raise ValueError("Corrupted model evidence")

    monkeypatch.setattr(pipeline, "audit_model", fail_audit)
    with pytest.raises(ValueError, match="Corrupted model evidence"):
        run_pipeline(replace(workflow["config"], cleanup_after=False))
    output = workflow["config"].model.output
    assert read(output / "run.json")["status"] == "incomplete"
    assert "Corrupted model evidence" in read(output / "run.json")["error"]
    assert pipeline_reporting.report_pipeline(output)["status"] == "incomplete"


def test_full_pipeline_audit_failure_does_not_publish_final_means(
    workflow, discovery, monkeypatch
):
    def fail_audit(*args):
        raise ValueError("Bad final linkage")

    monkeypatch.setattr(pipeline, "audit_pipeline", fail_audit)
    with pytest.raises(ValueError, match="Bad final linkage"):
        run_pipeline(workflow["config"])
    report = read(workflow["config"].model.output / "report.json")
    assert report["status"] == "incomplete"
    assert all(c["final_mean_score"] is None for c in report["conditions"])


def test_audit_rejects_phase_overlap_and_resume_rejects_pack_tampering(
    workflow, discovery
):
    run_pipeline(workflow["config"])
    output = workflow["config"].model.output
    phase = read(output / "phases/model.json")
    phase["started_epoch"] = 0
    write_json(output / "phases/model.json", phase)
    with pytest.raises(ValueError, match="overlapped"):
        pipeline_reporting.audit_pipeline(output)
    packs = read(output / "packs.json")
    packs["p"]["row"]["proof_length"] += 1
    write_json(output / "packs.json", packs)
    with pytest.raises(ValueError, match="packs changed"):
        run_pipeline(workflow["config"])
    assert read(output / "packs.json") == packs


def test_audit_links_initial_cleanup_to_the_requested_starting_state(
    workflow, discovery, tmp_path
):
    run_pipeline(workflow["config"])
    output = workflow["config"].model.output
    source = tmp_path / "different-requested-state.json"
    export_proof_states(
        source,
        workflow["batch"]["packs"],
        workflow["config"].model.references,
        {"p": A},
        lineage={"kind": "deterministic"},
    )
    config = read(output / "config.json")
    config["starting_proofs"] = freeze_proof_states(
        source, workflow["batch"]["packs"], workflow["config"].model.references
    )
    config["model"]["starting_proofs"] = str(source)
    write_json(output / "config.json", config)
    with pytest.raises(ValueError, match="requested starting state"):
        pipeline_reporting.audit_pipeline(output)


@pytest.mark.parametrize("stage", ["before", "after"])
def test_audit_enforces_each_cleanup_worker_count(workflow, discovery, stage):
    run_pipeline(workflow["config"])
    output = workflow["config"].model.output
    folder = (
        output / "before"
        if stage == "before"
        else output / "after" / fingerprint(("gpt-6.1-sol", "max"))
    )
    config = read(folder / "config.json")
    config["workers"] += 1
    write_json(folder / "config.json", config)
    with pytest.raises(ValueError, match="workers or plan changed"):
        pipeline_reporting.audit_pipeline(output)


def test_audit_requires_the_requested_one_sweep_plan(workflow, discovery):
    run_pipeline(workflow["config"])
    output = workflow["config"].model.output
    config = read(output / "config.json")
    config["cleanup_plan"]["methods"].reverse()
    write_json(output / "config.json", config)
    with pytest.raises(ValueError, match="Unsupported pipeline accounting"):
        pipeline_reporting.audit_pipeline(output)


def test_pipeline_audit_requires_current_or_exact_archived_source_bytes(
    workflow, discovery
):
    source = pipeline.ROOT / "src/proof_eval/audit_fixture.py"
    source.parent.mkdir(parents=True)
    original = b"raise RuntimeError('a snapshot must never execute')\n"
    source.write_bytes(original)
    expected = digest(source)
    run_pipeline(workflow["config"])
    output = workflow["config"].model.output
    source.write_text("changed\n")
    with pytest.raises(ValueError, match="implementation hash changed"):
        pipeline_reporting.audit_pipeline(output)
    archived = pipeline_reporting.SNAPSHOTS / expected / source.name
    archived.parent.mkdir(parents=True)
    archived.write_bytes(original)
    assert pipeline_reporting.audit_pipeline(output)["status"] == "passed"
    archived.write_text("not the original\n")
    with pytest.raises(ValueError, match="implementation hash changed"):
        pipeline_reporting.audit_pipeline(output)
