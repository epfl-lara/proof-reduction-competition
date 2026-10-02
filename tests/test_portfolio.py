import json

import pytest

from run_portfolio import finished_stage, stage_workers


def test_concurrency_change_preserves_existing_stage(tmp_path):
    assert stage_workers(tmp_path, 8) == 8
    (tmp_path / "config.json").write_text(json.dumps({"workers": 4}))
    assert stage_workers(tmp_path, 8) == 4


def test_invalid_existing_concurrency_does_not_fall_back_silently(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"workers": 0}))
    with pytest.raises(ValueError, match="positive"):
        stage_workers(tmp_path, 8)


def test_completed_stage_is_audited_and_requires_exact_input(tmp_path, monkeypatch):
    from run_deterministic import digest
    source = tmp_path / "input.jsonl"
    source.write_text("original input\n")
    (tmp_path / "run.json").write_text(json.dumps({"status": "finished"}))
    budget = {"rounds": 6, "trials": 64, "sites": 6, "min_gain": 0.05}
    (tmp_path / "config.json").write_text(json.dumps({"method": "menu", "budget": budget,
                                                     "input_sha256": digest(source)}))
    checked = []
    monkeypatch.setattr("run_portfolio.audit", lambda *a, **k: checked.append((a, k)))
    assert finished_stage(tmp_path, source, "menu", budget, "references.jsonl")
    assert checked[0][1]["check_code"] is True
    source.write_text("different input\n")
    with pytest.raises(ValueError, match="different inputs"):
        finished_stage(tmp_path, source, "menu", budget, "references.jsonl")


def test_unavailable_discovery_is_not_completed(tmp_path):
    (tmp_path / "run.json").write_text(json.dumps({"status": "finished_with_unavailable"}))
    assert not finished_stage(tmp_path, "unused", "menu", {}, "unused")
