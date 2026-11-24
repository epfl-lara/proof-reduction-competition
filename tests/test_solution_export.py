"""A valid host proof remains deliverable when native bookkeeping fails."""

import json

import pytest
from test_cleanup_cohort import batch
from test_search_exploration import A, C, Evaluator

from proof_eval.evidence.io import digest, fingerprint, read, write_json, write_jsonl
from proof_eval.evidence.solutions import publish_model_solutions
from proof_eval.harness import submission

__all__ = ["batch"]


@pytest.fixture
def saved_model(batch):
    output = batch["args"]["output"]
    model = output / "model"
    config = {
        "names": ["p"],
        "conditions": [["fixture", "max"]],
        "mode": "score_edges",
        "base_directory": str(batch["args"]["base"]),
        "base_config_sha256": digest(batch["args"]["base"] / "config.json"),
        "input_sha256": {n: fingerprint(p) for n, p in batch["packs"].items()},
        "references_path": str(batch["args"]["references"]),
        "references_sha256": digest(batch["args"]["references"]),
    }
    write_json(model / "config.json", config)
    cell = model / "cells" / fingerprint(("p", "fixture", "max", "score_edges"))
    write_json(
        cell / "input.json",
        {
            "name": "p",
            "model": "fixture",
            "effort": "max",
            "seed_proof": A,
            "seed_evaluation": Evaluator().evaluate("p", A),
        },
    )
    ledger = cell / "evidence/checks.jsonl"
    write_jsonl(
        ledger,
        [
            {
                "number": 1,
                "code": C,
                "evaluation": Evaluator().evaluate("p", C),
                "accepted": True,
                "all_versions_passed": True,
                "diagnostic": "literal\u2028separator",
            }
        ],
    )
    write_json(
        model / "run.json", {"status": "failed", "error": "native accounting failed"}
    )
    return output, model, ledger


def test_missing_native_result_does_not_withhold_best_verified_proof(saved_model):
    output, model, ledger = saved_model
    result = publish_model_solutions(model, output, ["p"])
    assert result["status"] == "ready"
    assert result["optimization_status"] == "failed"
    assert json.loads((output / "submission.jsonl").read_text()) == {
        "name": "p",
        "proof": C,
    }
    assert result["certificates"]["p"]["checks_sha256"] == digest(ledger)
    assert result["certificates"]["p"]["model_result_present"] is False
    assert not list(model.glob("cells/*/result.json"))


@pytest.mark.parametrize("damage", ["proof", "version", "references", "coverage"])
def test_invalid_or_missing_proof_certificate_blocks_complete_submission(
    saved_model, damage
):
    output, model, ledger = saved_model
    if damage == "references":
        config = read(model / "config.json")
        from pathlib import Path

        Path(config["references_path"]).write_text("changed")
    elif damage == "coverage":
        ledger.parent.parent.joinpath("input.json").unlink()
    else:
        checks = [json.loads(line) for line in ledger.read_text().split("\n") if line]
        if damage == "proof":
            checks[0]["evaluation"]["candidate"]["code_sha256"] = "changed"
        else:
            checks[0]["evaluation"]["per_version"]["v2"]["passed"] = False
        write_jsonl(ledger, checks)
    with pytest.raises((OSError, ValueError)):
        publish_model_solutions(model, output, ["p"])
    assert not (output / "submission.jsonl").exists()


@pytest.mark.parametrize("failure", ["model", "native_exit", "audit"])
def test_competition_run_returns_ready_json_and_preserves_diagnostics(
    saved_model, tmp_path, monkeypatch, failure
):
    from proof_eval.harness import cli
    from proof_eval.interfaces import local

    output, model, _ = saved_model
    bundle = tmp_path / "bundle"
    write_json(bundle / "recipe.json", {"names": ["p"]})
    monkeypatch.setattr(
        submission,
        "verify_initialization",
        lambda *a: ({"names": ["p"]}, {"identity": "fixed"}),
    )
    monkeypatch.setattr(submission, "optimization_arguments", lambda *a: [])

    def native(*args):
        if failure == "model":
            raise RuntimeError("native receipt bookkeeping failed")
        return 2 if failure == "native_exit" else 0

    def audit(*args):
        if failure == "audit":
            raise ValueError("native usage trace mismatch")
        return 0

    monkeypatch.setattr(local, "main", native)
    monkeypatch.setattr(cli, "main", audit)
    result = submission.run_submission(bundle, tmp_path / "work", output)
    assert result["status"] == "complete"
    assert json.loads((output / "submission.jsonl").read_text())["proof"] == C
    assert read(output / "submission-ready.json")["diagnostics"]
    finished = read(output / "optimization_finished.json")
    assert finished["exit_code"] == 0 and finished["submission_ready"] is True
    assert read(model / "run.json")["status"] == "failed"


def test_seed_with_no_later_check_is_exported_from_its_valid_certificate(saved_model):
    output, model, ledger = saved_model
    ledger.unlink()
    result = publish_model_solutions(model, output, ["p"])
    assert result["certificates"]["p"]["basis"] == "verified_seed"
    assert json.loads((output / "submission.jsonl").read_text())["proof"] == A


def test_active_batch_does_not_publish_a_final_submission(saved_model):
    output, model, _ = saved_model
    write_json(model / "run.json", {"status": "running"})
    with pytest.raises(ValueError, match="still active"):
        publish_model_solutions(model, output, ["p"])
    assert not (output / "submission.jsonl").exists()


def test_score_bookkeeping_does_not_withhold_a_fully_verified_proof(saved_model):
    output, model, ledger = saved_model
    checks = [json.loads(line) for line in ledger.read_text().split("\n") if line]
    checks[0]["evaluation"]["scores"]["combined_pct"] = None
    checks[0]["evaluation"]["candidate"]["length"] = -1
    write_jsonl(ledger, checks)
    assert publish_model_solutions(model, output, ["p"])["status"] == "ready"
    assert json.loads((output / "submission.jsonl").read_text())["proof"] == C


@pytest.mark.parametrize("content", ["", "theorem p : True := True.intro"])
def test_model_finishing_a_turn_does_not_stop_its_time_budget(content):
    from proof_eval.harness.tracking import stop_decision

    config = {
        "provider": "lemex-local",
        "budget_tracking": "time",
        "max_budget_restarts": 10000,
        "cleanup_reserve_seconds": 0,
    }
    generation = {"status": "received", "finish_reason": "stop", "content": content}
    assert (
        stop_decision(
            config,
            generation,
            {},
            unavailable=False,
            round_number=0,
            time_remaining=28000,
        )
        is None
    )
