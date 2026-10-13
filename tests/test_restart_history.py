"""History is bounded, evidence-derived, scoped, and never treated as proof."""

import json
from copy import deepcopy

import pytest

from proof_eval.harness.restart_history import (
    MAX_CONTEXT_CHARS,
    MAX_EVENTS_PER_ATTEMPT,
    RestartHistory,
    build_history,
)


def test_history_bounds_and_latest_notes_survive_reload(tmp_path):
    scope = {
        "name": "theorem",
        "model": "model",
        "effort": "max",
        "mode": "score_edges",
        "input_sha256": "pin",
    }
    history = RestartHistory(tmp_path, scope)
    history.attempt = 0
    for i in range(MAX_EVENTS_PER_ATTEMPT - 1):
        history.remember("next", f"{i}: " + "\\\nλ" * 100)
    history.record(
        "source_observation",
        {
            "request": {"op": "search", "query": "hint"},
            "response": {"text": "source" * 10000},
        },
    )
    assert not history.remember("next", "over limit")["saved"]
    loaded = RestartHistory(tmp_path, scope)
    result = build_history(scope, [], loaded.events, "seed")
    assert len(json.dumps(result, ensure_ascii=False, indent=2)) <= MAX_CONTEXT_CHARS
    assert result["unverified_model_notes"][0]["text"].startswith("62:")
    assert len(result["retrieved_source_observations"]) == 1
    assert result["host_checked_trials"] == []
    foreign = deepcopy(scope)
    foreign["name"] = "another theorem"
    with pytest.raises(ValueError, match="another theorem"):
        build_history(foreign, [], loaded.events, "seed")
    with pytest.raises(ValueError, match="1-600"):
        loaded.remember("discovery", "x" * 601)


def test_history_keeps_measured_rejections_separate_from_notes(tmp_path):
    scope = {"name": "t"}
    history = RestartHistory(tmp_path, scope)
    history.attempt = 0
    history.remember("discovery", "I think this lemma works; not checked")
    checks = []
    for i in range(30):
        accepted = i < 3
        checks.append(
            {
                "number": i + 1,
                "duplicate": False,
                "accepted": accepted,
                "all_versions_passed": accepted,
                "code": "x" * 4000 + str(i),
                "evaluation": {"scores": {"combined_pct": 91 if accepted else 0}},
                "previous_best_score": 90,
                "feedback": {"errors": ["bad term" * 300]},
            }
        )
    result = build_history(scope, checks, history.events, "seed")
    assert len(json.dumps(result, ensure_ascii=False, indent=2)) <= MAX_CONTEXT_CHARS
    trials = result["host_checked_trials"]
    assert len(trials) <= 6 and trials[-1]["check"] == 30
    assert trials[-1]["reason"] == "failed_required_version_check"
    assert result["unverified_model_notes"][0]["kind"] == "discovery"
    assert result["prior_check_count"] == 30
