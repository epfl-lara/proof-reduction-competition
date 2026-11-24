"""Observable order interactions, branch retention, evidence and isolation contracts."""

from dataclasses import replace

import pytest

from proof_eval.evidence.io import digest, read, sha, write_json
from proof_eval.optimization import engine, exploration
from proof_eval.optimization.exploration_reporting import audit_cell, report_exploration
from proof_eval.optimization.search_graph import SearchPlan, plans
from proof_eval.optimization.syntax import Edit
from proof_eval.verification.initial import measure_original
from proof_eval.verification.metrics import token_count, validate_candidate

ORIGINAL = "theorem p : True := by\n  have h : True := True.intro\n  exact h"
A = "theorem p : True := by exact True.intro"
B = "theorem p : True := by trivial"
C = "theorem p : True := True.intro"
BAD = "theorem p : True := by constructor"
ROW = {
    "name": "p",
    "source": "fixture",
    "statement": "theorem p : True",
    "src": ORIGINAL,
    "version_info": [{"v1": "r1"}, {"v2": "r2"}],
}
ROW["proof_length"] = token_count(validate_candidate(ROW, ORIGINAL)[1])


class Evaluator:
    def __init__(self):
        self.calls = []
        self.store = object()

    def evaluate(self, name, code, *, versions="all"):
        self.calls.append((code, versions))
        length = token_count(validate_candidate(ROW, code)[1])
        hb = {ORIGINAL: 1000, A: 100, B: 650, C: 5, BAD: 0}[code]
        scores = {
            "length_reduction_pct": 100 * (1 - length / ROW["proof_length"]),
            "heartbeat_reduction_pct": 100 * (1 - hb / 1000),
            "compatibility_pct": 50 if code == BAD else 100,
        }
        scores["combined_pct"] = sum(scores.values()) / 3
        return {
            "status": "passed",
            "scores": scores,
            "primary_version": "v1",
            "candidate": {
                "length": length,
                "code_sha256": sha(validate_candidate(ROW, code)[0]),
            },
            "per_version": {
                v: {
                    "status": "failed" if v == "v2" and code == BAD else "passed",
                    "passed": not (v == "v2" and code == BAD),
                    "heartbeats": hb,
                    "heartbeat_reduction_pct": scores["heartbeat_reduction_pct"],
                    "cached": False,
                    "environment_fingerprint": "env_" + v,
                    "diagnostics": [],
                }
                for v in (["v1"] if versions == "primary" else ["v1", "v2"])
            },
        }


@pytest.fixture
def discovery(monkeypatch):
    mapping = {
        (ORIGINAL, "simp"): [BAD, A],
        (ORIGINAL, "wrappers"): [B],
        (B, "simp"): [C],
    }

    def discover(evaluator, row, code, method, budget, **kwargs):
        return (
            [[Edit(0, len(code), p, "test")] for p in mapping.get((code, method), [])],
            "best_pool",
            {"analysis_requests": 0},
        )

    monkeypatch.setattr(engine, "discovery", discover)
    return mapping


def run(folder, plan):
    evaluator = Evaluator()
    proof, original = measure_original(
        evaluator, folder, {"name": "p", "row": ROW}, timeout_retries=1
    )
    kwargs = dict(
        evaluator=evaluator,
        row=ROW,
        proof=proof,
        evaluation=original,
        folder=folder / "search",
        plan=plan,
        provenance={"fixture": 1},
    )
    result = exploration.explore(**kwargs)
    write_json(
        folder / "result.json",
        {
            **result,
            "search_sha256": digest(folder / "search/result.json"),
            "measurement_sha256": digest(folder / "initial_measurement.json"),
        },
    )
    reference = {
        "per_version": {
            v: {
                "heartbeats": 1000,
                "provenance": {"environment_fingerprint": "env_" + v},
            }
            for v in ("v1", "v2")
        }
    }
    audited = audit_cell(folder, ROW, reference)
    return result, kwargs, audited


def test_branch_keeps_lower_scoring_path_that_unlocks_better_proof(tmp_path, discovery):
    plan = SearchPlan(methods=("simp", "wrappers"))
    greedy, _, _ = run(tmp_path / "greedy", plan)
    beam, _, audited = run(tmp_path / "beam", replace(plan, strategy="beam", width=2))
    reverse, _, _ = run(
        tmp_path / "reverse", replace(plan, methods=tuple(reversed(plan.methods)))
    )
    assert greedy["proof"] == A
    assert beam["proof"] == reverse["proof"] == C
    assert beam["gain_pp"] > greedy["gain_pp"]
    assert audited["nodes"] == 4
    assert not (tmp_path / "beam/search/nodes" / (sha(BAD) + ".json")).exists()


