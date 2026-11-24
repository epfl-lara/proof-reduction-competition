"""Small-score decisions retain all-version checks and their recorded policy."""

import json
import time
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_cleanup_cohort import batch
from test_cohort_pipeline import workflow
from test_search_exploration import ORIGINAL, ROW, A, C, Evaluator
from test_solution_export import saved_model
from test_submission_phases import release

from proof_eval.defaults import DEFAULT_SELECTION_MARGIN_PP
from proof_eval.evidence.io import digest, read, sha, write_json, write_jsonl
from proof_eval.harness import (
    configuration,
    discovery_tree,
    pipeline,
    pipeline_reporting,
)
from proof_eval.harness import submission_phases as phases
from proof_eval.harness.session import ProofSession
from proof_eval.optimization import cohort, engine, exploration
from proof_eval.optimization.cleanup import BUDGET
from proof_eval.optimization.exploration_reporting import audit_cell
from proof_eval.optimization.search_graph import SearchPlan, one_sweep_plan, plans
from proof_eval.optimization.syntax import Edit, score_improves
from proof_eval.providers.registry import DEFAULT_CONDITIONS
from proof_eval.verification.initial import measure_original

__all__ = ["batch", "saved_model", "release", "workflow"]


class SmallGainEvaluator(Evaluator):
    """Consistent fixed-reference measurements; no Lean or model execution."""

    def __init__(self, gain=0.03, invalid=None):
        super().__init__()
        self.gain, self.invalid = gain, invalid

    def evaluate(self, name, code, *, versions="all"):
        result = super().evaluate(name, code, versions=versions)
        if code == ORIGINAL:
            return result
        gain = self.gain * (2 if code == C else 1)
        length_reduction = result["scores"]["length_reduction_pct"]
        heartbeat_reduction = 3 * gain - length_reduction
        result["scores"].update(
            heartbeat_reduction_pct=heartbeat_reduction,
            compatibility_pct=100.0,
            combined_pct=100 / 3 + gain,
        )
        for check in result["per_version"].values():
            check.update(
                heartbeats=1000 * (1 - heartbeat_reduction / 100),
                heartbeat_reduction_pct=heartbeat_reduction,
            )
        if versions == "all" and self.invalid == "missing":
            del result["per_version"]["v2"]
        if versions == "all" and self.invalid == "failed":
            result["per_version"]["v2"].update(status="failed", passed=False)
        return result


@pytest.mark.parametrize("gain,accepted", [(0.01, False), (0.02, False), (0.03, True)])
def test_model_and_helper_require_a_strict_gain_above_default_margin(
    batch, tmp_path, gain, accepted
):
    evaluator = SmallGainEvaluator(gain)
    session = ProofSession(
        tmp_path / "session", batch["packs"]["p"], evaluator, "score"
    )
    before = deepcopy(session.best_evaluation)
    feedback = session.check(A)
    assert feedback["accepted_as_best"] is accepted
    assert score_improves(before, evaluator.evaluate("p", A)) is accepted
    assert session.best_code == (A if accepted else ORIGINAL)


@pytest.mark.parametrize("invalid", ["missing", "failed"])
def test_model_rejects_large_gain_without_every_required_version(
    batch, tmp_path, invalid
):
    session = ProofSession(
        tmp_path / "session",
        batch["packs"]["p"],
        SmallGainEvaluator(10, invalid),
        "score",
    )
    feedback = session.check(A)
    assert feedback["accepted_as_best"] is False
    assert feedback["all_versions_passed"] is False
    assert session.best_code == ORIGINAL


def test_generated_model_config_and_cleanup_plans_share_default(batch, monkeypatch):
    base = batch["args"]["base"]
    write_json(
        base / "config.json",
        {
            "names": ["p"],
            "code_sha256": {},
            "dataset_sha256": digest(batch["args"]["dataset"]),
            "environment_config_sha256": digest(batch["args"]["environments"]),
        },
    )
    monkeypatch.setattr(
        configuration,
        "adapter",
        lambda provider: SimpleNamespace(cli_identity=lambda: {}),
    )
    config = configuration.prepare(
        batch["args"]["output"],
        "score_edges",
        batch["packs"],
        DEFAULT_CONDITIONS["lemex-local"],
        base_directory=base,
        provider="lemex-local",
        problem_timeout_seconds=120,
        semantic_search=False,
        web_search=False,
        initial_pipeline=True,
    )
    assert config["selection_margin_pp"] == DEFAULT_SELECTION_MARGIN_PP == 0.02
    assert config["deterministic_budget"]["min_gain"] == BUDGET.min_gain == 0.02
    assert engine.Budget().min_gain == plans()["one_sweep"].budget.min_gain == 0.02
    for margin in (0.02, 0.05):
        plan = one_sweep_plan(margin)
        assert SearchPlan.from_record(plan.record()) == plan


