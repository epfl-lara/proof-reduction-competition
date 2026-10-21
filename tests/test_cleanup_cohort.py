"""Cleanup phase ordering, verified arbitrary seeds, isolation and safe resume."""

import json
import subprocess
from pathlib import Path

import pytest
from test_search_exploration import ROW, A, B, C, Evaluator, discovery

from proof_eval.evidence.io import fingerprint, read, write_json
from proof_eval.evidence.proof_states import export_proof_states, freeze_proof_states
from proof_eval.optimization import cohort

__all__ = ["discovery"]


@pytest.fixture
def batch(tmp_path, monkeypatch):
    packs = {"p": {"name": "p", "row": ROW}}
    base = tmp_path / "base"
    write_json(base / "config.json", {"names": ["p"]})
    write_json(base / "inputs/p.json", packs["p"])
    dataset, environments, references = [
        tmp_path / n for n in ("data.jsonl", "environments.json", "references.jsonl")
    ]
    dataset.write_text(json.dumps(ROW) + "\n")
    environments.write_text("{}")
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
    references.write_text(json.dumps(reference) + "\n")
    monkeypatch.setattr(cohort, "ROOT", tmp_path / "runtime")
    monkeypatch.setattr(cohort, "Evaluator", lambda *a, **kw: Evaluator())
    monkeypatch.setattr(cohort, "private_evaluator", lambda evaluator, *a: evaluator)
    monkeypatch.setattr(cohort, "check_references", lambda *a: None)
    requests = []

    def execute(command, **kwargs):
        request = Path(command[-1])
        requests.append((request, kwargs))
        cohort._cell(request)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(cohort, "run_owned_worker", execute)
    return {
        "args": {
            "output": tmp_path / "output",
            "base": base,
            "dataset": dataset,
            "environments": environments,
            "references": references,
            "cache": tmp_path / "cache",
        },
        "packs": packs,
        "reference": reference,
        "requests": requests,
    }


def test_one_sweep_exports_audited_state_and_completed_resume_does_no_work(
    batch, discovery
):
    report = cohort.run_cleanup(**batch["args"], workers=16)
    assert report["status"] == "complete"
    assert report["expected"] == report["completed"] == 1
    assert report["workers"] == 16
    assert report["mean_gain_pp"] > 0
    assert report["elapsed_seconds"] >= report["sum_cell_seconds"] > 0
    output = batch["args"]["output"]
    assert cohort.audit_cleanup(output)["status"] == "passed"
    config = read(output / "config.json")
    assert config["plan"] == cohort.plans()["one_sweep"].record()
    assert config["overall_wall_seconds"] is None
    state = freeze_proof_states(
        output / "state.json", batch["packs"], batch["args"]["references"]
    )
    assert state["cells"]["p"]["proof"] == A
    assert state["cells"]["p"]["lineage"] == {
        "kind": "deterministic",
        "origin_kind": "original",
    }
    assert len(batch["requests"]) == 1
    assert isinstance(batch["requests"][0][1]["lock_fd"], int)
    assert cohort.run_cleanup(**batch["args"], workers=16) == report
    assert len(batch["requests"]) == 1


def test_post_model_cleanup_uses_its_seed_and_preserves_model_lineage(
    batch, discovery, tmp_path
):
    source = tmp_path / "model.json"
    export_proof_states(
        source,
        batch["packs"],
        batch["args"]["references"],
        {"p": {"proof": B, "model": "sol", "effort": "max"}},
    )
    result = cohort.run_cleanup(
        **batch["args"], starting_proofs=source, condition=("sol", "max")
    )
    assert result["status"] == "complete"
    folder = batch["args"]["output"] / "cells" / fingerprint("p")
    assert read(folder / "seed.json")["proof"] == B
    assert read(folder / "result.json")["proof"] == C
    assert (
        read(batch["args"]["output"] / "state.json")["cells"]["p"]["lineage"]["model"]
        == "sol"
    )
    with pytest.raises(ValueError, match="another model condition"):
        freeze_proof_states(
            batch["args"]["output"] / "state.json",
            batch["packs"],
            batch["args"]["references"],
            condition=("qwen", "max"),
        )


