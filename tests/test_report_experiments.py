"""Reports must retain missing coverage and distinguish sequential score gains."""

import csv
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from proof_eval.optimization.reporting import (
    build_comparison,
    main,
    stage_report,
    write_comparison,
    write_stage_report,
)


def evaluation(score, code, versions, *, tokens=10, status="passed"):
    return {
        "status": status,
        "candidate": {"length": tokens, "code_sha256": code},
        "scores": {
            "length_reduction_pct": 0.0,
            "heartbeat_reduction_pct": None if score is None else score * 3 - 100,
            "compatibility_pct": 100.0 if score is not None else None,
            "combined_pct": score,
        },
        "per_version": {v: {"status": "passed", "passed": True} for v in versions},
    }


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.dataset = self.root / "dataset.jsonl"
        self.rows = [
            {"name": "a", "source": "one", "version_info": [{"v1": "x"}, {"v2": "y"}]},
            {"name": "b", "source": "two", "version_info": [{"v1": "z"}]},
        ]
        self.dataset.write_text("".join(json.dumps(row) + "\n" for row in self.rows))
        self.first = self.root / "01_linter_deletion"
        self.second = self.root / "02_wrappers"
        self._stage(self.first, "lint", [(20, 40), (30, 30)], "original", "first")
        self._stage(self.second, "wrappers", [(40, 45), (30, 35)], "first", "second")

    def _stage(self, directory, method, scores, before, after):
        directory.mkdir()
        config = {
            "method": method,
            "dataset_sha256": hashlib.sha256(self.dataset.read_bytes()).hexdigest(),
            "budget": {"rounds": 4, "trials": 12, "sites": 3, "min_gain": 0.05},
            "workers": 2,
        }
        (directory / "config.json").write_text(json.dumps(config))
        for index, (row, (initial, final)) in enumerate(zip(self.rows, scores)):
            versions = [v for item in row["version_info"] for v in item]
            record = {
                "name": row["name"],
                "source": row["source"],
                "initial": evaluation(initial, before + row["name"], versions),
                "final": evaluation(final, after + row["name"], versions),
                "changed": initial != final,
                "attempts": 2,
                "rounds": 1,
                "stop_reason": "trial_limit" if index == 0 else "no_improving_proposal",
                "accepted_edits": 1,
                "analysis_requests": 1,
                "elapsed_seconds": 2.5,
            }
            (directory / f"problem_{index}.json").write_text(json.dumps(record))

    def _record(self, directory, index=0):
        path = directory / f"problem_{index}.json"
        return path, json.loads(path.read_text())

    def test_previous_and_original_gains_have_distinct_denominators(self):
        report = stage_report(self.second, self.first, dataset=self.dataset)
        self.assertEqual(report["full_benchmark_final_mean"]["combined_pct"], 40)
        self.assertEqual(report["delta_previous_pp"]["combined_pct"], 5)
        self.assertEqual(report["delta_original_pp"]["combined_pct"], 15)
        self.assertEqual(report["passed_version_checks"], 3)
        self.assertEqual(report["expected_version_checks"], 3)
        self.assertEqual(report["cap_stopped_problems"], 1)
        self.assertIsNone(report["counters"]["lean_candidate_checks"])

    def test_missing_problem_cannot_be_reported_as_full_benchmark_gain(self):
        (self.second / "problem_1.json").unlink()
        report = stage_report(self.second, self.first, dataset=self.dataset)
        self.assertFalse(report["complete_benchmark"])
        self.assertIsNone(report["full_benchmark_final_mean"]["combined_pct"])
        self.assertIsNone(report["delta_previous_pp"]["combined_pct"])
        self.assertEqual(report["measured_subset_final_mean"]["combined_pct"], 45)
        self.assertEqual(report["missing_names"], ["b"])
        self.assertEqual(report["version_check_statuses"], {"missing": 1, "passed": 2})

    def test_unavailable_score_is_not_silently_dropped_from_denominator(self):
        path, record = self._record(self.second, 1)
        record["final"] = evaluation(None, "secondb", ["v1"], status="incomplete")
        path.write_text(json.dumps(record))
        report = stage_report(self.second, self.first, dataset=self.dataset)
        self.assertEqual(report["fully_scored_problems"], 1)
        self.assertEqual(report["unscored_names"], ["b"])
        self.assertIsNone(report["delta_original_pp"]["combined_pct"])

    def test_coverage_uses_actual_version_statuses_even_when_scores_exist(self):
        path, record = self._record(self.second)
        del record["final"]["per_version"]["v2"]
        path.write_text(json.dumps(record))
        report = stage_report(self.second, self.first, dataset=self.dataset)
        self.assertEqual(report["passed_version_checks"], 2)
        self.assertEqual(report["version_check_statuses"]["missing"], 1)
        self.assertFalse(report["complete_benchmark"])
        self.assertIsNone(report["full_benchmark_final_mean"]["combined_pct"])

    def test_failed_primary_zero_stays_in_benchmark_mean(self):
        path, record = self._record(self.second)
        record["final"] = evaluation(0, "seconda", [], status="failed")
        record["final"]["scores"] = {key: 0.0 for key in record["final"]["scores"]}
        record["final"]["per_version"] = {"v1": {"status": "failed", "passed": False}}
        path.write_text(json.dumps(record))
        report = stage_report(self.second, self.first, dataset=self.dataset)
        self.assertTrue(report["complete_benchmark"])
        self.assertEqual(report["full_benchmark_final_mean"]["combined_pct"], 17.5)
        self.assertEqual(
            report["version_check_statuses"], {"failed": 1, "missing": 1, "passed": 1}
        )

    def test_mismatched_stage_input_and_dataset_hash_fail_loudly(self):
        path, record = self._record(self.second)
        record["initial"]["candidate"]["code_sha256"] = "unrelated"
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "differs from selected previous"):
            stage_report(self.second, self.first, dataset=self.dataset)
        config_path = self.second / "config.json"
        config = json.loads(config_path.read_text())
        config["dataset_sha256"] = "wrong"
        config_path.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, "Dataset fingerprint"):
            stage_report(self.second, dataset=self.dataset)

    def test_comparison_preserves_original_evidence_files(self):
        original = self.root / "comparison.json"
        original.write_text("original evidence\n")
        result = write_comparison([self.first, self.second], dataset=self.dataset)
        self.assertEqual(original.read_text(), "original evidence\n")
        self.assertEqual(len(result["stages"]), 2)
        self.assertTrue((self.root / "deterministic_comparison.csv").exists())
        self.assertIn(
            "gain_previous_pp", (self.root / "deterministic_comparison.csv").read_text()
        )
        self.assertEqual(result["original_control_mean"]["combined_pct"], 25)

    def test_repeated_stage_basenames_keep_distinct_paths_in_json_and_csv(self):
        sweep_a = self.root / "sweep_01" / "01_wrappers"
        sweep_b = self.root / "sweep_02" / "01_wrappers"
        sweep_a.parent.mkdir()
        sweep_b.parent.mkdir()
        self._stage(sweep_a, "wrappers", [(45, 46), (35, 36)], "second", "sweep_a")
        self._stage(sweep_b, "wrappers", [(46, 47), (36, 37)], "sweep_a", "sweep_b")
        result = write_comparison(
            [sweep_a, sweep_b],
            output_root=self.root,
            dataset=self.dataset,
            baseline=self.first,
        )
        self.assertEqual(
            [stage["stage"] for stage in result["stages"]],
            ["01_wrappers", "01_wrappers"],
        )
        paths = [stage["stage_path"] for stage in result["stages"]]
        self.assertEqual(len(set(paths)), 2)
        self.assertTrue(paths[0].endswith("sweep_01/01_wrappers"))
        self.assertTrue(paths[1].endswith("sweep_02/01_wrappers"))
        self.assertTrue(all(not Path(path).is_absolute() for path in paths))
        with (self.root / "deterministic_comparison.csv").open() as stream:
            self.assertEqual(
                [row["stage_path"] for row in csv.DictReader(stream)], paths
            )

    def test_wall_time_sums_sessions_separately_from_worker_time(self):
        (self.second / "run.json").write_text(
            json.dumps(
                {
                    "status": "finished",
                    "sessions": [{"elapsed_seconds": 2.0}, {"elapsed_seconds": 0.125}],
                }
            )
        )
        report = stage_report(self.second, self.first, dataset=self.dataset)
        self.assertEqual(report["counters"]["elapsed_seconds"], 5.0)
        self.assertEqual(report["counters"]["wall_seconds"], 2.125)
        (self.second / "run.json").write_text(
            json.dumps(
                {
                    "status": "running",
                    "sessions": [
                        {"elapsed_seconds": 2.0},
                        {"started_at": "2026-10-02T00:00:00Z"},
                    ],
                }
            )
        )
        self.assertIsNone(
            stage_report(self.second, dataset=self.dataset)["counters"]["wall_seconds"]
        )
        self.assertIsNone(
            stage_report(self.first, dataset=self.dataset)["counters"]["wall_seconds"]
        )

    def test_candidate_outcomes_distinguish_failure_timeout_and_bound_pruning(self):
        events = []
        cases = [
            ("invalid", None, False, None, False),
            ("failed", "failed", False, 0, False),
            ("failed", "timeout", False, 0, False),
            ("incomplete", "passed", False, 35, False),
            ("incomplete", "unavailable", False, None, False),
            ("passed", "passed", True, 50, True),
            ("passed", "passed", True, 40, False),
            ("incomplete", "passed", True, 50, False),
        ]
        for status, primary_status, requested, bound, improves in cases:
            result = evaluation(
                40 if status == "passed" else None, "proof", ["v1"], status=status
            )
            result["primary_version"] = "v1"
            result["per_version"]["v1"]["status"] = primary_status
            events.append(
                {
                    "name": "a",
                    "kind": "candidate",
                    "evaluation": result,
                    "all_versions_requested": requested,
                    "primary_upper_bound": bound,
                    "improves_incumbent": improves,
                }
            )
        (self.second / "trials_a.jsonl").write_text(
            "".join(json.dumps(event) + "\n" for event in events)
        )
        report = stage_report(self.second, self.first, dataset=self.dataset)
        self.assertEqual(
            report["candidate_status_counts"],
            {"failed": 2, "incomplete": 3, "invalid": 1, "passed": 2},
        )
        self.assertEqual(
            report["candidate_outcome_counts"],
            {
                "invalid_candidate": 1,
                "primary_failed": 1,
                "primary_timeout": 1,
                "primary_bound_pruned": 1,
                "primary_evaluation_unavailable_or_unscored": 1,
                "fully_scored_improvement": 1,
                "fully_scored_no_improvement": 1,
                "full_evaluation_unavailable_or_unscored": 1,
            },
        )
        self.assertEqual(report["primary_screened_events"], 5)

    def test_discovery_outcomes_and_errors_are_reported_separately(self):
        events = [
            {
                "name": "a",
                "kind": "proposal_set",
                "discovery": {
                    "status": "discovery_failed",
                    "diagnostics": [
                        {
                            "kind": "tactic_outcome",
                            "tactic": "ring",
                            "status": "unavailable",
                        },
                        {
                            "kind": "tactic_outcome",
                            "tactic": "omega",
                            "status": "solved",
                        },
                        {
                            "kind": "tactic_outcome",
                            "tactic": "omega",
                            "status": "failed",
                        },
                        {
                            "kind": "tactic_outcome",
                            "tactic": "ring",
                            "status": "not_observed",
                        },
                        {"kind": "discovery_error", "message": "Instrumentation error"},
                    ],
                },
            },
            {"name": "b", "kind": "discovery_error", "message": "Analysis unavailable"},
        ]
        (self.second / "trials_a.jsonl").write_text(
            "".join(json.dumps(event) + "\n" for event in events)
        )
        report = write_stage_report(self.second, self.first, dataset=self.dataset)
        self.assertEqual(
            report["tactic_outcome_status_counts"],
            {"failed": 1, "not_observed": 1, "solved": 1, "unavailable": 1},
        )
        self.assertEqual(
            report["tactic_outcomes_by_tactic"]["ring"],
            {"not_observed": 1, "unavailable": 1},
        )
        self.assertEqual(
            report["tactic_outcomes_by_source"]["one"],
            report["tactic_outcome_status_counts"],
        )
        self.assertEqual(report["discovery_status_counts"], {"discovery_failed": 1})
        self.assertEqual(report["proposal_error_count"], 2)
        self.assertEqual(
            report["proposal_error_counts_by_kind"],
            {"diagnostic:discovery_error": 1, "event:discovery_error": 1},
        )
        self.assertIn("Decision outcomes", (self.second / "README.md").read_text())

    def _example_logs(self, *, accept_second=False):
        parent = "theorem example : True := by\n  exact h"
        start = parent.index("exact h")
        parent_sha = hashlib.sha256(parent.encode()).hexdigest()
        previous_path, previous = self._record(self.first)
        previous["proof"] = parent
        previous["final"]["candidate"]["code_sha256"] = parent_sha
        previous_path.write_text(json.dumps(previous))
        path, record = self._record(self.second)
        record["initial"]["candidate"]["code_sha256"] = parent_sha
        events = []
        for trial, replacement, score in [(1, "assumption", 41), (2, "trivial", 49)]:
            proof = parent[:start] + replacement
            result = evaluation(
                score, hashlib.sha256(proof.encode()).hexdigest(), ["v1", "v2"]
            )
            events.append(
                {
                    "name": "a",
                    "kind": "candidate",
                    "trial": trial,
                    "round": 0,
                    "parent_sha256": parent_sha,
                    "proof": proof,
                    "evaluation": result,
                    "edits": [
                        {
                            "start": start,
                            "end": len(parent),
                            "replacement": replacement,
                            "reason": "menu",
                        }
                    ],
                    "improves_incumbent": True,
                    "all_versions_requested": True,
                }
            )
        selected = events[1 if accept_second else 0]
        record["final"], record["proof"] = selected["evaluation"], selected["proof"]
        path.write_text(json.dumps(record))
        events.append(
            {"name": "a", "kind": "accepted", "trial": selected["trial"], "round": 0}
        )
        log = self.second / "trials_a.jsonl"
        log.write_text("".join(json.dumps(event) + "\n" for event in events))
        return parent, events, log

    def test_example_uses_accepted_trial_not_larger_unselected_improvement(self):
        self._example_logs()
        report = write_stage_report(self.second, self.first, dataset=self.dataset)
        example = report["accepted_example"]
        self.assertEqual(example["trial"], 1)
        self.assertEqual(example["before"], "exact h")
        self.assertEqual(example["after"], "assumption")
        self.assertEqual(example["combined_gain_pp"], 1)
        self.assertEqual(example["edit_count"], 1)
        self.assertIn("complete candidate", example["gain_scope"])
        self.assertIn("Accepted example", (self.second / "README.md").read_text())

    def test_example_reconstructs_later_parent_before_measuring_transition_gain(self):
        _, events, log = self._example_logs()
        accepted = events[0]
        parent = accepted["proof"]
        start = parent.index("assumption")
        proof = parent[:start] + "trivial"
        result = evaluation(
            43, hashlib.sha256(proof.encode()).hexdigest(), ["v1", "v2"]
        )
        events += [
            {
                "name": "a",
                "kind": "candidate",
                "trial": 3,
                "round": 1,
                "parent_sha256": hashlib.sha256(parent.encode()).hexdigest(),
                "proof": proof,
                "evaluation": result,
                "edits": [
                    {"start": start, "end": len(parent), "replacement": "trivial"}
                ],
            },
            {"name": "a", "kind": "accepted", "trial": 3, "round": 1},
        ]
        log.write_text("".join(json.dumps(event) + "\n" for event in events))
        example = stage_report(self.second, self.first, dataset=self.dataset)[
            "accepted_example"
        ]
        self.assertEqual(example["trial"], 3)
        self.assertEqual(example["before"], "assumption")
        self.assertEqual(example["combined_gain_pp"], 2)

    def test_multi_edit_and_unreconstructable_examples_are_omitted(self):
        _, events, log = self._example_logs()
        events[0]["edits"].append({"start": 0, "end": 0, "replacement": ""})
        log.write_text("".join(json.dumps(event) + "\n" for event in events))
        self.assertIsNone(
            stage_report(self.second, self.first, dataset=self.dataset)[
                "accepted_example"
            ]
        )
        events[0]["edits"].pop()
        events[0]["edits"][0]["replacement"] = "different proof"
        log.write_text("".join(json.dumps(event) + "\n" for event in events))
        self.assertIsNone(
            stage_report(self.second, self.first, dataset=self.dataset)[
                "accepted_example"
            ]
        )

    def test_example_can_recover_initial_proof_from_saved_input_path(self):
        parent, _, _ = self._example_logs()
        input_path = self.root / "input.jsonl"
        input_path.write_text(json.dumps({"name": "a", "proof": parent}) + "\n")
        config_path = self.second / "config.json"
        config = json.loads(config_path.read_text())
        config["input_path"] = str(input_path)
        config_path.write_text(json.dumps(config))
        example = stage_report(self.second, dataset=self.dataset)["accepted_example"]
        self.assertEqual(example["before"], "exact h")

    def test_report_records_screening_without_calling_it_missing_infrastructure(self):
        (self.second / "trials_a.jsonl").write_text(
            json.dumps({"kind": "candidate", "all_versions_requested": False}) + "\n"
        )
        report = write_stage_report(self.second, self.first, dataset=self.dataset)
        text = (self.second / "README.md").read_text()
        self.assertEqual(report["primary_screened_events"], 1)
        self.assertIn("3/3 required version checks", text)
        self.assertIn("do not establish a global optimum", text)
        self.assertIn("not wall time", text)
        self.assertTrue((self.second / "report.json").exists())

    def test_duplicate_or_nonfinite_records_are_rejected(self):
        path, record = self._record(self.second)
        (self.second / "problem_duplicate.json").write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "Duplicate problem"):
            stage_report(self.second, dataset=self.dataset)
        (self.second / "problem_duplicate.json").unlink()
        record["final"]["scores"]["combined_pct"] = float("nan")
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "finite"):
            stage_report(self.second, dataset=self.dataset)

    def test_cli_can_write_both_kinds_of_report(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(
                main(
                    [
                        "--stage",
                        str(self.second),
                        "--previous",
                        str(self.first),
                        "--dataset",
                        str(self.dataset),
                    ]
                ),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "--stages",
                        str(self.first),
                        str(self.second),
                        "--dataset",
                        str(self.dataset),
                    ]
                ),
                0,
            )
        with self.assertRaisesRegex(ValueError, "distinct stages"):
            build_comparison([self.first, self.first], dataset=self.dataset)


if __name__ == "__main__":
    unittest.main()