@pytest.mark.parametrize("margin,accepted", [(0.02, True), (0.05, False)])
def test_starting_point_and_model_session_use_recorded_margin(
    batch, tmp_path, margin, accepted
):
    evaluator = SmallGainEvaluator()
    candidate = evaluator.evaluate("p", A)
    for version, check in candidate["per_version"].items():
        check["reference"] = batch["packs"]["p"]["incumbent"]["per_version"][version][
            "reference"
        ]
    pack = {**batch["packs"]["p"], "proof": A, "incumbent": candidate}
    seed, _ = configuration.starting_point(
        pack, "score_edges", selection_margin_pp=margin
    )
    assert seed == (A if accepted else ORIGINAL)
    session = ProofSession(
        tmp_path / "session",
        batch["packs"]["p"],
        evaluator,
        "score",
        selection_margin_pp=margin,
    )
    assert session.check(A)["accepted_as_best"] is accepted


def propose_small_gain(monkeypatch, parent=ORIGINAL, child=A):
    def discover(evaluator, row, code, method, budget, **kwargs):
        proposals = [[Edit(0, len(code), child, "fixture")]] if code == parent else []
        return proposals, "best_pool", {"analysis_requests": 0}

    monkeypatch.setattr(engine, "discovery", discover)


@pytest.mark.parametrize(
    "gain,margin,accepted",
    [(0.03, 0.02, True), (0.03, 0.05, False), (0.06, 0.05, True)],
)
def test_search_trace_audit_preserves_recorded_small_gain_policy(
    tmp_path, monkeypatch, batch, gain, margin, accepted
):
    evaluator = SmallGainEvaluator(gain)
    propose_small_gain(monkeypatch)
    proof, evaluation = measure_original(
        evaluator, tmp_path, batch["packs"]["p"], timeout_retries=1
    )
    result = exploration.explore(
        evaluator=evaluator,
        row=ROW,
        proof=proof,
        evaluation=evaluation,
        folder=tmp_path / "search",
        plan=SearchPlan(methods=("simp",), budget=replace(BUDGET, min_gain=margin)),
        provenance={"fixture": True},
    )
    write_json(
        tmp_path / "result.json",
        {
            **result,
            "search_sha256": digest(tmp_path / "search/result.json"),
            "measurement_sha256": digest(tmp_path / "initial_measurement.json"),
        },
    )
    assert result["proof"] == (A if accepted else ORIGINAL)
    assert audit_cell(tmp_path, ROW, batch["reference"])["status"] == "passed"


def test_legacy_cleanup_policy_remains_auditable_after_default_changes(
    batch, monkeypatch
):
    monkeypatch.setattr(cohort, "Evaluator", lambda *a, **kw: SmallGainEvaluator(0.06))
    propose_small_gain(monkeypatch)
    with monkeypatch.context() as legacy:
        legacy.setattr(cohort, "plans", lambda: {"one_sweep": one_sweep_plan(0.05)})
        assert cohort.run_cleanup(**batch["args"])["status"] == "complete"
    output = batch["args"]["output"]
    assert read(output / "config.json")["plan"]["budget"]["min_gain"] == 0.05
    assert plans()["one_sweep"].budget.min_gain == 0.02
    assert read(output / "state.json")["cells"]["p"]["proof"] == A
    assert cohort.audit_cleanup(output)["status"] == "passed"


def test_legacy_pipeline_policy_remains_auditable_after_default_changes(
    workflow, monkeypatch
):
    with monkeypatch.context() as legacy:

        def fixed():
            return {"one_sweep": one_sweep_plan(0.05)}

        legacy.setattr(cohort, "plans", fixed)
        legacy.setattr(pipeline, "plans", fixed)
        assert pipeline.run_pipeline(workflow["config"])["status"] == "complete"
    output = workflow["config"].model.output
    assert read(output / "config.json")["cleanup_plan"]["budget"]["min_gain"] == 0.05
    assert pipeline_reporting.audit_pipeline(output)["status"] == "passed"


def test_cleanup_rejects_a_cell_run_under_a_different_recorded_margin(
    batch, monkeypatch
):
    monkeypatch.setattr(cohort, "Evaluator", lambda *a, **kw: SmallGainEvaluator())
    propose_small_gain(monkeypatch)
    assert cohort.run_cleanup(**batch["args"])["status"] == "complete"
    output = batch["args"]["output"]
    config = read(output / "config.json")
    config["plan"] = one_sweep_plan(0.05).record()
    write_json(output / "config.json", config)
    folder = next((output / "cells").iterdir())
    with pytest.raises(ValueError, match="one-sweep plan changed"):
        cohort.audit_cleanup_cell(
            folder, ROW, batch["reference"], config["starting_proofs"]["cells"]["p"]
        )
    with pytest.raises(ValueError, match="incomplete"):
        cohort.audit_cleanup(output)


