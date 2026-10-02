"""Input and coverage checks for the resumable ablation CLI."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from run_experiments import initial_proofs, persist_summary


class Data:
    names = ["a", "b"]

    def get(self, name):
        return {"src": "original " + name}


def test_input_requires_full_unique_benchmark(tmp_path):
    evaluator = SimpleNamespace(dataset=Data())
    path = tmp_path / "input.jsonl"
    path.write_text('\n'.join(json.dumps({"name": n, "proof": "by rfl"}) for n in ["a", "a"]))
    with pytest.raises(ValueError, match="exactly one"):
        initial_proofs(evaluator, path)
    path.write_text('\n'.join(json.dumps({"name": n, "proof": "by rfl"}) for n in ["b", "a"]))
    assert initial_proofs(evaluator, path) == {"a": "by rfl", "b": "by rfl"}


def test_partial_stage_preserves_fallback_and_has_no_full_score(tmp_path):
    scores = dict(length_reduction_pct=0, heartbeat_reduction_pct=0,
                  compatibility_pct=100, combined_pct=100/3)
    result = {"status": "passed", "scores": scores,
              "per_version": {"v1": {"passed": True}, "v2": {"passed": True}}}
    record = {"name": "a", "initial": result, "final": result, "changed": False,
              "attempts": 0, "stop_reason": "no_new_proposals"}
    summary = persist_summary(tmp_path, [record], {"a": "selected", "b": "original"}, ["a", "b"])
    assert summary["full_benchmark_combined_pct"] is None
    assert summary["version_checks_passed"] == 2
    rows = [json.loads(s) for s in (tmp_path / "candidates.jsonl").read_text().splitlines()]
    assert rows == [{"name": "a", "proof": "selected"}, {"name": "b", "proof": "original"}]
