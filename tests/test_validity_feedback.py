"""Correctness feedback must not expose performance or silently repair outputs."""

import json
from copy import deepcopy

import pytest

from proof_eval.verification.feedback import (
    all_versions_passed,
    build_validity_feedback,
)


def checked(status="passed", diagnostics=None):
    return {
        "status": status,
        "passed": status == "passed",
        "diagnostics": diagnostics or [],
    }


def error(text):
    return {"severity": "error", "data": text}


def test_success_requires_every_configured_version_not_aggregate_success():
    evaluation = {
        "status": "passed",
        "per_version": {
            "v1": checked(),
            "v2": checked("failed", [error("unknown constant foo")]),
        },
    }
    assert not all_versions_passed(evaluation, ["v1", "v2"])
    feedback = build_validity_feedback(evaluation, ["v1", "v2"])
    assert feedback["primary_passed"] and not feedback["all_versions_passed"]
    assert feedback["status"] == "failed"
    assert feedback["versions"][0]["errors"] == []
    assert feedback["versions"][1]["version"] == "v2"
    assert feedback["versions"][1]["errors"] == ["unknown constant foo"]


@pytest.mark.parametrize(
    "checks",
    [
        {"v1": checked()},
        {"v1": checked(), "v2": checked(), "extra": checked()},
        {"v1": checked(), "v2": {"status": "passed", "passed": 1}},
        {"v1": checked(), "v2": {"status": "failed", "passed": True}},
        {"v1": None, "v2": checked()},
    ],
)
def test_missing_extra_or_inconsistent_checks_are_not_success(checks):
    evaluation = {"status": "passed", "per_version": checks}
    assert not all_versions_passed(evaluation, ["v1", "v2"])
    assert not build_validity_feedback(evaluation, ["v1", "v2"])["all_versions_passed"]


def test_all_compiler_checks_can_pass_without_any_available_score():
    evaluation = {
        "status": "incomplete",
        "scores": {"combined_pct": None},
        "per_version": {"v1": checked(), "v2": checked()},
    }
    assert all_versions_passed(evaluation, ["v1", "v2"])
    assert build_validity_feedback(evaluation, ["v1", "v2"])["status"] == "valid"


def test_measurement_fields_and_wrapper_messages_never_reach_feedback():
    evaluation = {
        "status": "failed",
        "scores": {"combined_pct": 77.1234},
        "candidate": {"length": 314159},
        "reference": {"length": 271828},
        "diagnostics": ["Primary reference heartbeat count is zero"],
        "per_version": {
            "v1": {
                **checked(
                    "failed",
                    [
                        {"severity": "info", "data": "PROOF_EVAL_deadbeef:123456789"},
                        error("No heartbeat marker was returned by the wrapper"),
                        error('PROOF_CONTEXT:{"tactic_allocations": 999999}'),
                        error(
                            "combined_pct: 77.1234\nunsolved goals\nx : Nat\n⊢ x = x"
                        ),
                    ],
                ),
                "heartbeats": 123456789,
                "elapsed_seconds": 777777,
                "reference": {"heartbeats_raw": 123456789000},
            }
        },
    }
    previous = deepcopy(evaluation)
    feedback = build_validity_feedback(evaluation, ["v1"])
    text = json.dumps(feedback)
    for forbidden in (
        "77.1234",
        "314159",
        "271828",
        "123456789",
        "777777",
        "999999",
        "heartbeat",
        "allocations",
        "combined_pct",
        "PROOF_EVAL",
        "PROOF_CONTEXT",
        "elapsed",
    ):
        assert forbidden not in text
    assert feedback["versions"][0]["errors"] == ["unsolved goals\nx : Nat\n⊢ x = x"]
    assert evaluation == previous


def test_sorry_wrapper_is_only_retained_when_no_real_lean_error_exists():
    wrapper = error("Target declaration depends on sorryAx")
    evaluation = {
        "status": "failed",
        "per_version": {
            "v1": checked("failed", [wrapper, error("unsolved goals\n⊢ True")])
        },
    }
    assert build_validity_feedback(evaluation, ["v1"])["versions"][0]["errors"] == [
        "unsolved goals\n⊢ True"
    ]
    evaluation["per_version"]["v1"]["diagnostics"] = [wrapper]
    assert build_validity_feedback(evaluation, ["v1"])["versions"][0]["errors"] == [
        "Target declaration depends on sorryAx"
    ]


def test_successful_logs_and_nonerror_messages_are_ignored():
    diagnostics = [
        {"severity": "warning", "data": "irrelevant warning"},
        {"severity": "info", "data": "Try this: exact alternative"},
    ]
    evaluation = {
        "status": "passed",
        "per_version": {"v1": checked(diagnostics=diagnostics)},
    }
    assert build_validity_feedback(evaluation, ["v1"])["versions"][0]["errors"] == []


