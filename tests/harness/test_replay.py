from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import pytest

from proof_eval.evidence.io import read
from proof_eval.harness.discovery_tree import (
    AttemptNode,
    CheckNode,
    EvidenceReader,
    ProblemTree,
    load_run,
)
from proof_eval.harness.replay import AttemptCap, Identity, Stagnation, splice
from proof_eval.harness.replay_reporting import (
    audit_replay,
    gate,
    run_replay,
    validate_identity,
    validate_output,
)

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "results/harness/14_replay_stagnation/protocol.json"
STAGE10 = ROOT / "results/harness/10_budget_resets/sol61_max_3usd"


def check(number: int, at: float, accepted: bool, score: float, sha: str) -> CheckNode:
    return CheckNode(number, at, "agent_tool", accepted, True, score, sha)


def tree(*, late_gain: bool = False, cost: float | None = 1.0) -> ProblemTree:
    checks = [check(1, 60, True, 51, "one"), check(2, 300, False, 49, "bad")]
    if late_gain:
        checks.append(check(3, 480, True, 53, "late"))
    parent = "late" if late_gain else "one"
    return ProblemTree(
        "example",
        ("test", "max"),
        "synthetic",
        4,
        0,
        1000,
        50,
        (
            AttemptNode(0, 0, 600, "seed", tuple(checks), cost),
            AttemptNode(1, 610, 900, parent, (check(4, 700, True, 55, "two"),), 1),
        ),
        "synthetic",
        "seed",
        55,
    )


def test_stagnant_tail_splices_matching_parent_with_gap() -> None:
    result = splice(tree(), Stagnation(3))
    assert result.on_support
    assert result.raw_combined_pct == 55
    assert result.attempts[0].ended_elapsed == 300
    assert result.attempts[1].started_elapsed == 310
    assert result.anytime[-1] == (400, 55)
    assert result.freed_seconds == 300
    assert result.unspent_seconds == 400


def test_cut_accepted_check_breaks_support_and_hides_next_attempt() -> None:
    result = splice(tree(late_gain=True), Stagnation(3))
    assert not result.on_support
    assert result.support_reason == "accepted_check_cut"
    assert result.raw_combined_pct == 51
    assert len(result.attempts) == 1
    assert result.attempts[0].revealed_check_numbers == (1, 2)
    assert result.loss_pp == 4


def test_parent_mismatch_prevents_next_attempt() -> None:
    original = tree()
    altered = replace(
        original,
        attempts=(
            original.attempts[0],
            replace(original.attempts[1], incumbent_sha256="other"),
        ),
    )
    result = splice(altered, Identity())
    assert not result.on_support
    assert result.support_reason == "next_parent_sha_mismatch"
    assert len(result.attempts) == 1


def test_deadline_cannot_reveal_future_gain_or_credit_unspent_time() -> None:
    original = tree()
    clipped = replace(original, deadline=350)
    result = splice(clipped, Stagnation(3))
    assert result.raw_combined_pct == 51
    assert result.elapsed_seconds == 350
    assert all(at <= 350 for at, _ in result.anytime)
    assert result.unspent_seconds == 0


def test_limits_and_first_attempt() -> None:
    original = tree()
    assert (
        splice(original, Stagnation(math.inf)).raw_combined_pct
        == splice(original, Identity()).raw_combined_pct
    )
    assert (
        splice(original, AttemptCap(math.inf)).elapsed_seconds
        == splice(original, Identity()).elapsed_seconds
    )
    assert splice(original, AttemptCap(1)).raw_combined_pct == 51
    assert splice(original, AttemptCap(1)).on_support


def test_unknown_cost_stays_unknown_even_when_attempt_truncated() -> None:
    result = splice(tree(cost=None), Stagnation(3))
    assert result.estimated_cost_usd is None
    assert result.estimated_cost_savings_usd is None


def test_prefix_views_do_not_include_unrevealed_outcomes_or_intra_attempt_cost() -> (
    None
):
    class Observer:
        name = "observer"
        reset_gain_pp = 0

        def __init__(self) -> None:
            self.views = []

        def decide(self, view):
            self.views.append(view)
            return "end_attempt" if view.elapsed_attempt_seconds >= 300 else "continue"

    first, future = Observer(), Observer()
    splice(tree(), first)
    splice(tree(late_gain=True), future)
    assert first.views[:2] == future.views[:2]
    assert first.views[1].best_raw_pct == 51
    assert first.views[1].known_cumulative_cost_usd == 0
    assert not hasattr(first.views[1], "checks")
    assert first.views[2].known_cumulative_cost_usd is None


def test_micro_gain_updates_incumbent_without_resetting_secondary_clock() -> None:
    original = tree()
    attempt = replace(
        original.attempts[0],
        checks=(check(1, 60, True, 51, "one"), check(2, 300, True, 51.1, "micro")),
    )
    altered = replace(original, attempts=(attempt,), recorded_raw_pct=51.1)
    result = splice(altered, Stagnation(3, 0.25))
    assert result.raw_combined_pct == 51.1
    assert result.elapsed_seconds == 300


def test_output_overlap_and_existing_output_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="overlaps"):
        validate_output(tmp_path / "run" / "report", [tmp_path / "run"])
    with pytest.raises(ValueError, match="overlaps"):
        validate_output(tmp_path, [tmp_path / "run"])
    target = tmp_path / "report"
    target.mkdir()
    with pytest.raises(ValueError, match="already exists"):
        validate_output(target, [tmp_path / "run"])


def test_saved_identity_all_attempts_and_inputs_unchanged() -> None:
    reader = EvidenceReader()
    trees, excluded = load_run(STAGE10, reader=reader)
    assert not excluded
    assert len(trees) == 15
    result = validate_identity(trees, read(STAGE10 / "comparison.json"))
    assert result["comparison_attempts"] == 57
    reader.verify()


def test_gate_cannot_pass_on_missing_primary_problems() -> None:
    result = gate([tree()], [], read(PROTOCOL))
    assert result["verdict"] == "NO-GO"
    assert result["selected_minutes"] is None


def test_one_saved_problem_pilot_has_provenance_and_no_gate(tmp_path: Path) -> None:
    result = run_replay([STAGE10], PROTOCOL, tmp_path / "pilot", pilot=True)
    assert result["status"] == "complete"
    assert result["gate"]["verdict"] == "NOT_EVALUATED"
    assert len(result["input_sha256"]) > 50
    assert result["source_sha256"]
    assert (tmp_path / "pilot" / "per_problem.csv").exists()
    assert audit_replay(tmp_path / "pilot")["status"] == "passed"
    (tmp_path / "pilot" / "per_problem.csv").write_text("tampered")
    with pytest.raises(ValueError, match="artifact mismatch"):
        audit_replay(tmp_path / "pilot")