def test_repeated_sweep_revisits_methods_after_later_change(tmp_path, discovery):
    discovery.clear()
    discovery.update({(ORIGINAL, "wrappers"): [B], (B, "simp"): [C]})
    plan = SearchPlan(methods=("simp", "wrappers"))
    once, _, _ = run(tmp_path / "once", replace(plan, strategy="sweep"))
    repeated, _, _ = run(tmp_path / "repeat", plan)
    assert once["proof"] == B and repeated["proof"] == C
    assert repeated["stop"] == "no_change_sweep" and repeated["sweeps"] == 3


def test_completed_search_reuses_only_verified_sealed_artifacts(tmp_path, discovery):
    result, kwargs, _ = run(tmp_path, SearchPlan(methods=("simp", "wrappers")))
    count = len(kwargs["evaluator"].calls)
    assert exploration.explore(**kwargs) == result
    assert len(kwargs["evaluator"].calls) == count
    with pytest.raises(ValueError, match="configuration changed"):
        exploration.explore(**{**kwargs, "plan": replace(kwargs["plan"], sweeps=9)})
    proof_path = tmp_path / "search/nodes" / (result["best"] + ".json")
    changed = read(proof_path)
    changed["evaluation"]["scores"]["combined_pct"] += 1
    write_json(proof_path, changed)
    with pytest.raises(ValueError, match="evidence changed"):
        exploration.explore(**kwargs)


def test_interrupted_expansion_is_not_replayed_and_checkpoint_survives(
    tmp_path, discovery, monkeypatch
):
    original_optimize = exploration.optimize
    calls = []

    def interrupted(*args, **kwargs):
        calls.append(args[3])
        if args[3] == "wrappers":
            raise RuntimeError("interrupted")
        return original_optimize(*args, **kwargs)

    monkeypatch.setattr(exploration, "optimize", interrupted)
    evaluator = Evaluator()
    kwargs = dict(
        evaluator=evaluator,
        row=ROW,
        proof=ORIGINAL,
        evaluation=evaluator.evaluate("p", ORIGINAL),
        folder=tmp_path,
        plan=SearchPlan(methods=("simp", "wrappers")),
        provenance={},
    )
    with pytest.raises(RuntimeError, match="interrupted"):
        exploration.explore(**kwargs)
    assert read(tmp_path / "progress.json")["best"] == sha(A)
    before = len(calls)
    with pytest.raises(RuntimeError, match="Indeterminate"):
        exploration.explore(**kwargs)
    assert len(calls) == before


@pytest.mark.parametrize(
    "timed_out,status", [(True, "complete"), (False, "incomplete")]
)
def test_discovery_timeout_is_limited_and_other_failures_are_incomplete(
    tmp_path, monkeypatch, timed_out, status
):
    def discover(*args, **kwargs):
        return (
            [],
            "best_pool",
            {
                "status": "discovery_timeout" if timed_out else "discovery_failed",
                "diagnostics": [{"kind": "discovery_process", "timed_out": timed_out}],
            },
        )

    monkeypatch.setattr(engine, "discovery", discover)
    result, _, _ = run(tmp_path, SearchPlan(methods=("search",)))
    assert result["status"] == status and result["proof"] == ORIGINAL
    assert result["discovery_limited_expansions"] == int(timed_out)


def test_report_withholds_mean_until_entire_audited_cohort_completes(
    tmp_path, discovery
):
    write_json(
        tmp_path / "config.json",
        {"names": ["p", "q"], "conditions": {"test": {}}, "scope": "test"},
    )
    folder = tmp_path / "conditions/test/cells/p"
    _, _, audited = run(folder, SearchPlan(methods=("simp",)))
    write_json(folder / "audit.json", audited)
    assert report_exploration(tmp_path)["conditions"]["test"]["mean_gain_pp"] is None
    config = read(tmp_path / "config.json")
    config["names"] = ["p"]
    write_json(tmp_path / "config.json", config)
    assert report_exploration(tmp_path)["best_observed"] == "test"


def test_study_plans_roundtrip_and_keep_every_method():
    from proof_eval.optimization.cleanup import METHODS, PROOF_THEORY_METHODS

    for plan in plans().values():
        assert SearchPlan.from_record(plan.record()) == plan
        assert set(plan.methods) == set(METHODS + PROOF_THEORY_METHODS)
    with pytest.raises(ValueError):
        SearchPlan(methods=("simp", "simp"))


def test_exploration_keeps_searching_after_five_minutes(
    tmp_path, discovery, monkeypatch
):
    import time

    clock = [time.time()]

    def tick():
        clock[0] += 100
        return clock[0]

    monkeypatch.setattr(exploration.time, "time", tick)
    result, _, _ = run(tmp_path, SearchPlan(methods=("wrappers", "simp")))
    assert result["elapsed_seconds"] > 300 and result["proof"] == C
