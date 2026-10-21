"""Study selection waits for full cohorts and never pools partial means."""

from proof_eval.evidence.io import write_json
from proof_eval.optimization.bounded import ALL_METHODS
from proof_eval.optimization.study import select_combinations
from proof_eval.optimization.study_reporting import report_study


def test_incomplete_condition_has_no_full_cohort_mean(tmp_path):
    write_json(
        tmp_path / "config.json",
        {"names": ["a", "b"], "conditions": {"golf": ["golf"]}, "scope": "development"},
    )
    write_json(
        tmp_path / "conditions/golf/cells/a/result.json",
        {
            "status": "complete",
            "gain_pp": 30,
            "optimization_seconds": 1,
            "elapsed_seconds": 2,
            "evaluation": {"scores": {"combined_pct": 63.333}},
        },
    )
    report = report_study(tmp_path)
    assert report["conditions"]["golf"]["mean_gain_pp"] is None
    assert report["recommended_methods"] is None


def test_full_cohort_keeps_discovery_limited_results_and_counts_them(tmp_path):
    write_json(
        tmp_path / "config.json",
        {
            "names": ["a", "b"],
            "conditions": {"search": ["search"]},
            "scope": "development",
        },
    )
    for name, status, gain in (("a", "discovery_limit", 0), ("b", "complete", 2)):
        write_json(
            tmp_path / f"conditions/search/cells/{name}/result.json",
            {
                "status": status,
                "gain_pp": gain,
                "optimization_seconds": 120,
                "elapsed_seconds": 150,
                "evaluation": {"scores": {"combined_pct": 33 + gain}},
            },
        )
    row = report_study(tmp_path)["conditions"]["search"]
    assert row["complete"] and row["mean_gain_pp"] == 1
    assert row["discovery_limited_problems"] == 1


def test_combinations_require_all_screens_and_exclude_zero_gain():
    report = {
        "conditions": {
            "single_"
            + method: {
                "methods": [method],
                "complete": True,
                "mean_gain_pp": 0,
                "mean_optimization_seconds": 300,
            }
            for method in ALL_METHODS
        }
    }
    report["conditions"]["single_golf"].update(
        mean_gain_pp=2, mean_optimization_seconds=1
    )
    report["conditions"]["single_simp"].update(
        mean_gain_pp=3, mean_optimization_seconds=100
    )
    selected = select_combinations(report)
    assert selected == {
        "selected_top4_gain": ("simp", "golf"),
        "selected_top4_rate": ("golf", "simp"),
    }
    report["conditions"]["single_menu"]["complete"] = False
    assert select_combinations(report) == {}
