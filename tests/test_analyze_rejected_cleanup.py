"""Counterfactual selection, deduplicated cost, and historical-copy accounting."""
import pytest

import analyze_rejected_cleanup as analysis
from report_one_shot import digest, read_json, write_json
from test_report_combined_matrix import MatrixFixture, branch


def test_original_margin_and_control_tie_are_preserved():
    row = {"d0": branch("d0", 40), "d1": branch("d1", 40), "l": branch("l", 40),
           "f": branch("raw", 40.03), "cleaned_f": branch("clean", 40.03),
           "stage03_accepted": False, "proposal_job_key": "job"}
    assert analysis.selected_without_rejected_cleanup(row) == ("d1", 40)
    assert analysis.selected_without_rejected_cleanup(row, retained_jobs={"job"}) == ("d1", 40)
    row["f"] = branch("raw", 40.05)
    assert analysis.selected_without_rejected_cleanup(row) == ("d1", 40)
    row.update(d1=branch("d1", 45), l=branch("l", 45), f=branch("raw", 45),
               cleaned_f=branch("clean", 45), stage03_accepted=True)
    assert analysis.selected_without_rejected_cleanup(row) == ("d1", 45)


def rescue_fixture(tmp_path):
    data = MatrixFixture(tmp_path)
    for name in data.names:
        data.control(name)
    data.cell("plain", "p", final_score=39, cleaned_score=45, selected="cleaned_f")
    data.cell("plain", "q", final_score=65, cleaned_score=66, selected="cleaned_f")
    return data


def test_rejected_rescue_counts_loss_but_keeps_accepted_cleanup(tmp_path):
    data = rescue_fixture(tmp_path)
    report, rows = analysis.analyze(data.output, require_complete=True)
    assert report["status"] == "complete"
    condition = report["conditions"][0]
    assert condition["actual_h_mean"] == 55.5
    assert condition["accepted_only_mean"] == 54
    assert condition["mean_score_lost_pp"] == 1.5
    assert condition["affected_problems"] == 1
    assert condition["cache_preserving_mean_loss_pp"] == 1.5
    assert [row["score_lost_pp"] for row in rows] == [3, 0]
    omitted = report["physical_work"]["omitted"]
    assert omitted["unique_jobs"] == 1
    assert omitted["recorded_counters"]["attempts"] == 3
    assert omitted["recorded_counters"]["lean_candidate_checks"] == 2


def test_shared_rejected_proof_is_one_physical_job_across_arms(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain", "cards"])
    for name in data.names:
        data.control(name)
    for arm in data.arms:
        data.cell(arm, "p", final_score=39, cleaned_score=42, proof="same rejected proof", selected="d1")
        data.cell(arm, "q")
    report, _ = analysis.analyze(data.output, require_complete=True)
    assert report["physical_work"]["omitted"]["unique_jobs"] == 1
    assert report["physical_work"]["omitted"]["recorded_counters"]["attempts"] == 3
    assert len(report["omitted_jobs"][0]["origins"]) == 2
    assert [row["globally_omittable_jobs_referenced"] for row in report["conditions"]] == [1, 1]
    assert all(row["mean_score_lost_pp"] == 0 for row in report["conditions"])


def test_job_needed_by_control_or_accepted_origin_is_never_omitted(tmp_path):
    data = MatrixFixture(tmp_path)
    for name in data.names:
        data.control(name)
    data.cell("plain", "p", final_score=40, proof=data.packs["p"]["proof"], selected="d1")
    data.cell("plain", "q", final_score=65, cleaned_score=66, selected="cleaned_f")
    report, _ = analysis.analyze(data.output, require_complete=True)
    assert report["physical_work"]["omitted"]["unique_jobs"] == 0
    assert report["conditions"][0]["mean_score_lost_pp"] == 0


def test_partial_matrix_masks_global_work_and_only_incomplete_condition_mean(tmp_path):
    data = MatrixFixture(tmp_path, arms=["plain", "cards"])
    for name in data.names:
        data.control(name)
        data.cell("plain", name)
    data.cell("cards", "p")
    report, _ = analysis.analyze(data.output)
    assert report["status"] == "incomplete"
    assert report["conditions"][0]["mean_score_lost_pp"] == 0
    assert report["conditions"][1]["mean_score_lost_pp"] is None
    assert report["physical_work"]["omitted"] is None
    assert report["conditions"][0]["cache_preserving_mean_loss_pp"] is None
    with pytest.raises(ValueError, match="all declared"):
        analysis.analyze(data.output, require_complete=True)


def test_historical_omitted_work_is_not_new_spend_and_receipt_is_checked(tmp_path):
    data = rescue_fixture(tmp_path)
    baseline, _ = analysis.analyze(data.output, require_complete=True)
    key = baseline["omitted_jobs"][0]["job_key"]
    folder = data.output / "jobs" / key
    job = read_json(folder / "result.json")
    receipt = {"status": "complete", "jobs": {key: {"job_key": key,
        "destination_directory": str(folder), "result_sha256": digest(folder / "result.json"),
        "historical_counters": job["counters"]}}}
    path = data.output / "validation" / "cleanup_reuse.json"
    path.parent.mkdir()
    write_json(path, receipt)
    report, _ = analysis.analyze(data.output, receipts=[path], require_complete=True)
    assert report["physical_work"]["omitted_copied_historical"]["unique_jobs"] == 1
    assert report["physical_work"]["omitted_without_recognized_copy_receipt"]["unique_jobs"] == 0
    assert report["omitted_jobs"][0]["copied_historical"]
    automatic, _ = analysis.analyze(data.output, require_complete=True)
    assert automatic["physical_work"]["omitted_copied_historical"]["unique_jobs"] == 1
    receipt["jobs"][key]["result_sha256"] = "incorrect"
    write_json(path, receipt)
    with pytest.raises(ValueError, match="differs from its receipt"):
        analysis.analyze(data.output, receipts=[path])


def test_missing_registered_shared_origin_rejects_physical_accounting(tmp_path):
    data = rescue_fixture(tmp_path)
    manifest = read_json(data.output / "jobs.json")
    for job in manifest["jobs"].values():
        if any(origin["kind"] == "proposal" for origin in job["origins"]):
            job["origins"] = []
    write_json(data.output / "jobs.json", manifest)
    with pytest.raises(ValueError, match="missing a recorded cell origin"):
        analysis.analyze(data.output, require_complete=True)


def test_physical_job_shared_with_accepted_origin_is_retained():
    config = {"controls": {"p": "control"}}
    records = {"a": {"stage03_accepted": True, "proposal_job_key": "shared"},
               "b": {"stage03_accepted": False, "proposal_job_key": "shared"}}
    manifest = {"shared": {"origins": [{"kind": "proposal", "cell_key": key} for key in records]}}
    retained, omitted, _ = analysis.classify_jobs(config, records, records, {"shared": {}}, manifest)
    assert retained == {"control", "shared"}
    assert not omitted
