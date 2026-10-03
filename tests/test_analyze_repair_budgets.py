"""Recorded-prefix validity, stopping, strict score selection and budget costs."""
from copy import deepcopy

import pytest

import analyze_repair_budgets as analysis
from report_one_shot import read_json, write_json
from test_report_repair_matrix import MatrixFixture, evaluation, generation


def pack():
    return {"proof": "incumbent", "incumbent": evaluation(50),
            "row": {"version_info": [{"v1": "revision"}]}}


def state(proof="candidate", value=0, status="failed"):
    return {"proof": proof, "evaluation": evaluation(value, status), "generation": generation(proof)}


def final_record(reference, initial, trials, *, valid=False, returned=False, accepted=False):
    last = trials[-1] if trials else initial
    return {"round_count": len(trials), "final_proof": last["proof"], "final_evaluation": last["evaluation"],
        "final_valid": valid, "returned_incumbent": returned, "accepted": accepted,
        "selected_proof": last["proof"] if accepted else reference["proof"],
        "selected_evaluation": last["evaluation"] if accepted else reference["incumbent"]}


def replay(reference, initial, later, **labels):
    trials = [{"round": number, **value} for number, value in enumerate(later, 1)]
    record = final_record(reference, initial, trials, **labels)
    start = {"evaluation": initial["evaluation"], "generation": initial["generation"],
             "extracted_proof": initial["proof"]}
    return analysis.replay_cell(reference, start, trials, record)


def test_second_round_gain_stops_cost_at_two_even_with_budget_three():
    rows = replay(pack(), state(), [state(), state("better", 56, "passed")], valid=True, accepted=True)
    assert [r["selected_score"] for r in rows] == [50, 50, 56, 56]
    assert [r["repair_calls"] for r in rows] == [0, 1, 2, 2]
    assert [r["changed_valid"] for r in rows] == [False, False, True, True]
    assert rows[3]["additional_generation"]["completion_tokens"] == 40


@pytest.mark.parametrize("value", [40, 50.05])
def test_first_valid_inferior_or_margin_equal_candidate_stops_without_acceptance(value):
    rows = replay(pack(), state(), [state("valid changed", value, "passed")], valid=True)
    assert [r["selected_score"] for r in rows] == [50] * 4
    assert [r["repair_calls"] for r in rows] == [0, 1, 1, 1]
    assert [r["changed_valid"] for r in rows] == [False, True, True, True]
    assert not any(r["accepted_improvement"] for r in rows)


def test_valid_incumbent_return_and_empty_initial_are_distinct():
    returned = replay(pack(), state(), [state("incumbent", 50, "passed")], valid=True, returned=True)
    empty = replay(pack(), state("", 0, "invalid"), [])
    assert returned[1]["returned_incumbent"] and not returned[1]["changed_valid"]
    assert not empty[3]["returned_incumbent"] and not empty[3]["all_versions_valid"]
    assert empty[3]["repair_calls"] == 0 and empty[3]["raw_score"] == 0


def test_transport_unknown_stops_and_does_not_become_raw_zero():
    unavailable = state("", None, "unavailable")
    unavailable["generation"] = {"status": "transport_error", "usage": None}
    rows = replay(pack(), state(), [unavailable])
    assert [r["repair_calls"] for r in rows] == [0, 1, 1, 1]
    assert rows[1]["raw_score"] is None and rows[1]["raw_unknown"]
    assert rows[1]["selected_score"] == 50
    assert rows[1]["additional_generation"]["usage_missing_generations"] == 1
    assert rows[1]["additional_generation"]["completion_tokens"] == 0


def test_primary_version_success_does_not_bypass_all_version_gate():
    reference = pack()
    reference["row"]["version_info"].append({"v2": "revision"})
    reference["incumbent"]["per_version"]["v2"] = {"status": "passed", "passed": True}
    partial = state("partial", 99, "passed")
    partial["evaluation"]["per_version"]["v2"] = {"status": "failed", "passed": False}
    rows = replay(reference, partial, [deepcopy(partial) for _ in range(3)])
    assert not any(r["all_versions_valid"] for r in rows)
    assert [r["repair_calls"] for r in rows] == [0, 1, 2, 3]
    assert [r["selected_score"] for r in rows] == [50] * 4