@pytest.mark.parametrize("data", [None, "", "   ", {"unexpected": "structured data"}])
def test_generic_error_message_is_retained_when_data_is_missing_or_empty(data):
    diagnostic = {"severity": "error", "message": "unsolved goals\n⊢ RequiredTarget"}
    if data is not None:
        diagnostic["data"] = data
    evaluation = {
        "status": "failed",
        "per_version": {"v1": checked("failed", [diagnostic])},
    }
    assert build_validity_feedback(evaluation, ["v1"])["versions"][0]["errors"] == [
        "unsolved goals\n⊢ RequiredTarget",
    ]


def test_error_data_takes_precedence_over_generic_message():
    diagnostic = {
        "severity": "error",
        "data": "unknown constant missingName",
        "message": "generic fallback",
    }
    evaluation = {
        "status": "failed",
        "per_version": {"v1": checked("failed", [diagnostic])},
    }
    assert build_validity_feedback(evaluation, ["v1"])["versions"][0]["errors"] == [
        "unknown constant missingName",
    ]


def test_timeout_and_unavailable_are_distinct_without_timing_or_environment_details():
    evaluation = {
        "status": "incomplete",
        "per_version": {
            "v1": checked(
                "timeout", [error("Timeout after 900.3 seconds with 812344 heartbeats")]
            ),
            "v2": checked(
                "unavailable", [error("Missing private path /secret/config")]
            ),
        },
    }
    feedback = build_validity_feedback(evaluation, ["v1", "v2"])
    assert feedback["status"] == "timeout"
    assert [version["status"] for version in feedback["versions"]] == [
        "timeout",
        "unavailable",
    ]
    text = json.dumps(feedback)
    assert "900.3" not in text and "812344" not in text and "/secret" not in text
    assert "not evidence that the proof is incorrect" in text


@pytest.mark.parametrize(
    "message",
    [
        "Candidate must preserve the exact benchmark statement",
        "Forbidden construct: sorry",
        "Forbidden construct: native_decide",
        "Expected := immediately after the exact benchmark statement",
    ],
)
def test_structural_invalidity_retains_the_actual_correctness_reason(message):
    feedback = build_validity_feedback(
        {"status": "invalid", "diagnostics": [message], "per_version": {}}, ["v1", "v2"]
    )
    assert feedback["status"] == "invalid"
    assert feedback["errors"] == [message]
    assert all(version["status"] == "not_checked" for version in feedback["versions"])


def test_truncation_is_output_recovery_without_numeric_generation_budget():
    feedback = build_validity_feedback(
        {
            "status": "invalid",
            "diagnostics": ["generation_truncated"],
            "per_version": {},
        },
        ["v1"],
    )
    assert "Recover a complete declaration" in feedback["errors"][0]
    assert "token" not in json.dumps(feedback)


def test_message_truncation_keeps_goal_target_after_long_context():
    message = "unsolved goals\n" + "h : LongHypothesis\n" * 1000 + "⊢ required_target x"
    feedback = build_validity_feedback(
        {
            "status": "failed",
            "per_version": {"v1": checked("failed", [error(message)])},
        },
        ["v1"],
        max_message_chars=200,
    )
    observed = feedback["versions"][0]["errors"][0]
    assert len(observed) <= 200 and "⊢ required_target x" in observed
    assert feedback["truncated"]


def test_total_budget_handles_json_escaping_and_preserves_version_labels():
    message = ('quoted "text" and slash \\\n' * 300) + "⊢ Goal"
    evaluation = {
        "status": "failed",
        "per_version": {
            "v1": checked("failed", [error(message), error("second error")]),
            "v2": checked("failed", [error(message)]),
        },
    }
    feedback = build_validity_feedback(evaluation, ["v1", "v2"], max_total_chars=650)
    assert len(json.dumps(feedback, ensure_ascii=False)) <= 650
    assert feedback["truncated"]
    assert [version["version"] for version in feedback["versions"]] == ["v1", "v2"]
    assert "⊢ Goal" in feedback["versions"][0]["errors"][0]


def test_error_count_is_bounded_and_duplicates_are_removed():
    diagnostics = [error("first"), error("first"), error("second"), error("third")]
    feedback = build_validity_feedback(
        {"status": "failed", "per_version": {"v1": checked("failed", diagnostics)}},
        ["v1"],
        max_messages_per_version=2,
    )
    assert feedback["versions"][0]["errors"] == ["first", "second"]
    assert feedback["truncated"]


@pytest.mark.parametrize("versions", [[], ["v1", "v1"], [""], "v1"])
def test_required_versions_must_be_explicit_and_unique(versions):
    with pytest.raises(ValueError):
        all_versions_passed({}, versions)


def test_feedback_budget_cannot_silently_drop_required_validity_metadata():
    with pytest.raises(ValueError, match="too small"):
        build_validity_feedback({}, ["v1", "v2"], max_total_chars=20)
