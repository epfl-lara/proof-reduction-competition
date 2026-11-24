"""Actual search-clock publication and admission delay regression contracts."""

import json
from types import SimpleNamespace

import pytest
from test_search_exploration import ROW, C

from proof_eval.evidence.io import digest, read
from proof_eval.harness import attempts, limits
from proof_eval.harness.tracking_audit import _audit_attempt_time


def test_first_search_event_uses_problem_clock_and_is_never_restarted(
    tmp_path, monkeypatch, capsys
):
    first = tmp_path / "model/cells/first"
    second = first.with_name("second")
    first.mkdir(parents=True)
    second.mkdir()
    epoch = [1000.0]
    monkeypatch.setattr(limits.time, "time", lambda: epoch[0])
    budget = limits.start_budget(first, 600, announce=True)
    marker = first.parent.parent / "model-timer-started.json"
    before = marker.read_bytes()
    event = json.loads(capsys.readouterr().out)
    assert event["event"] == "MODEL_SEARCH_STARTED"
    assert event["started_epoch"] == budget["started_epoch"] == 1000.0
    assert event["clock_sha256"] == digest(first / "budget_started.json")
    assert event["setup_and_model_loading_excluded"] is True
    epoch[0] += 601
    limits.start_budget(second, 600, announce=True)
    assert capsys.readouterr().out == ""
    assert marker.read_bytes() == before
    assert limits.start_budget(first, 600, announce=True) == budget
    assert read(marker)["started_epoch"] == 1000.0


def test_changed_first_clock_is_rejected_before_new_search(tmp_path):
    first = tmp_path / "model/cells/first"
    second = first.with_name("second")
    first.mkdir(parents=True)
    second.mkdir()
    limits.start_budget(first, 600, announce=True)
    (first / "budget_started.json").write_text("{}")
    with pytest.raises(ValueError, match="First model-search clock changed"):
        limits.start_budget(second, 600, announce=True)


def test_slow_message_storage_does_not_replenish_attempt_timeout(tmp_path, monkeypatch):
    # Reproduce a delay larger than the old audit's one-second tolerance.
    session = SimpleNamespace(
        checks=[],
        best_code=C,
        best_evaluation={"status": "passed"},
        row=ROW,
        deadline_at=100.0,
        finished=None,
        restart_history=None,
        proof_history=None,
    )
    monkeypatch.setattr(attempts.time, "time", lambda: 11.364929676)
    folder = tmp_path / "attempt_00"
    folder.mkdir()
    saved = attempts.start_attempt(
        folder, session, [], 0, {}, 90.0, None, remaining=90.0
    )
    assert saved["generation_timeout_seconds"] == pytest.approx(88.635070324)
    assert saved["time_remaining_seconds"] == saved["generation_timeout_seconds"]
    _audit_attempt_time(
        {"generation_timeout": 90},
        {"time_budget": {"deadline_epoch": 100.0}},
        saved,
        {"timeout": saved["generation_timeout_seconds"]},
    )
