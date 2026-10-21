"""Explicit checkpoint lineage, fresh startup checks, resume and track boundaries."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from test_budget_tracking import fake_native
from test_initial_pipeline import fresh_backend, tracking_run
from test_search_exploration import ROW, SearchPlan, discovery
from test_search_exploration import run as explore

from proof_eval.evidence.io import digest, read, write_json
from proof_eval.harness.audit import audit
from proof_eval.harness.budget import run_cell
from proof_eval.harness.checkpoint import freeze_checkpoint
from proof_eval.harness.config import RunConfig
from proof_eval.protocol import code_identity

__all__ = ["discovery", "tracking_run"]


@pytest.mark.parametrize(
    "settings",
    [
        {"deterministic": True},
        {"deterministic": False, "problem_timeout_seconds": 3600},
        {"deterministic": False, "budget_tracking": "time"},
        {"deterministic": False, "provider": "lemex", "budget_tracking": "cost"},
    ],
)
def test_checkpoint_rejects_ambiguous_or_timed_conditions(settings):
    with pytest.raises(ValueError, match="checkpoint"):
        RunConfig(deterministic_checkpoint=Path("source"), **settings)


def test_freeze_requires_complete_audited_model_free_lineage(tmp_path, discovery):
    source = tmp_path / "source"
    folder = source / "cells/p"
    result, _, _ = explore(folder, SearchPlan(methods=("simp",), strategy="sweep"))
    path = folder / "result.json"
    saved = read(path)
    saved["name"] = "p"
    write_json(path, saved)
    reference = {
        "name": "p",
        "per_version": {
            v: {
                "heartbeats": 1000,
                "provenance": {"environment_fingerprint": "env_" + v},
            }
            for v in ("v1", "v2")
        },
    }
    refs = tmp_path / "refs.jsonl"
    refs.write_text(json.dumps(reference) + "\n")
    packs = {"p": {"row": ROW}}
    frozen = freeze_checkpoint(source, packs, refs)
    assert frozen["cells"]["p"]["proof"] == result["proof"]
    assert frozen["cells"]["p"]["audit"]["status"] == "passed"
    with pytest.raises(ValueError, match="complete declared cohort"):
        freeze_checkpoint(source, {**packs, "missing": {}}, refs)
    saved["proof"] = ROW["src"]
    write_json(path, saved)
    with pytest.raises(ValueError, match="summary disagrees"):
        freeze_checkpoint(source, packs, refs)


def test_checkpoint_is_fresh_initial_model_input_and_gain_is_audited(
    tracking_run, monkeypatch, tmp_path
):
    run = tracking_run(initial_pipeline=True, cleanup=False, usd=0.1, timeout=None)
    fresh_backend(run, monkeypatch)
    proof = run.saved["selected_proof"]
    source = tmp_path / "source.json"
    write_json(source, {"proof": proof})
    # Source graph audit is covered separately above; use a saved real certificate
    # to exercise the complete native harness and its proof ledger offline.
    item = {
        "source_result": str(source),
        "source_sha256": digest(source),
        "proof": proof,
        "proof_sha256": code_identity(run.pack["row"], proof),
        "source_score": run.saved["selected_evaluation"]["scores"]["combined_pct"],
    }
    run.config["deterministic_checkpoint"] = {
        "version": 1,
        "cells": {run.pack["name"]: item},
    }
    write_json(run.output / "config.json", run.config)
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
    assert result["model_start_score"] == item["source_score"]
    candidate = read(run.folder / "attempt_00/workspace/initial_candidate.json")
    assert candidate["proof"] == proof
    assert audit(run.output)["status"] == "passed"
    boundary = (run.folder / "initial_phase.json").read_bytes()
    # A completed cell is reusable without measurement or another model call.
    assert (
        run_cell(run.output, run.config, run.pack, run.model, run.effort, run.evaluator)
        == result
    )
    assert (run.folder / "initial_phase.json").read_bytes() == boundary
    tampered = deepcopy(result)
    tampered["model_gain_pp"] += 1
    write_json(run.folder / "result.json", tampered)
    with pytest.raises(ValueError, match="model gain"):
        audit(run.output)


def test_interrupted_checkpoint_is_not_automatically_rechecked(
    tracking_run, monkeypatch, tmp_path
):
    from proof_eval.harness.checkpoint import adopt_checkpoint
    from proof_eval.harness.session import ProofSession

    run = tracking_run(initial_pipeline=True, cleanup=False, timeout=None)
    source = tmp_path / "source.json"
    write_json(source, {})
    proof = run.saved["selected_proof"]
    run.config["deterministic_checkpoint"] = {
        "cells": {
            run.pack["name"]: {
                "source_result": str(source),
                "source_sha256": digest(source),
                "proof": proof,
                "proof_sha256": code_identity(run.pack["row"], proof),
            }
        }
    }
    session = ProofSession(
        run.folder / "evidence", run.pack, run.evaluator, "score_edges"
    )
    write_json(run.folder / "checkpoint_started.json", {"started_epoch": 1})
    with pytest.raises(ValueError, match="Indeterminate checkpoint"):
        adopt_checkpoint(session, run.folder, run.config)
    assert session.checks == []
