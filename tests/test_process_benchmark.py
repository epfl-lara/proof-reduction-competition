"""Processing/export behavior with a deterministic evaluator double."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from proof_eval.dataset import Dataset
from process_benchmark import main, parse_versions, process_benchmark


class FakeEvaluator:
    def __init__(self, dataset_path):
        self.dataset = Dataset(dataset_path)
        self.cache = {}
        self.measurements = 0
        self.calls = []
        self.failures = {}
        self.interrupt_name = None

    def _selected(self, name, versions):
        listed = [v for item in self.dataset.get(name)["version_info"] for v in item]
        selected = listed if versions == "all" else listed[:1] if versions == "primary" else list(versions)
        if set(selected) - set(listed):
            raise ValueError("Requested version is not listed for problem")
        return selected

    def prepare_reference(self, name, *, versions, refresh=False):
        self.calls.append(("prepare", name, refresh))
        if name == self.interrupt_name:
            raise KeyboardInterrupt()
        results = {}
        for version in self._selected(name, versions):
            key = (name, version)
            if key in self.failures:
                results[version] = self.failures[key]
                continue
            cached = key in self.cache and not refresh
            if not cached:
                self.measurements += 1
                self.cache[key] = {
                    "status": "prepared", "heartbeats": 100 + self.measurements,
                    "heartbeats_raw": (100 + self.measurements) * 1000,
                    "environment_fingerprint": {"compiler": "test", "version": version},
                    "machine": {"host": "test-host"}, "measured_at": "2026-10-02T00:00:00+00:00",
                    "reference_code_sha256": hashlib.sha256(self.dataset.get(name)["src"].encode()).hexdigest(),
                    "details": {"measurement_scope": "test"},
                }
            results[version] = {**self.cache[key], "cached": cached}
        return {"name": name, "versions": results}

    def get_reference(self, name, *, versions):
        self.calls.append(("get", name))
        return {"name": name, "versions": {
            version: self.cache.get((name, version), {"status": "reference_not_prepared"})
            for version in self._selected(name, versions)
        }}


class ProcessBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.dataset_path = self.root / "benchmark.jsonl"
        rows = [{
            "name": name, "source": "toy", "statement": f"theorem {name} : True",
            "src": f"theorem {name} : True := by trivial", "proof_length": 345,
            "version_info": [{"v4.0.0": "a" * 40}, {"v4.1.0": "b" * 40}],
        } for name in ("first", "second")]
        self.dataset_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        self.evaluator = FakeEvaluator(self.dataset_path)
        self.output = self.root / "results" / "benchmark_values.jsonl"

    def read_rows(self):
        return [json.loads(line) for line in self.output.read_text(encoding="utf-8").splitlines()]

    def test_export_schema_uses_fixed_counts_and_local_provenance(self):
        summary = process_benchmark(self.evaluator, self.output)
        self.assertEqual(summary["problems"], 2)
        self.assertEqual(summary["prepared_versions"], 4)
        self.assertEqual(summary["unavailable_versions"], 0)
        rows = self.read_rows()
        self.assertEqual([row["name"] for row in rows], ["first", "second"])
        row = rows[0]
        self.assertEqual(row["schema_version"], 1)
        self.assertEqual(row["reference_length_tokens"], 345)
        self.assertIsNone(row["published_heartbeats"])
        self.assertEqual(row["dataset_sha256"], hashlib.sha256(self.dataset_path.read_bytes()).hexdigest())
        self.assertEqual(row["primary_version"], "v4.0.0")
        value = row["per_version"]["v4.0.0"]
        self.assertEqual(value["source_commit"], "a" * 40)
        self.assertEqual(value["heartbeats_raw"], value["heartbeats"] * 1000)
        self.assertFalse(value["cached"])
        self.assertEqual(value["provenance"]["machine"], {"host": "test-host"})
        self.assertNotIn("src", row)
        self.assertNotIn("statement", row)
        self.assertEqual(self.evaluator.calls, [
            ("prepare", "first", False), ("get", "first"),
            ("prepare", "second", False), ("get", "second"),
        ])

    def test_restart_uses_cache_and_only_refresh_remeasures(self):
        process_benchmark(self.evaluator, self.output)
        self.assertEqual(self.evaluator.measurements, 4)
        summary = process_benchmark(self.evaluator, self.output)
        self.assertEqual(self.evaluator.measurements, 4)
        self.assertEqual(summary["cached_versions"], 4)
        self.assertTrue(all(v["cached"] for row in self.read_rows() for v in row["per_version"].values()))
        summary = process_benchmark(self.evaluator, self.output, refresh=True)
        self.assertEqual(self.evaluator.measurements, 8)
        self.assertEqual(summary["cached_versions"], 0)

    def test_missing_environment_retains_problem_and_null_values(self):
        self.evaluator.failures[("first", "v4.1.0")] = {
            "status": "unavailable", "diagnostics": [{"severity": "error", "data": "No configured project"}],
        }
        summary = process_benchmark(self.evaluator, self.output)
        self.assertEqual(summary["problems"], 2)
        self.assertEqual(summary["prepared_versions"], 3)
        self.assertEqual(summary["unavailable_versions"], 1)
        failed = self.read_rows()[0]["per_version"]["v4.1.0"]
        self.assertEqual(failed["status"], "unavailable")
        self.assertIsNone(failed["heartbeats"])
        self.assertIsNone(failed["heartbeats_raw"])
        self.assertIn("No configured project", failed["diagnostics"][0]["data"])

    def test_failed_refresh_preserves_failure_even_when_old_cache_exists(self):
        process_benchmark(self.evaluator, self.output)
        self.evaluator.failures[("first", "v4.0.0")] = {
            "status": "timeout", "diagnostics": [{"severity": "error", "data": "exceeded 60 seconds"}],
        }
        process_benchmark(self.evaluator, self.output, refresh=True)
        failed = self.read_rows()[0]["per_version"]["v4.0.0"]
        self.assertEqual(failed["status"], "timeout")
        self.assertEqual(failed["cache_status"], "prepared")
        self.assertIsNone(failed["heartbeats"])
        self.assertIn("exceeded", failed["diagnostics"][0]["data"])

    def test_interruption_keeps_all_rows_and_completed_checkpoint(self):
        self.evaluator.interrupt_name = "second"
        with self.assertRaises(KeyboardInterrupt):
            process_benchmark(self.evaluator, self.output)
        rows = self.read_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["status"], "prepared")
        self.assertEqual(rows[1]["status"], "pending")
        self.assertIsNone(rows[1]["per_version"]["v4.0.0"]["heartbeats"])
        self.evaluator.interrupt_name = None
        summary = process_benchmark(self.evaluator, self.output)
        self.assertEqual(summary["cached_versions"], 2)
        self.assertEqual(self.evaluator.measurements, 4)

    def test_named_problem_and_primary_version_restriction(self):
        summary = process_benchmark(self.evaluator, self.output, names=["second"], versions="primary")
        self.assertEqual(summary["problems"], 1)
        self.assertEqual(summary["prepared_versions"], 1)
        self.assertEqual(self.read_rows()[0]["requested_versions"], ["v4.0.0"])

    def test_unknown_version_is_explicit_unavailable(self):
        summary = process_benchmark(self.evaluator, self.output, versions="v9.9.9")
        self.assertEqual(summary["unavailable_versions"], 2)
        value = self.read_rows()[0]["per_version"]["v9.9.9"]
        self.assertEqual(value["status"], "unavailable")
        self.assertIsNone(value["source_commit"])
        self.assertIn("not listed", value["diagnostics"][0]["data"])

    def test_output_cannot_overwrite_inputs(self):
        environment = self.root / "environments.local.json"
        heartbeat = self.root / "custom_heartbeats.jsonl"
        for path in (environment, heartbeat):
            path.write_text("preserve me", encoding="utf-8")
        original_dataset = self.dataset_path.read_bytes()
        for output in (self.dataset_path, environment, heartbeat, self.root / "benchmark_heartbeats.jsonl"):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "must not overwrite"):
                process_benchmark(self.evaluator, output, protected_paths=(environment, heartbeat))
        self.assertEqual(self.dataset_path.read_bytes(), original_dataset)
        self.assertEqual(environment.read_text(), "preserve me")
        self.assertEqual(heartbeat.read_text(), "preserve me")

    def test_invalid_names_do_not_clobber_existing_output(self):
        process_benchmark(self.evaluator, self.output)
        original = self.output.read_bytes()
        with self.assertRaises(KeyError):
            process_benchmark(self.evaluator, self.output, names=["unknown"])
        self.assertEqual(self.output.read_bytes(), original)

    def test_cli_summary_and_partial_exit_status(self):
        self.evaluator.failures[("first", "v4.0.0")] = {"status": "failed", "diagnostics": []}
        out = io.StringIO()
        with patch("process_benchmark.Evaluator", return_value=self.evaluator) as factory, redirect_stdout(out):
            status = main([
                "--dataset", str(self.dataset_path), "--output", str(self.output),
                "--environments", str(self.root / "env.json"), "--cache", str(self.root / "cache"),
                "--name", "first", "--versions", "primary", "--timeout", "15",
            ])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(out.getvalue())["unavailable_versions"], 1)
        self.assertEqual(factory.call_args.kwargs["timeout"], 15.0)
        self.assertEqual(len(out.getvalue().splitlines()), 1)

    def test_cli_success_and_errors(self):
        out = io.StringIO()
        with patch("process_benchmark.Evaluator", return_value=self.evaluator), redirect_stdout(out):
            self.assertEqual(main(["--output", str(self.output)]), 0)
        err = io.StringIO()
        with patch("process_benchmark.Evaluator", return_value=self.evaluator), redirect_stderr(err):
            self.assertEqual(main(["--versions", "v4.0.0,,v4.1.0"]), 2)
        self.assertIn("unique", json.loads(err.getvalue())["error"])

    def test_version_argument_parser(self):
        self.assertEqual(parse_versions("all"), "all")
        self.assertEqual(parse_versions("primary"), "primary")
        self.assertEqual(parse_versions("v4.0.0, v4.1.0"), ["v4.0.0", "v4.1.0"])
        for text in ("", "v4.0.0,v4.0.0", "v4.0.0,"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_versions(text)


if __name__ == "__main__":
    unittest.main()
