"""Saved-only failure categories, usage accounting, and partial-run handling."""
import hashlib
import json

from analyze_one_shot_failures import analyze, classify, main, markdown, usage_summary


def test_usage_split_requires_actual_consistent_provider_counts():
    result = usage_summary({"content": "", "reasoning_characters": 99999, "usage": {
        "completion_tokens": 32768, "completion_tokens_details": {"reasoning_tokens": 32768}}}, 32768)
    assert result["non_reasoning_completion_tokens_derived"] == 0
    assert result["all_reported_completion_tokens_are_reasoning"]
    assert result["completion_budget_fraction"] == 1
    missing = usage_summary({"content": "theorem t", "reasoning_characters": 99999,
                             "usage": {"completion_tokens": 200}}, 1000)
    assert missing["reasoning_tokens"] is None
    assert missing["non_reasoning_completion_tokens_derived"] is None
    assert missing["split_status"] == "unavailable"
    broken = usage_summary({"usage": {"completion_tokens": 100,
                           "completion_tokens_details": {"reasoning_tokens": 101}}}, 1000)
    assert broken["split_status"] == "inconsistent"
    assert broken["non_reasoning_completion_tokens_derived"] is None


def test_multiversion_failures_preserve_authoritative_passed_status_and_ignore_warnings():
    evaluation = {"status": "passed", "per_version": {
        "v1": {"status": "passed", "passed": True, "diagnostics": [{"severity": "warning", "data": "declaration uses 'sorry'"}]},
        "v2": {"status": "failed", "passed": False, "diagnostics": [
            {"severity": "error", "data": "Unknown identifier `new_lemma`"},
            {"severity": "error", "data": "Application type mismatch: The argument\nsecret proof text"},
            {"severity": "error", "kind": "Tactic.unsolvedGoals", "data": "unsolved goals\n⊢ True"},
            {"severity": "error", "message": "Expected exactly one verified target heartbeat marker"}]}}}
    out = classify(evaluation, {"status": "received"}, result_exists=True, generation_exists=True)
    assert out["primary_category"] == "lean_missing_name"
    assert {"lean_missing_name", "lean_type_mismatch", "lean_unsolved_goals"} <= set(out["heuristic_categories"])
    assert "verification_rejected_sorry" not in out["heuristic_categories"]
    assert all(item["version"] == "v2" for item in out["evidence"])
    assert "secret proof text" not in json.dumps(out)
    assert evaluation["status"] == "passed"


def test_statement_contract_and_infrastructure_classification():
    def classify_result(evaluation):
        return classify(evaluation, {"status": "received"}, result_exists=True, generation_exists=True)
    statement = classify_result({"status": "invalid", "diagnostics": ["Candidate must preserve the exact benchmark statement"]})
    assert statement["primary_category"] == "statement_violation"
    contract = classify_result({"status": "invalid", "diagnostics": ["query_tactic_in_final_output"]})
    assert contract["primary_category"] == "output_contract_violation"
    unavailable = classify_result({"status": "incomplete", "per_version": {"v1": {
        "status": "unavailable", "diagnostics": [{"severity": "error", "data": "Unknown identifier in a broken prefix"}]}}})
    assert unavailable["heuristic_categories"] == ["evaluation_unavailable"]


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def test_partial_analysis_is_read_only_groups_cells_and_never_exports_reasoning(tmp_path):
    root = tmp_path / "run"
    names, model, arms = ["a", "b"], "model", ["plain", "goals"]
    _write(root / "config.json", {"names": names, "models": [model], "arms": arms, "max_tokens": 100})
    _write(root / "run.json", {"status": "running"})
    index = {}
    for name in names:
        _write(root / "inputs" / (name + ".json"), {"name": name, "row": {"name": name, "source": "source-" + name}, "proof": "theorem " + name})
        for arm in arms:
            key = hashlib.sha256((name + arm).encode()).hexdigest()
            index[json.dumps([name, arm, model])] = key
            _write(root / "cells" / key / "request.json", {"name": name, "model": model, "arm": arm, "max_tokens": 100})
    _write(root / "cell_index.json", index)
    first = root / "cells" / index[json.dumps(["a", "plain", model])]
    generation = {"status": "received", "finish_reason": "stop", "content": "theorem a", "reasoning_content": "DO_NOT_EXPORT_REASONING",
                  "usage": {"completion_tokens": 20, "completion_tokens_details": {"reasoning_tokens": 10}}}
    _write(first / "generation.json", generation)
    _write(first / "result.json", {"name": "a", "model": model, "arm": "plain", "source": "source-a", "generation": generation,
        "extracted_proof": "\n theorem a \n", "accepted": False, "all_versions_passed": True,
        "evaluation": {"status": "passed", "per_version": {"v1": {"status": "passed", "passed": True}}}})
    second = root / "cells" / index[json.dumps(["a", "goals", model])]
    _write(second / "generation.json", {"status": "received", "finish_reason": "length", "content": "",
        "usage": {"completion_tokens": 100, "completion_tokens_details": {"reasoning_tokens": 100}}})
    third = root / "cells" / index[json.dumps(["b", "plain", model])]
    _write(third / "request_started.json", {})
    before = {p: p.read_bytes() for p in root.rglob("*.json")}
    report = analyze(root)
    assert report["recorded_results"] == 1
    assert report["planned_cells"] == 4
    assert report["missing_result_cells"] == 3
    assert report["snapshot_status"] == "partial_or_unreadable"
    assert report["overall"]["unchanged_all_versions_passed_cells"] == 1
    assert report["overall"]["changed_all_versions_passed_cells"] == 0
    assert report["overall"]["truncated_with_empty_final_cells"] == 1
    assert report["overall"]["primary_category_counts"]["pending_generation"] == 1
    assert report["overall"]["primary_category_counts"]["not_started"] == 1
    assert len(report["groups"]["source"]) == 2
    assert "DO_NOT_EXPORT_REASONING" not in json.dumps(report)
    assert "theorem a" not in json.dumps(report)
    assert before == {p: p.read_bytes() for p in root.rglob("*.json")}
    output = tmp_path / "reports"
    main(["--input", str(root), "--output", str(output)])
    assert (output / "failure_analysis.json").exists()
    report_text = (output / "FAILURE_ANALYSIS.md").read_text()
    assert "Unchanged returned incumbents" in report_text
    assert "(<../run/cells/" in report_text
    assert str(tmp_path) not in report_text
    default_text = markdown(report)
    assert "(<cells/" in default_text
    assert str(tmp_path) not in default_text


def test_changed_valid_and_unreadable_artifacts_are_not_hidden(tmp_path):
    root = tmp_path / "run"
    key = "a" * 64
    _write(root / "inputs" / "a.json", {"name": "a", "row": {"source": "s"}, "proof": "theorem a := by trivial"})
    folder = root / "cells" / key
    _write(folder / "result.json", {"name": "a", "model": "m", "arm": "plain", "extracted_proof": "theorem a := by exact True.intro",
        "all_versions_passed": True, "evaluation": {"status": "passed", "per_version": {"v": {"status": "passed", "passed": True}}}})
    (folder / "generation.json").write_text('{"reasoning": "PRIVATE_IN_MALFORMED_JSON"')
    report = analyze(root)
    assert report["overall"]["changed_all_versions_passed_cells"] == 1
    assert report["overall"]["primary_category_counts"]["artifact_error"] == 1
    assert report["artifact_issues"]
    assert "PRIVATE_IN_MALFORMED_JSON" not in json.dumps(report)
