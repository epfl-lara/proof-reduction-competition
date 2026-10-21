"""Explicit proof-state reuse is fresh, condition-scoped and budgeted as model work."""

from copy import deepcopy
from pathlib import Path

import pytest
from test_budget_tracking import fake_native
from test_initial_pipeline import fresh_backend, tracking_run

from proof_eval.evidence.io import read, write_json
from proof_eval.evidence.proof_states import export_proof_states, freeze_proof_states
from proof_eval.harness.audit import audit
from proof_eval.harness.budget import run_cell
from proof_eval.harness.config import RunConfig
from proof_eval.harness.configuration import load_inputs
from proof_eval.harness.session import ProofSession
from proof_eval.harness.starting import adopt_starting_proof
from proof_eval.paths import ROOT

__all__ = ["tracking_run"]


def select_state(run, tmp_path, *, original=False):
    references = (
        ROOT / "results/deterministic/00_reference_baseline/reference_values.jsonl"
    )
    packs = load_inputs()
    records = {name: pack["row"]["src"] for name, pack in packs.items()}
    if not original:
        records[run.pack["name"]] = run.saved["selected_proof"]
    source = tmp_path / "state.json"
    export_proof_states(
        source, packs, references, records, lineage={"kind": "deterministic"}
    )
    run.config.update(
        starting_proofs=freeze_proof_states(source, packs, references),
        references_path=str(references),
        seed="fresh_original_then_explicit_state",
        model_phase_version=1,
    )
    write_json(run.output / "config.json", run.config)


@pytest.mark.parametrize("tracking,timeout", [("cost", None), ("time", 30)])
def test_explicit_state_is_fresh_model_input_and_auditable(
    tracking_run, monkeypatch, tmp_path, tracking, timeout
):
    run = tracking_run(
        initial_pipeline=True,
        cleanup=False,
        tracking=tracking,
        timeout=timeout,
        usd=0.1,
        restarts=0,
    )
    fresh_backend(run, monkeypatch)
    select_state(run, tmp_path)
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
    assert result["model_gain_pp"] == 0
    assert (
        result["model_start_score"]
        == run.saved["selected_evaluation"]["scores"]["combined_pct"]
    )
    assert result["phase_accounting"] == "model_only_external_cleanup_excluded"
    saved = read(run.folder / "starting_proof.json")
    assert saved["adopted"]
    assert (
        read(run.folder / "attempt_00/workspace/initial_candidate.json")["proof"]
        == run.saved["selected_proof"]
    )
    assert audit(run.output)["status"] == "passed"
    before = (run.folder / "starting_proof.json").read_bytes()
    assert (
        run_cell(run.output, run.config, run.pack, run.model, run.effort, run.evaluator)
        == result
    )
    assert (run.folder / "starting_proof.json").read_bytes() == before
    changed = deepcopy(result)
    changed["model_gain_pp"] += 1
    write_json(run.folder / "result.json", changed)
    with pytest.raises(ValueError, match="model gain"):
        audit(run.output)


def test_original_selected_state_reuses_same_phase_fresh_measurement(
    tracking_run, monkeypatch, tmp_path
):
    run = tracking_run(initial_pipeline=True, cleanup=False, timeout=None, usd=0.1)
    fresh_backend(run, monkeypatch)
    select_state(run, tmp_path, original=True)
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
    saved = read(run.folder / "starting_proof.json")
    assert saved["original_measurement_reused"] and not saved["adopted"]
    assert audit(run.output)["status"] == "passed"


def test_interrupted_selected_measurement_is_never_replayed(tracking_run, tmp_path):
    run = tracking_run(initial_pipeline=True, cleanup=False, timeout=None)
    select_state(run, tmp_path)
    session = ProofSession(
        run.folder / "evidence", run.pack, run.evaluator, "score_edges"
    )
    write_json(run.folder / "starting_proof_started.json", {"started_epoch": 1})
    with pytest.raises(ValueError, match="Indeterminate starting-proof"):
        adopt_starting_proof(session, run.folder, run.config)
    assert not session.checks


def test_model_defaults_and_qwen_phase_budget():
    sol = RunConfig()
    assert not sol.restart_history and not sol.deterministic
    qwen = RunConfig(
        provider="lemex",
        conditions=(("Qwen/Qwen3.8-Flash-Next", "xhigh"),),
        starting_proofs=Path("state.json"),
    )
    assert qwen.problem_timeout_seconds == 14400 and qwen.workers == 5
    assert RunConfig(workers=16).workers == 16
    historical_timeout = RunConfig(
        provider="lemex", conditions=qwen.conditions, problem_timeout_seconds=3420
    )
    assert historical_timeout.problem_timeout_seconds == 3420
    with pytest.raises(ValueError, match="cohort pipeline"):
        RunConfig(deterministic=True)
    with pytest.raises(ValueError, match="positive integer"):
        RunConfig(workers=0)