def test_repair_after_valid_or_early_unjustified_termination_is_rejected():
    with pytest.raises(ValueError, match="terminal prefix"):
        replay(pack(), state(), [state("valid", 55, "passed"), state("later", 56, "passed")], valid=True, accepted=True)
    with pytest.raises(ValueError, match="ended before"):
        replay(pack(), state(), [state()])


def test_partial_condition_means_are_masked_at_every_budget(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain"])
    data.write_final("plain", "p", score=56)
    report, problems = analysis.analyze(data.output)
    assert report["status"] == "incomplete" and len(problems) == 4
    assert all(row["selected_mean"] is None and row["raw_mean"] is None for row in report["conditions"])
    assert all(row["recorded_complete_trajectories"] == 1 for row in report["conditions"])
    assert not report["positive_marginal_outcomes"]
    with pytest.raises(ValueError, match="incomplete"):
        analysis.analyze(data.output, require_complete=True)


def test_complete_cohort_round_two_gain_round_three_copy_and_missing_usage(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain"])
    folders = [(data.write_final("plain", "p", score=56, rounds=2), 2),
               (data.write_final("plain", "q", score=60, incumbent=True, rounds=3), 3)]
    for folder, count in folders:
        for number in range(1, count):
            path = folder / "rounds" / f"{number:02d}" / "result.json"
            trial = read_json(path)
            trial["evaluation"] = evaluation(0, "failed")
            write_json(path, trial)
    path = folders[1][0] / "rounds" / "03" / "result.json"
    trial = read_json(path)
    trial["generation"]["usage"] = None
    write_json(path, trial)
    write_json(path.with_name("generation.json"), trial["generation"])
    report, _ = analysis.analyze(data.output, require_complete=True)
    conditions = report["conditions"]
    assert [row["selected_mean"] for row in conditions] == [55, 55, 58, 58]
    assert [row["all_versions_valid"] for row in conditions] == [0, 0, 1, 2]
    assert [row["changed_valid"] for row in conditions] == [0, 0, 1, 1]
    assert [row["returned_incumbent"] for row in conditions] == [0, 0, 0, 1]
    assert [row["additional_generation"]["request_attempts"] for row in conditions] == [0, 2, 4, 5]
    assert conditions[3]["additional_generation"]["completion_tokens"] == 80
    assert conditions[3]["additional_generation"]["usage_missing_generations"] == 1
    assert conditions[2]["marginal_selected_gain_pp"] == 3
    assert conditions[3]["marginal_selected_gain_pp"] == 0
    assert conditions[3]["marginal_generation"]["request_attempts"] == 1
    assert len(report["positive_marginal_outcomes"]) == 1
    assert report["positive_marginal_outcomes"][0]["round"] == 2
    assert report["positive_marginal_outcomes"][0]["selected_gain_pp"] == 6
    assert "selected_mean" not in report["diagnostic_totals"][3]


def test_budget_three_must_match_saved_terminal_selection():
    reference, initial = pack(), state()
    trials = [{"round": 1, **state("better", 56, "passed")}]
    wrong = final_record(reference, initial, trials, valid=True, accepted=False)
    with pytest.raises(ValueError, match="differs from the recorded final"):
        analysis.replay_cell(reference, {"evaluation": initial["evaluation"], "generation": initial["generation"]}, trials, wrong)


def test_declared_pilot_subset_is_not_a_full_benchmark_condition(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain"])
    path = data.output / "matrix_config.json"
    config = read_json(path)
    config["cells"] = config["cells"][:1]
    write_json(path, config)
    with pytest.raises(ValueError, match="full original theorem cohort"):
        analysis.analyze(data.output)
