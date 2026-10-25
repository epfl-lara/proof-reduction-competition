"""Offline all-version gating, fixed cleanup, streaming dedup, and resumability."""

import json
from copy import deepcopy
from dataclasses import asdict

import pytest

from proof_eval.optimization.cleanup import (
    BUDGET,
    METHODS,
    AllVersionsEvaluator,
    cleanup_proof,
    sha,
)
from proof_eval.optimization.engine import optimize
from proof_eval.optimization.syntax import Edit
from proof_eval.verification.metrics import validate_candidate

CODE = "theorem p : True := by trivial"
OTHER = "theorem p : True := by exact True.intro"
BEST = "theorem p : True := True.intro"
ROW = {
    "name": "p",
    "source": "fixture",
    "statement": "theorem p : True",
    "version_info": [{"v1": "rev1"}, {"v2": "rev2"}],
}


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def evaluation(proof=CODE, value=60, compatible=True):
    return {
        "status": "passed",
        "primary_version": "v1",
        "candidate": {
            "code_sha256": sha(validate_candidate(ROW, proof)[0]),
            "length": 10,
        },
        "scores": {
            "combined_pct": value,
            "length_reduction_pct": value,
            "heartbeat_reduction_pct": value,
            "compatibility_pct": 100 if compatible else 50,
        },
        "per_version": {
            v: {
                "status": "passed" if v == "v1" or compatible else "failed",
                "passed": v == "v1" or compatible,
                "diagnostics": [],
                "cached": True,
            }
            for v in ("v1", "v2")
        },
    }


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
        values = {
            v: {"status": "prepared", **deepcopy(item["reference"])}
            for v, item in self.pack["incumbent"]["per_version"].items()
        }
        if self.changed:
            values["v1"]["heartbeats"] += 1
        return {"versions": values}

    def _context(self, row, version):
        return None, None, "context_" + version

    def reference_snapshot(self, name, *, expected_row=None):
        result = self.get_reference(name)
        return result, {version: "context_" + version for version in result["versions"]}


def test_adapter_gates_only_full_checks_and_keeps_authoritative_evidence():
    raw = evaluation(OTHER, 90, False)
    fake = FakeEvaluator(values={OTHER: raw})
    events = []
    adapter = AllVersionsEvaluator(fake, ["v1", "v2"], events.append)
    assert adapter.evaluate("p", OTHER, versions="primary")["status"] == "passed"
    assert not events
    gated = adapter.evaluate("p", OTHER)
    assert gated["status"] == "policy_compatibility_rejected"
    assert (
        gated["scores"] == raw["scores"] and gated["per_version"] == raw["per_version"]
    )
    assert raw["status"] == events[0]["evaluation"]["status"] == "passed"
    assert events[0]["eligible"] is False
    assert events[0]["authoritative_status"] == "passed"
    assert adapter.calls is fake.calls
    missing = evaluation(OTHER)
    missing["per_version"].pop("v2")
    fake.values[OTHER] = missing
    assert adapter.evaluate("p", OTHER)["status"] == "policy_compatibility_rejected"


def test_frozen_optimizer_cannot_accept_higher_score_with_failed_version(monkeypatch):
    import proof_eval.optimization.engine as experiments

    def discover(evaluator, row, code, method, budget, **kwargs):
        groups = (
            [
                [Edit(0, len(code), OTHER, "partial")],
                [Edit(0, len(code), BEST, "valid")],
            ]
            if code == CODE
            else []
        )
        return groups, "best_pool", {"analysis_requests": 0}

    monkeypatch.setattr(experiments, "discovery", discover)
    fake = FakeEvaluator(
        values={
            CODE: evaluation(CODE, 50),
            OTHER: evaluation(OTHER, 90, False),
            BEST: evaluation(BEST, 60),
        }
    )
    policies, trials = [], []
    result = optimize(
        AllVersionsEvaluator(fake, ["v1", "v2"], policies.append),
        ROW,
        CODE,
        "lint",
        BUDGET,
        trials.append,
        lambda state: None,
    )
    assert result["proof"] == BEST
    partial_trial = next(t for t in trials if t.get("proof") == OTHER)
    assert partial_trial["improves_incumbent"] is False
    assert partial_trial["evaluation"]["status"] == "policy_compatibility_rejected"


def fake_method(evaluator, row, initial, method, budget, emit, save, state=None):
    result = evaluation(initial)
    return {
        "name": row["name"],
        "source": row["source"],
        "method": method,
        "proof": initial,
        "initial": result,
        "final": result,
        "stop_reason": "no_new_proposals",
        "attempts": 1,
        "analysis_requests": 1,
        "lean_candidate_checks": 0,
        "cache_hits": 1,
        "accepted_transitions": 0,
        "elapsed_seconds": 0.5,
    }


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

    kwargs = dict(
        evaluator=fake,
        row=ROW,
        proof=CODE,
        folder=tmp_path / "job",
        provenance={"frozen": "pins"},
        optimize_fn=method,
    )
    with pytest.raises(RuntimeError, match="interruption"):
        cleanup_proof(**kwargs)
    result = cleanup_proof(**kwargs)
    assert result["status"] == "complete"
    assert [stage["method"] for stage in result["stages"]] == list(METHODS)
    assert result["counters"]["attempts"] == 10
    assert (
        len(calls) == 11
    )  # One interrupted method resumes, prior methods do not replay.
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

    result = cleanup_proof(
        evaluator=FakeEvaluator(),
        row=ROW,
        proof=CODE,
        folder=tmp_path,
        provenance={},
        optimize_fn=method,
    )
    assert result["status"] == "incomplete_discovery"
    assert result["incomplete_methods"] == ["menu"]
    assert result["all_versions_valid"]


def test_immutable_budget_is_exact():
    assert asdict(BUDGET) == {"rounds": 3, "trials": 32, "sites": 6, "min_gain": 0.05}
    assert len(METHODS) == 10


@pytest.mark.parametrize("secondary_passes", [False, True])
def test_new_golf_method_preserves_all_version_gate_and_completed_job(
    tmp_path, secondary_passes
):
    initial = "theorem p : True := by exact (True.intro)"
    shorter = "theorem p : True := by exact True.intro"
    fake = FakeEvaluator(
        values={
            initial: evaluation(initial, 50),
            shorter: evaluation(shorter, 60, secondary_passes),
        }
    )
    args = dict(
        evaluator=fake,
        row=ROW,
        proof=initial,
        folder=tmp_path,
        provenance={"test": "new_method"},
        methods=("golf",),
    )
    result = cleanup_proof(**args)
    assert result["proof"] == (shorter if secondary_passes else initial)
    before = len(fake.calls)
    assert cleanup_proof(**args) == result
    assert len(fake.calls) == before
    with pytest.raises(ValueError, match="configuration changed"):
        cleanup_proof(**{**args, "methods": ("proof_theory",)})