def test_failed_cell_does_not_cancel_others_or_get_replayed(
    batch, discovery, monkeypatch
):
    args, packs = batch["args"], batch["packs"]
    packs["q"] = {"name": "q", "row": {**ROW, "name": "q"}}
    write_json(args["base"] / "inputs/q.json", packs["q"])
    write_json(args["base"] / "config.json", {"names": ["p", "q"]})
    args["references"].write_text(
        args["references"].read_text()
        + json.dumps({**batch["reference"], "name": "q"})
        + "\n"
    )
    original = cohort.run_owned_worker

    def execute(command, **kwargs):
        if read(Path(command[-1]))["name"] == "p":
            batch["requests"].append((Path(command[-1]), kwargs))
            raise subprocess.CalledProcessError(1, command)
        return original(command, **kwargs)

    monkeypatch.setattr(cohort, "run_owned_worker", execute)
    result = cohort.run_cleanup(**args, workers=1)
    assert result["status"] == "incomplete"
    assert result["completed"] == 1
    assert result["mean_output_score"] is None
    assert not (args["output"] / "state.json").exists()
    assert len(batch["requests"]) == 2
    assert cohort.run_cleanup(**args, workers=1)["status"] == "incomplete"
    assert len(batch["requests"]) == 2


def test_indeterminate_cell_and_tampered_export_are_rejected(batch, discovery):
    args = batch["args"]
    cohort.run_cleanup(**args, prepare_only=True)
    folder = args["output"] / "cells" / fingerprint("p")
    write_json(folder / "started.json", {"epoch": 1, "name": "p"})
    assert cohort.run_cleanup(**args)["status"] == "incomplete"
    assert not batch["requests"]
    assert "not replayed" in read(args["output"] / "run.json")["failures"][0]["error"]


@pytest.mark.parametrize("workers", [0, -1, True, 1.5])
def test_worker_count_is_positive_integer(batch, workers):
    with pytest.raises(ValueError, match="positive integer"):
        cohort.run_cleanup(**batch["args"], workers=workers)


def test_audit_detects_replaced_search_root(batch, discovery):
    cohort.run_cleanup(**batch["args"])
    folder = batch["args"]["output"] / "cells" / fingerprint("p")
    seed = read(folder / "seed.json")
    seed["proof"] = B
    write_json(folder / "seed.json", seed)
    with pytest.raises(ValueError, match="incomplete"):
        cohort.audit_cleanup(batch["args"]["output"])


def test_cohort_interruption_cancels_admission_and_keeps_terminal_evidence(
    batch, monkeypatch
):
    args, packs = batch["args"], batch["packs"]
    for name in ("q", "r", "s"):
        packs[name] = {"name": name, "row": {**ROW, "name": name}}
        write_json(args["base"] / "inputs" / (name + ".json"), packs[name])
    write_json(args["base"] / "config.json", {"names": list(packs)})
    args["references"].write_text(
        "".join(
            json.dumps({**batch["reference"], "name": name}) + "\n" for name in packs
        )
    )
    admitted = []

    def waiting(command, *, cancellation, **kwargs):
        admitted.append(read(Path(command[-1]))["name"])
        assert cancellation.wait(2), "Coordinator failed to cancel its workers"
        raise RuntimeError("Cancelled owned worker")

    def interrupt(futures):
        raise KeyboardInterrupt

    monkeypatch.setattr(cohort, "run_owned_worker", waiting)
    monkeypatch.setattr(cohort, "as_completed", interrupt)
    with pytest.raises(KeyboardInterrupt):
        cohort.run_cleanup(**args, workers=1)
    assert len(admitted) <= 1
    terminal = read(args["output"] / "run.json")
    assert terminal["status"] == "incomplete"
    assert terminal["error"].startswith("KeyboardInterrupt")
    assert not (args["output"] / "state.json").exists()
