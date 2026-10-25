"""API contracts that prevent invalid rewards and hidden reference recompilation."""

import concurrent.futures
import copy
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from proof_eval.verification.api import EvaluationNotReady, Evaluator
from proof_eval.verification.references import check_references


class FakeBackend:
    def __init__(self):
        self.calls = []
        self.revision = "original"
        self.statuses = {}
        self.reference_cost = {"v1": 1000, "v2": 2000}
        self.candidate_cost = {"v1": 250, "v2": 1000}
        self.change_during_check = False
        self.delay = 0

    def fingerprint(self, row, version, project):
        return {"version": version, "revision": self.revision}

    def check(self, row, code, version, project):
        is_reference = code == row["src"]
        self.calls.append((version, is_reference, code))
        if self.delay:
            time.sleep(self.delay)
        if self.change_during_check:
            self.revision += "changed"
        status = self.statuses.get(version, "passed")
        heartbeats = (self.reference_cost if is_reference else self.candidate_cost)[
            version
        ]
        return {
            "status": status,
            "passed": status == "passed",
            "heartbeats": heartbeats if status == "passed" else None,
            "heartbeats_raw": heartbeats * 1000 if status == "passed" else None,
            "diagnostics": [],
        }


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.row = {
            "name": "toy",
            "source": "toy-project",
            "statement": "theorem toy : True",
            "src": "theorem toy : True := by exact True.intro",
            # Deliberately independent of src: the API must trust the input
            # dataset's reference measurement instead of replacing it.
            "proof_length": 10,
            "version_info": [{"v1": "a" * 40}, {"v2": "b" * 40}],
        }
        self.dataset_path = self.root / "benchmark.jsonl"
        self.dataset_path.write_text(json.dumps(self.row) + "\n")
        (self.root / "benchmark_heartbeats.jsonl").write_text(
            json.dumps({"name": "toy", "heartbeat": 99999}) + "\n"
        )
        self.config_path = self.root / "environments.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "projects": [
                        {"source": "toy-project", "version": version, "path": version}
                        for version in ("v1", "v2")
                    ]
                }
            )
        )
        self.backend = FakeBackend()
        self.evaluator = self.make_evaluator()
        self.code = "theorem toy : True := by trivial"

    def make_evaluator(self, **overrides):
        values = {
            "dataset_path": self.dataset_path,
            "environments_path": self.config_path,
            "cache_dir": self.root / "cache",
            "backend": self.backend,
        }
        values.update(overrides)
        return Evaluator(**values)

    def prepare(self):
        result = self.evaluator.prepare_reference("toy")
        self.assertEqual(result["status"], "prepared")
        return result

    def test_evaluate_never_measures_reference_or_uses_published_heartbeat(self):
        result = self.evaluator.evaluate("toy", self.code)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["reference"]["length"], 10)
        self.assertEqual(result["reference"]["published_heartbeats"], 99999)
        self.assertEqual(result["scores"]["length_reduction_pct"], 80)
        self.assertIsNone(result["scores"]["heartbeat_reduction_pct"])
        self.assertIsNone(result["scores"]["combined_pct"])
        self.assertEqual(len(self.backend.calls), 2)
        self.assertFalse(any(is_reference for _, is_reference, _ in self.backend.calls))
        with self.assertRaises(EvaluationNotReady):
            self.evaluator.reward("toy", self.code)

    def test_reference_preparation_is_explicit_and_reused(self):
        first = self.prepare()
        second = self.prepare()
        self.assertEqual(len(self.backend.calls), 2)
        self.assertFalse(first["versions"]["v1"]["cached"])
        self.assertTrue(second["versions"]["v1"]["cached"])
        self.evaluator.get_reference("toy")
        self.assertEqual(len(self.backend.calls), 2)
        self.evaluator.prepare_reference("toy", versions="primary", refresh=True)
        self.assertEqual(len(self.backend.calls), 3)

    def reference_guard_inputs(self):
        prepared = self.prepare()
        row = self.evaluator.dataset.get("toy")
        pack = {
            "name": "toy",
            "row": row,
            "incumbent": {
                "per_version": {
                    version: {"reference": reference}
                    for version, reference in prepared["versions"].items()
                }
            },
        }
        contexts = {
            version: self.evaluator._context(row, version)[2]
            for version in ("v1", "v2")
        }
        return pack, {"contexts": {"toy": contexts}}

    def test_reference_guard_scans_each_version_once_but_never_reuses_an_old_scan(self):
        pack, base = self.reference_guard_inputs()
        with patch.object(
            self.backend, "fingerprint", wraps=self.backend.fingerprint
        ) as scanned:
            check_references(self.evaluator, pack, base)
            check_references(self.evaluator, pack, base)
        self.assertEqual(
            [call.args[1] for call in scanned.call_args_list],
            ["v1", "v2", "v1", "v2"],
        )
        self.assertEqual(len(self.backend.calls), 2)
        self.backend.revision = "changed dependency"
        with self.assertRaisesRegex(ValueError, "Cached reference unavailable"):
            check_references(self.evaluator, pack, base)
        self.assertEqual(len(self.backend.calls), 2)

    def test_reference_guard_still_rejects_changed_reference_context_and_cohort(self):
        pack, base = self.reference_guard_inputs()
        wrong_pack = copy.deepcopy(pack)
        wrong_pack["row"]["proof_length"] += 1
        with self.assertRaisesRegex(ValueError, "Prepared dataset row changed"):
            check_references(self.evaluator, wrong_pack, base)
        wrong = copy.deepcopy(base)
        wrong["contexts"]["toy"]["v2"] = "different context"
        with self.assertRaisesRegex(ValueError, "Environment changed"):
            check_references(self.evaluator, pack, wrong)
        wrong["contexts"]["toy"].pop("v2")
        with self.assertRaisesRegex(ValueError, "version cohort changed"):
            check_references(self.evaluator, pack, wrong)
        key = base["contexts"]["toy"]["v2"]
        record = self.evaluator.store.read("references", key)
        record["heartbeats"] += 1
        self.evaluator.store.write("references", key, record)
        with self.assertRaisesRegex(ValueError, "Cached reference changed"):
            check_references(self.evaluator, pack, base)
        self.assertEqual(len(self.backend.calls), 2)

    def test_reference_snapshot_keeps_the_existing_reference_response(self):
        self.prepare()
        original = self.evaluator.get_reference("toy")
        snapshot, contexts = self.evaluator.reference_snapshot("toy")
        self.assertEqual(snapshot, original)
        for version, key in contexts.items():
            self.assertEqual(
                snapshot["versions"][version],
                self.evaluator.store.read("references", key),
            )

    def test_component_scores_use_local_reference_and_primary_version(self):
        self.prepare()
        result = self.evaluator.evaluate("toy", self.code)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(
            result["scores"],
            {
                "length_reduction_pct": 80,
                "heartbeat_reduction_pct": 75,
                "compatibility_pct": 100,
                "combined_pct": 85,
            },
        )
        self.assertEqual(result["per_version"]["v2"]["heartbeat_reduction_pct"], 50)
        self.assertAlmostEqual(self.evaluator.reward("toy", self.code), 0.85)
        self.assertEqual(len(self.backend.calls), 4)

    def test_candidate_cache_can_be_scored_after_reference_is_prepared(self):
        self.evaluator.evaluate("toy", self.code)
        self.prepare()
        result = self.evaluator.evaluate("toy", self.code)
        self.assertEqual(result["status"], "passed")
        self.assertTrue(all(r["cached"] for r in result["per_version"].values()))
        self.assertEqual(len(self.backend.calls), 4)

    def test_stale_environment_does_not_reuse_or_remeasure_reference(self):
        self.prepare()
        self.backend.revision = "new-revision"
        result = self.evaluator.evaluate("toy", self.code)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["scores"]["heartbeat_reduction_pct"])
        self.assertEqual(sum(ref for _, ref, _ in self.backend.calls), 2)
        self.assertTrue(
            all(r["reference"] is None for r in result["per_version"].values())
        )

    def test_changed_dataset_reference_does_not_reuse_baseline(self):
        self.prepare()
        altered = copy.deepcopy(self.row)
        altered["src"] = "theorem toy : True := by constructor"
        self.dataset_path.write_text(json.dumps(altered) + "\n")
        result = self.make_evaluator().evaluate("toy", self.code)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["scores"]["heartbeat_reduction_pct"])
        self.assertEqual(sum(ref for _, ref, _ in self.backend.calls), 2)

    def test_partial_checks_have_no_compatibility_or_combined_reward(self):
        self.prepare()
        result = self.evaluator.evaluate("toy", self.code, versions="primary")
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["scores"]["compatibility_pct"])
        self.assertIsNone(result["scores"]["combined_pct"])
        self.assertEqual(
            self.evaluator.reward(
                "toy", self.code, versions="primary", metric="heartbeat"
            ),
            0.75,
        )
        with self.assertRaises(EvaluationNotReady):
            self.evaluator.reward("toy", self.code, versions="primary")

    def test_subset_without_primary_cannot_receive_length_reward(self):
        self.prepare()
        result = self.evaluator.evaluate("toy", self.code, versions=["v2"])
        self.assertIsNone(result["scores"]["length_reduction_pct"])
        with self.assertRaises(EvaluationNotReady):
            self.evaluator.reward("toy", self.code, versions=["v2"], metric="length")

    def test_all_versions_in_reverse_order_still_produce_full_score(self):
        self.prepare()
        result = self.evaluator.evaluate("toy", self.code, versions=["v2", "v1"])
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["scores"]["compatibility_pct"], 100)
        self.assertEqual(result["primary_version"], "v1")

    def test_missing_environment_is_not_a_bad_candidate_reward(self):
        evaluator = self.make_evaluator(environments_path=None)
        result = evaluator.evaluate("toy", self.code)
        self.assertEqual(result["status"], "incomplete")
        self.assertTrue(
            all(v["status"] == "unavailable" for v in result["per_version"].values())
        )
        self.assertFalse(self.backend.calls)
        with self.assertRaises(EvaluationNotReady):
            evaluator.reward("toy", self.code)

    def test_secondary_infrastructure_failure_is_not_compatibility_failure(self):
        self.prepare()
        self.backend.statuses["v2"] = "unavailable"
        result = self.evaluator.evaluate("toy", self.code)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["scores"]["compatibility_pct"])
        with self.assertRaises(EvaluationNotReady):
            self.evaluator.reward("toy", self.code)

    def test_primary_compilation_failure_zeroes_every_axis(self):
        self.prepare()
        self.backend.statuses["v1"] = "failed"
        result = self.evaluator.evaluate("toy", self.code)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(all(value == 0 for value in result["scores"].values()))
        self.assertEqual(self.evaluator.reward("toy", self.code), 0)

    def test_secondary_failure_reduces_compatibility_only(self):
        self.prepare()
        self.backend.statuses["v2"] = "failed"
        result = self.evaluator.evaluate("toy", self.code)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["scores"]["compatibility_pct"], 50)
        self.assertAlmostEqual(result["scores"]["combined_pct"], (80 + 75 + 50) / 3)

    def test_timeout_is_candidate_failure_but_is_not_cached(self):
        self.prepare()
        self.backend.statuses["v1"] = "timeout"
        self.assertEqual(self.evaluator.reward("toy", self.code), 0)
        self.backend.statuses["v1"] = "passed"
        result = self.evaluator.evaluate("toy", self.code)
        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["per_version"]["v1"]["cached"])

    def test_forbidden_or_changed_statement_zero_without_compilation(self):
        for code in (
            "theorem toy : False := by trivial",
            "theorem toy : True := by sorry",
        ):
            with self.subTest(code=code):
                result = self.evaluator.evaluate("toy", code)
                self.assertEqual(result["status"], "invalid")
                self.assertTrue(all(value == 0 for value in result["scores"].values()))
                self.assertEqual(self.evaluator.reward("toy", code), 0)
        self.assertFalse(self.backend.calls)

    def test_body_input_attaches_exact_statement(self):
        self.prepare()
        self.evaluator.evaluate("toy", "by trivial", input_kind="body")
        self.assertEqual(self.backend.calls[-1][2], self.code)

    def test_negative_heartbeat_reductions_are_not_clipped(self):
        self.prepare()
        self.backend.candidate_cost["v1"] = 5000
        result = self.evaluator.evaluate("toy", self.code)
        self.assertEqual(result["scores"]["heartbeat_reduction_pct"], -400)
        self.assertLess(result["scores"]["combined_pct"], 0)
        self.assertEqual(
            self.evaluator.reward("toy", self.code, metric="heartbeat"), -4
        )

    def test_zero_baseline_never_yields_nan_or_fabricated_reward(self):
        self.backend.reference_cost["v1"] = 0
        self.prepare()
        result = self.evaluator.evaluate("toy", self.code)
        self.assertIsNone(result["scores"]["heartbeat_reduction_pct"])
        json.dumps(result, allow_nan=False)
        with self.assertRaises(EvaluationNotReady):
            self.evaluator.reward("toy", self.code)

    def test_environment_change_during_compile_does_not_populate_cache(self):
        self.backend.change_during_check = True
        prepared = self.evaluator.prepare_reference("toy")
        self.assertEqual(prepared["status"], "incomplete")
        self.assertFalse(list((self.root / "cache" / "references").glob("*.json")))
        result = self.evaluator.evaluate("toy", self.code)
        self.assertTrue(
            all(r["status"] == "unavailable" for r in result["per_version"].values())
        )
        self.assertFalse(list((self.root / "cache" / "candidates").glob("*.json")))

    def test_parallel_reference_requests_measure_once_per_version(self):
        self.backend.delay = 0.01
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(
                pool.map(lambda _: self.evaluator.prepare_reference("toy"), range(4))
            )
        self.assertTrue(all(result["status"] == "prepared" for result in results))
        self.assertEqual(len(self.backend.calls), 2)

    def test_parallel_candidates_compile_once_per_version(self):
        self.prepare()
        self.evaluator = self.make_evaluator(version_workers=2)
        self.backend.delay = 0.01
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(
                pool.map(lambda _: self.evaluator.evaluate("toy", self.code), range(4))
            )
        self.assertTrue(all(result["status"] == "passed" for result in results))
        self.assertEqual(len(self.backend.calls), 4)

    def test_concurrent_versions_keep_order_scores_and_all_version_results(self):
        self.prepare()
        serial = self.evaluator.evaluate("toy", self.code)
        # A second spelling gives fresh candidate keys against the same references.
        candidate = "theorem toy : True := by\n  trivial"
        parallel = self.make_evaluator(version_workers=2)
        rendezvous = threading.Barrier(2, timeout=5)
        check = self.backend.check

        def simultaneous(row, code, version, project):
            rendezvous.wait()
            return check(row, code, version, project)

        with patch.object(self.backend, "check", side_effect=simultaneous):
            result = parallel.evaluate("toy", candidate)
        self.assertEqual(list(result["per_version"]), ["v1", "v2"])
        self.assertEqual(result["scores"], serial["scores"])
        self.assertTrue(all(not r["cached"] for r in result["per_version"].values()))
        self.backend.statuses["v1"] = "timeout"
        with patch.object(self.backend, "check", side_effect=simultaneous):
            rejected = parallel.evaluate("toy", candidate + "\n-- new candidate")
        self.assertEqual(rejected["status"], "failed")
        self.assertEqual(rejected["scores"]["combined_pct"], 0)
        self.assertEqual(rejected["per_version"]["v1"]["status"], "timeout")
        self.assertTrue(rejected["per_version"]["v2"]["passed"])

    def test_concurrent_versions_reject_environment_changes_without_caching(self):
        self.prepare()
        parallel = self.make_evaluator(version_workers=2)
        rendezvous = threading.Barrier(2, timeout=5)
        check = self.backend.check

        def changed(row, code, version, project):
            result = check(row, code, version, project)
            rendezvous.wait()
            self.backend.revision = "changed"
            return result

        with patch.object(self.backend, "check", side_effect=changed):
            result = parallel.evaluate("toy", self.code)
        self.assertTrue(
            all(r["status"] == "unavailable" for r in result["per_version"].values())
        )
        self.assertFalse(list((self.root / "cache" / "candidates").glob("*.json")))

    def test_version_worker_bounds_and_custom_backend_default(self):
        self.assertEqual(self.make_evaluator().version_workers, 1)
        self.assertEqual(self.make_evaluator(backend=None).version_workers, 4)
        for invalid in (True, False, 0, -1, 5, 2.0, "2"):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                self.make_evaluator(version_workers=invalid)

    def test_batch_checks_lengths_and_propagates_missing_measurements(self):
        with self.assertRaises(ValueError):
            self.evaluator.reward_batch(["toy"], [])
        with self.assertRaises(EvaluationNotReady):
            self.evaluator.reward_batch(["toy"], [self.code])
        self.prepare()
        self.assertEqual(
            self.evaluator.reward_batch(["toy", "toy"], [self.code, self.code]),
            [0.85, 0.85],
        )

    def test_invalid_version_selection_is_a_caller_error(self):
        for versions in ([], ["v1", "v1"], ["unknown"]):
            with self.subTest(versions=versions), self.assertRaises(ValueError):
                self.evaluator.evaluate("toy", self.code, versions=versions)


if __name__ == "__main__":
    unittest.main()