@pytest.mark.parametrize("invalid", ["missing", "failed"])
def test_cleanup_rejects_large_gain_without_every_required_version(
    batch, monkeypatch, invalid
):
    monkeypatch.setattr(
        cohort, "Evaluator", lambda *a, **kw: SmallGainEvaluator(10, invalid)
    )
    propose_small_gain(monkeypatch)
    result = cohort.run_cleanup(**batch["args"])
    assert result["status"] == "complete"
    assert (
        read(batch["args"]["output"] / "state.json")["cells"]["p"]["proof"] == ORIGINAL
    )
    assert cohort.audit_cleanup(batch["args"]["output"])["status"] == "passed"


@pytest.mark.parametrize("interrupted", [False, True])
def test_small_cleanup_gain_survives_audits_recovery_and_final_jsonl(
    release, batch, monkeypatch, interrupted
):
    from proof_eval.providers import host_support

    monkeypatch.setattr(host_support, "require_supported", lambda *a: {"fixture": True})
    bundle, work, output, _ = release
    model = batch["args"]["output"] / "model"
    cell = next((model / "cells").iterdir())
    evaluator = SmallGainEvaluator()
    write_json(
        cell / "input.json",
        {
            "name": "p",
            "model": "fixture",
            "effort": "max",
            "seed_proof": ORIGINAL,
            "seed_evaluation": evaluator.evaluate("p", ORIGINAL),
        },
    )
    write_jsonl(
        cell / "evidence/checks.jsonl",
        [
            {
                "number": 1,
                "code": A,
                "evaluation": evaluator.evaluate("p", A),
                "accepted": True,
                "all_versions_passed": True,
            }
        ],
    )
    phases.search(bundle, work, output)
    assert json.loads((output / "model-submission.jsonl").read_text())["proof"] == A
    monkeypatch.setattr(cohort, "Evaluator", lambda *a, **kw: SmallGainEvaluator())
    propose_small_gain(monkeypatch, A, C)
    execute = cohort.run_owned_worker

    def finish_then_interrupt(*args, **kwargs):
        execute(*args, **kwargs)
        raise RuntimeError("fixture worker loss after saving verified small gain")

    if interrupted:
        monkeypatch.setattr(cohort, "run_owned_worker", finish_then_interrupt)
    final = phases.cleanup(bundle, work, output)
    assert final["cleanup_completed"] is True
    assert final["audit"]["status"] == "passed"
    assert json.loads((output / "submission.jsonl").read_text()) == {
        "name": "p",
        "proof": C,
    }
    result = read(next((output / "cleanup/cells").iterdir()) / "result.json")
    assert bool(result.get("fallback")) is interrupted
    assert result["gain_pp"] == pytest.approx(0.03)


def test_discovery_replay_uses_saved_margin(batch, tmp_path):
    evaluator = SmallGainEvaluator()
    folder = tmp_path / "cell"
    session = ProofSession(folder / "evidence", batch["packs"]["p"], evaluator, "score")
    session.check(A)
    write_json(
        folder / "result.json",
        {
            "name": "p",
            "model": "fixture",
            "effort": "max",
            "status": "complete",
            "seed_evaluation": evaluator.evaluate("p", ORIGINAL),
            "before_final_cleanup": {"evaluation": session.best_evaluation},
        },
    )
    epoch = time.time()
    write_json(
        folder / "attempt_00/attempt.json",
        {
            "number": 0,
            "check_start": 0,
            "check_end": 1,
            "started_epoch": epoch - 10,
            "ended_epoch": epoch + 10,
            "incumbent_sha256": sha(ORIGINAL),
            "incumbent_evaluation": evaluator.evaluate("p", ORIGINAL),
        },
    )
    config = {"schema_version": 8, "selection_margin_pp": 0.02}
    tree = discovery_tree._load_cell(
        folder, config, discovery_tree.EvidenceReader(), allow_incomplete=False
    )
    assert tree.recorded_raw_pct == evaluator.evaluate("p", A)["scores"]["combined_pct"]
    with pytest.raises(ValueError, match="margin contract"):
        discovery_tree._load_cell(
            folder,
            {**config, "selection_margin_pp": 0.05},
            discovery_tree.EvidenceReader(),
            allow_incomplete=False,
        )
