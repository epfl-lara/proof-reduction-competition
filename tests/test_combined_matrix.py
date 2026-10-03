"""Offline all-version gating, fixed cleanup, streaming dedup, and resumability."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from proof_eval.experiments import optimize
from proof_eval.one_shot import fingerprint
from proof_eval.optimizer import Edit
from proof_eval.metrics import validate_candidate
from run_combined_matrix import (AllVersionsEvaluator, BUDGET, METHODS, cleanup_proof, job_key,
                                 prepare, read, require_valid, run, select_cell, sha)
from run_deterministic import digest


CODE = "theorem p : True := by trivial"
OTHER = "theorem p : True := by exact True.intro"
BEST = "theorem p : True := True.intro"
ROW = {"name": "p", "source": "fixture", "statement": "theorem p : True", "version_info": [{"v1": "rev1"}, {"v2": "rev2"}]}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def evaluation(proof=CODE, value=60, compatible=True):
    return {"status": "passed", "primary_version": "v1", "candidate": {"code_sha256": sha(validate_candidate(ROW, proof)[0]), "length": 10},
            "scores": {"combined_pct": value, "length_reduction_pct": value,
                       "heartbeat_reduction_pct": value, "compatibility_pct": 100 if compatible else 50},
            "per_version": {v: {"status": "passed" if v == "v1" or compatible else "failed",
                                "passed": v == "v1" or compatible, "diagnostics": [], "cached": True}
                            for v in ("v1", "v2")}}


class FakeEvaluator:
    def __init__(self, pack=None, values=None):
        self.pack, self.values, self.calls, self.changed = pack, values or {}, [], False

    def evaluate(self, name, code, *, versions="all"):
        self.calls.append((name, code, versions))
        result = deepcopy(self.values.get(code, evaluation(code)))
        if versions == "primary":
            result["per_version"] = {"v1": result["per_version"]["v1"]}
        return result

    def get_reference(self, name):
        values = {v: {"status": "prepared", **deepcopy(item["reference"])}
                  for v, item in self.pack["incumbent"]["per_version"].items()}
        if self.changed:
            values["v1"]["heartbeats"] += 1
        return {"versions": values}

    def _context(self, row, version):
        return None, None, "context_" + version


def test_adapter_gates_only_full_checks_and_keeps_authoritative_evidence():
    raw = evaluation(OTHER, 90, False)
    fake = FakeEvaluator(values={OTHER: raw})
    events = []
    adapter = AllVersionsEvaluator(fake, ["v1", "v2"], events.append)
    assert adapter.evaluate("p", OTHER, versions="primary")["status"] == "passed"
    assert not events
    gated = adapter.evaluate("p", OTHER)
    assert gated["status"] == "policy_compatibility_rejected"
    assert gated["scores"] == raw["scores"] and gated["per_version"] == raw["per_version"]
    assert raw["status"] == events[0]["evaluation"]["status"] == "passed"
    assert events[0]["eligible"] is False
    assert events[0]["authoritative_status"] == "passed"
    assert adapter.calls is fake.calls
    missing = evaluation(OTHER)
    missing["per_version"].pop("v2")
    fake.values[OTHER] = missing
    assert adapter.evaluate("p", OTHER)["status"] == "policy_compatibility_rejected"


def test_frozen_optimizer_cannot_accept_higher_score_with_failed_version(monkeypatch):
    import proof_eval.experiments as experiments
    def discover(evaluator, row, code, method, budget, **kwargs):
        groups = [[Edit(0, len(code), OTHER, "partial")], [Edit(0, len(code), BEST, "valid")]] if code == CODE else []
        return groups, "best_pool", {"analysis_requests": 0}
    monkeypatch.setattr(experiments, "discovery", discover)
    fake = FakeEvaluator(values={CODE: evaluation(CODE, 50), OTHER: evaluation(OTHER, 90, False), BEST: evaluation(BEST, 60)})
    policies, trials = [], []
    result = optimize(AllVersionsEvaluator(fake, ["v1", "v2"], policies.append), ROW, CODE, "lint",
                      BUDGET, trials.append, lambda state: None)
    assert result["proof"] == BEST
    partial_trial = next(t for t in trials if t.get("proof") == OTHER)
    assert partial_trial["improves_incumbent"] is False
    assert partial_trial["evaluation"]["status"] == "policy_compatibility_rejected"


def fake_method(evaluator, row, initial, method, budget, emit, save, state=None):
    result = evaluation(initial)
    return {"name": row["name"], "source": row["source"], "method": method, "proof": initial,
            "initial": result, "final": result, "stop_reason": "no_new_proposals", "attempts": 1,
            "analysis_requests": 1, "lean_candidate_checks": 0, "cache_hits": 1,
            "accepted_transitions": 0, "elapsed_seconds": 0.5}


def test_cleanup_resumes_exact_method_checkpoint_and_cached_job_without_calls(tmp_path):
    fake = FakeEvaluator()
    calls = []
    crashed = False
    def method(*args, state=None):
        nonlocal crashed
        method_name, budget, save = args[3], args[4], args[6]
        calls.append((method_name, state))
        assert budget == BUDGET
        if method_name == "facts" and not crashed:
            crashed = True
            save({"cursor": "pending_trial"})
            raise RuntimeError("simulated interruption")
        if method_name == "facts":
            assert state == {"cursor": "pending_trial"}
        return fake_method(*args, state=state)
    kwargs = dict(evaluator=fake, row=ROW, proof=CODE, folder=tmp_path / "job", provenance={"frozen": "pins"}, optimize_fn=method)
    with pytest.raises(RuntimeError, match="interruption"):
        cleanup_proof(**kwargs)
    result = cleanup_proof(**kwargs)
    assert result["status"] == "complete"
    assert [stage["method"] for stage in result["stages"]] == list(METHODS)
    assert result["counters"]["attempts"] == 10
    assert len(calls) == 11  # One interrupted method resumes, prior methods do not replay.
    before = len(fake.calls), len(calls)
    assert cleanup_proof(**kwargs) == result
    assert (len(fake.calls), len(calls)) == before
    with pytest.raises(ValueError, match="configuration changed"):
        cleanup_proof(**{**kwargs, "provenance": {"frozen": "different"}})


def test_unavailable_discovery_is_explicitly_incomplete(tmp_path):
    def method(*args, **kwargs):
        result = fake_method(*args, **kwargs)
        if result["method"] == "menu":
            result["stop_reason"] = "discovery_unavailable"
        return result
    result = cleanup_proof(evaluator=FakeEvaluator(), row=ROW, proof=CODE, folder=tmp_path,
                           provenance={}, optimize_fn=method)
    assert result["status"] == "incomplete_discovery"
    assert result["incomplete_methods"] == ["menu"]
    assert result["all_versions_valid"]


def test_proof_identity_uses_evaluator_normalization_but_dedup_uses_raw_bytes():
    spaced = "theorem p : True :=\n  by trivial\n"
    require_valid(evaluation(spaced), ROW, spaced)
    assert job_key("p", spaced) != job_key("p", CODE)


def test_selection_preserves_prior_small_gain_and_control_ties():
    pack = {"name": "p", "row": ROW, "proof": CODE, "incumbent": evaluation(CODE, 60)}
    repair = {"selected_proof": OTHER, "selected_evaluation": evaluation(OTHER, 60.09),
              "final_valid": True, "final_proof": OTHER, "final_evaluation": evaluation(OTHER, 60.09),
              "accepted": True, "returned_incumbent": False}
    control = {"proof": CODE, "evaluation": evaluation(CODE, 60.08), "status": "complete"}
    proposal = {"proof": OTHER, "evaluation": evaluation(OTHER, 60.09), "status": "complete"}
    kwargs = dict(cell={"key": "cell", "logical": ["p", "plain", "model"]}, pack=pack,
                  repair=repair, snapshot={}, control=control, proposal=proposal)
    selected = select_cell(**kwargs)
    assert selected["selected_from"] == "l"
    control["evaluation"] = evaluation(CODE, 60.09)
    assert select_cell(**kwargs)["selected_from"] == "d1"
    repair.update(selected_proof=CODE, selected_evaluation=pack["incumbent"], accepted=False,
                  final_evaluation=evaluation(OTHER, 59))
    proposal.update(proof=BEST, evaluation=evaluation(BEST, 61))
    selected = select_cell(**kwargs)
    assert selected["rescued_vs_d0"] and selected["rescued_vs_d1"]
    assert selected["selected_from"] == "cleaned_f"
    control["evaluation"] = evaluation(CODE, 60)
    proposal["evaluation"] = evaluation(BEST, 60.03)
    selected = select_cell(**kwargs)
    assert not selected["rescued_vs_d1"]
    assert selected["selected_from"] == "d1"


@pytest.fixture
def matrix_fixture(tmp_path):
    base, repair = tmp_path / "base", tmp_path / "repair"
    dataset, environments = tmp_path / "dataset", tmp_path / "environments"
    dataset.write_text("fixture dataset")
    environments.write_text("fixture environments")
    incumbent = evaluation()
    for version, item in incumbent["per_version"].items():
        item["reference"] = {"measured_at": "frozen", "heartbeats": 10, "heartbeats_raw": 10000,
                             "environment_fingerprint": version, "reference_code_sha256": "reference"}
    pack = {"name": "p", "row": ROW, "proof": CODE, "incumbent": incumbent}
    config = {"names": ["p"], "models": ["model"], "arms": ["plain", "goals", "cards"], "code_sha256": {},
              "dataset_sha256": digest(dataset), "environment_config_sha256": digest(environments),
              "contexts": {"p": {v: "context_" + v for v in ("v1", "v2")}}}
    write(base / "config.json", config)
    write(base / "inputs/p.json", pack)
    write(base / "input_hashes.json", {"p": fingerprint(pack)})
    index, cells, records = {}, [], {}
    for arm in config["arms"]:
        logical = ["p", arm, "model"]
        key = fingerprint(logical)
        index[json.dumps(logical)] = key
        cells.append({"key": key, "logical": logical})
        proof = CODE if arm == "plain" else OTHER
        records[key] = {"name": "p", "source": "fixture", "model": "model", "arm": arm,
            "base_request_sha256": key, "final_valid": True, "final_proof": proof,
            "final_evaluation": evaluation(proof, 59 if proof == OTHER else 60), "selected_proof": CODE,
            "selected_evaluation": incumbent, "accepted": False, "returned_incumbent": proof == CODE}
        write(repair / "cells" / key / "cell_config.json", {"input_sha256": fingerprint(pack)})
    write(base / "cell_index.json", index)
    prior = {"base_directory": str(base), "base_config_sha256": digest(base / "config.json"),
             "base_index_sha256": digest(base / "cell_index.json"), "base_input_hashes_sha256": digest(base / "input_hashes.json"),
             "input_files_sha256": {"inputs/p.json": digest(base / "inputs/p.json")},
             "input_sha256": {"p": fingerprint(pack)}, "cells": cells, "code_sha256": {}}
    write(repair / "matrix_config.json", prior)
    write(repair / "run.json", {"status": "running"})
    args = SimpleNamespace(input=repair, output=tmp_path / "combined", dataset=dataset,
                           environments=environments, cache=tmp_path / "cache", workers=2, watch=True, poll_seconds=0.001)
    return args, pack, records


def arrive(args, records):
    for key, record in records.items():
        write(args.input / "cells" / key / "result.json", record)


def fake_cleanup(**kwargs):
    return cleanup_proof(**kwargs, optimize_fn=fake_method)


def test_matrix_cleans_score_rejected_finals_deduplicates_and_resumes(matrix_fixture):
    args, pack, records = matrix_fixture
    arrive(args, records)
    write(args.input / "run.json", {"status": "complete"})
    evaluator = FakeEvaluator(pack)
    result = run(args, evaluator=evaluator, cleanup_fn=fake_cleanup)
    assert result["status"] == "complete"
    assert result["recorded_cells"] == 3 and result["recorded_controls"] == 1
    assert result["unique_cleanup_jobs"] == 2  # Control/returned original shared; both other arms share F.
    jobs = read(args.output / "jobs.json")["jobs"]
    assert len(jobs[job_key("p", CODE)]["origins"]) == 2
    assert len(jobs[job_key("p", OTHER)]["origins"]) == 2
    assert all(read(args.output / "cells" / key / "result.json")["proposal_job_key"] for key in records)
    before = len(evaluator.calls)
    assert run(args, evaluator=evaluator, cleanup_fn=fake_cleanup)["status"] == "complete"
    assert len(evaluator.calls) == before


def test_matrix_waits_streams_and_terminal_partial_is_resumable(matrix_fixture):
    args, pack, records = matrix_fixture
    first = next(iter(records))
    arrive(args, {first: records[first]})
    write(args.input / "run.json", {"status": "interrupted"})
    assert run(args, evaluator=FakeEvaluator(pack), cleanup_fn=fake_cleanup)["status"] == "incomplete_repair_terminal"
    write(args.input / "run.json", {"status": "running"})
    waits = []
    def on_wait(seconds):
        waits.append(seconds)
        arrive(args, records)
        write(args.input / "run.json", {"status": "complete"})
    assert run(args, evaluator=FakeEvaluator(pack), cleanup_fn=fake_cleanup, sleep=on_wait)["status"] == "complete"
    assert waits == [args.poll_seconds]


def test_matrix_refuses_changed_references_inputs_and_arrived_results(matrix_fixture):
    args, pack, records = matrix_fixture
    evaluator = FakeEvaluator(pack)
    evaluator.changed = True
    with pytest.raises(ValueError, match="Cached reference changed"):
        run(args, evaluator=evaluator, cleanup_fn=fake_cleanup)
    assert not evaluator.calls
    arrive(args, records)
    run(args, evaluator=FakeEvaluator(pack), cleanup_fn=fake_cleanup)
    first = next(iter(records))
    records[first]["accepted"] = True
    arrive(args, {first: records[first]})
    with pytest.raises(ValueError, match="Saved repair cell changed"):
        run(args, evaluator=FakeEvaluator(pack), cleanup_fn=fake_cleanup)
    config = read(args.input / "matrix_config.json")
    config["cells"].pop()
    write(args.input / "matrix_config.json", config)
    with pytest.raises(ValueError, match="complete base cohort"):
        prepare(args)


def test_immutable_budget_is_exact():
    assert asdict(BUDGET) == {"rounds": 3, "trials": 32, "sites": 6, "min_gain": 0.05}
    assert len(METHODS) == 10
