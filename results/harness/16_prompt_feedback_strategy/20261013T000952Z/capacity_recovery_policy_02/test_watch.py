import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import watch


class MonitorContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(watch, "ROOT", self.root)
        self.config_patch = patch.object(watch, "CONFIG", self.root / "monitor.json")
        self.root_patch.start()
        self.config_patch.start()
        self.config = {"run": str(self.root / "experiment"), "phase": "comparison", "cohort_size": 15,
                       "timer": "fixture.timer", "thread_id": "fixture", "codex": "unused",
                       "targets": [{"name": arm, "output": str(self.root / "experiment" / arm)}
                                   for arm in ("revised", "baseline")]}
        watch.save(watch.CONFIG, self.config)

    def tearDown(self):
        self.root_patch.stop()
        self.config_patch.stop()
        self.temp.cleanup()

    def delivered(self, folder, *args):
        watch.save(folder / "queued.json", {"returncode": 0})
        return True

    def test_pid_reuse_is_not_alive(self):
        self.assertTrue(watch.process(os.getpid())["alive"])
        self.assertFalse(watch.process(os.getpid(), expected_start=-1)["alive"])
        self.assertFalse(watch.process(os.getpid(), expected_path="impossible-identity-value")["alive"])

    def test_healthy_partial_cohort_and_failed_candidates_do_not_alert(self):
        arm = Path(self.config["targets"][0]["output"])
        watch.save(arm / "report.json", {"planned_cells": 15, "terminal_cells": 0,
                   "conditions": [{"complete": False}], "active": [{"checks": 20, "valid_checks": 3}]})
        with patch.object(watch, "process", return_value={"alive": True}):
            snapshot = watch.collect(self.config)
        self.assertEqual(snapshot["issues"], [])
        self.assertEqual(watch.events(snapshot), [])

    def test_complete_requires_both_cohorts_and_audits(self):
        run = Path(self.config["run"])
        watch.save(run / "launch_complete.json", {"status": "finished"})
        for target in self.config["targets"]:
            arm = Path(target["output"])
            watch.save(arm / "report.json", {"planned_cells": 15, "terminal_cells": 15,
                       "conditions": [{"complete": True, "mean_scores": {"combined_pct": 90}}]})
        with patch.object(watch, "process", return_value={"alive": False}):
            self.assertFalse(watch.collect(self.config)["ready"])
            for target in self.config["targets"]:
                watch.save(Path(target["output"]) / "audit.json", {"status": "passed"})
            snapshot = watch.collect(self.config)
        self.assertTrue(snapshot["ready"])
        self.assertEqual(watch.events(snapshot)[0]["kind"], "cohorts_complete_and_audited")

    def test_controlled_budget_outcome_is_not_a_failure(self):
        arm = Path(self.config["targets"][0]["output"])
        watch.save(arm / "cells/a/result.json", {"status": "complete", "termination": "cost_limit"})
        with patch.object(watch, "process", return_value={"alive": True}):
            self.assertEqual(watch.collect(self.config)["issues"], [])

    def test_report_refresh_does_not_mask_a_host_stall(self):
        run = Path(self.config["run"])
        watch.save(run / "launch.json", {"pid": 1})
        os.utime(run / "launch.json", (time.time() - 7200, time.time() - 7200))
        arm = Path(self.config["targets"][0]["output"])
        watch.save(arm / "report.json", {"planned_cells": 15, "terminal_cells": 0})
        with patch.object(watch, "process", return_value={"alive": True}):
            snapshot = watch.collect(self.config)
        self.assertIn("suspected_host_stall", [i["kind"] for i in snapshot["issues"]])

    def test_indeterminate_dead_request_is_flagged_never_reissued(self):
        attempt = Path(self.config["targets"][0]["output"]) / "cells/a/attempt_00"
        watch.save(attempt / "request_started.json", {"started_at": "fixture"})
        os.utime(attempt / "request_started.json", (time.time() - 400, time.time() - 400))
        with patch.object(watch, "process", return_value={"alive": False}):
            issues = watch.collect(self.config)["issues"]
        issue = next(i for i in issues if i["kind"] == "request_without_terminal_and_process")
        self.assertTrue(issue["resampling_forbidden"])

    def test_confirm_suspected_failure_and_deduplicate_without_stopping_timer(self):
        snapshot = {"phase": "comparison", "ready": False, "issues": [{"kind": "launcher_missing"}]}
        with patch.object(watch, "collect", return_value=snapshot), \
                patch.object(watch, "notify", side_effect=self.delivered) as notify, \
                patch.object(watch.subprocess, "run") as command:
            watch.run_once()
            notify.assert_not_called()
            watch.run_once()
            watch.run_once()
        self.assertEqual(notify.call_count, 1)
        command.assert_not_called()
        self.assertFalse((self.root / "STOP").exists())

    def test_new_phase_completion_alerts_and_monitor_keeps_running(self):
        snapshot = {"phase": "comparison", "ready": True, "issues": []}
        with patch.object(watch, "collect", return_value=snapshot), \
                patch.object(watch, "notify", side_effect=self.delivered) as notify:
            watch.run_once()
            watch.run_once()
            snapshot["phase"] = "step4"
            watch.run_once()
        self.assertEqual(notify.call_count, 2)
        self.assertFalse((self.root / "STOP").exists())

    def test_only_one_agy_call_per_tick(self):
        snapshot = {"phase": "comparison", "ready": False,
                    "issues": [{"kind": "incomplete_cell", "name": "a"},
                               {"kind": "incomplete_cell", "name": "b"}]}
        with patch.object(watch, "collect", return_value=snapshot), \
                patch.object(watch, "notify", side_effect=self.delivered) as notify:
            watch.run_once()
            self.assertEqual(notify.call_count, 1)
            watch.run_once()
        self.assertEqual(notify.call_count, 2)

    def test_agy_indeterminate_review_is_not_resampled(self):
        folder = self.root / "review"
        watch.save(folder / "started.json", {"at_epoch": 1})
        with patch.object(watch.subprocess, "Popen") as launch:
            result = watch.agy_review(folder, self.config, {}, {})
        self.assertEqual(result["status"], "indeterminate")
        launch.assert_not_called()

    def test_review_failure_falls_back_to_host_notification(self):
        folder = self.root / "alert"
        result = subprocess.CompletedProcess([], 0, "Queued message test", "")
        with patch.object(watch, "agy_review", side_effect=OSError("monitor unavailable")), \
                patch.object(watch.subprocess, "run", return_value=result):
            self.assertTrue(watch.notify(folder, self.config, {}, {"kind": "run_failed"}))
        self.assertTrue((folder / "review_error.json").exists())
        self.assertTrue((folder / "queued.json").exists())

    def test_unknown_queue_delivery_is_not_duplicated(self):
        folder = self.root / "alert"
        with patch.object(watch, "agy_review", return_value={"status": "SUCCESS"}), \
                patch.object(watch.subprocess, "run", side_effect=subprocess.TimeoutExpired("queue", 30)) as queue:
            self.assertFalse(watch.notify(folder, self.config, {}, {"kind": "test"}))
            self.assertFalse(watch.notify(folder, self.config, {}, {"kind": "test"}))
        self.assertEqual(queue.call_count, 1)

    def retry_fixture(self):
        return ({"retry_id": "retry02", "status": "waiting", "source_phase": "comparison",
                 "source_output": "baseline", "cohort_size": 15, "not_before_epoch": 1000},
                {"phase": "comparison", "ready": False, "completion": {"status": "finished_with_incomplete_outcomes"},
                 "launcher": {"alive": False}, "live_native_processes": [], "issues": [],
                 "arms": [{"output": "baseline", "terminal_cells": 15,
                           "audit_status": "passed", "pending_requests": []}]})

    def test_capacity_retry_waits_for_cooldown_and_inactive_audited_source(self):
        plan, snapshot = self.retry_fixture()
        self.assertFalse(watch.capacity_retry_due(snapshot, plan, 999))
        self.assertTrue(watch.capacity_retry_due(snapshot, plan, 1000))
        snapshot["launcher"]["alive"] = True
        self.assertFalse(watch.capacity_retry_due(snapshot, plan, 2000))
        snapshot["launcher"]["alive"] = False
        snapshot["arms"][0]["audit_status"] = None
        self.assertFalse(watch.capacity_retry_due(snapshot, plan, 2000))
        snapshot["arms"][0]["audit_status"] = "passed"
        snapshot["arms"][0]["pending_requests"] = [{"indeterminate": True}]
        self.assertFalse(watch.capacity_retry_due(snapshot, plan, 2000))

    def test_consumed_retry_wrong_phase_and_successful_source_do_not_wake(self):
        plan, snapshot = self.retry_fixture()
        plan["status"] = "admitted"
        self.assertFalse(watch.capacity_retry_due(snapshot, plan, 2000))
        plan["status"] = "waiting"
        plan["source_phase"] = "another_phase"
        self.assertFalse(watch.capacity_retry_due(snapshot, plan, 2000))
        plan["source_phase"] = "comparison"
        snapshot["ready"] = True
        self.assertFalse(watch.capacity_retry_due(snapshot, plan, 2000))

    def test_due_capacity_retry_notification_is_deduplicated(self):
        plan, snapshot = self.retry_fixture()
        snapshot.update(capacity_retry_plan=plan, capacity_retry_due=True)
        with patch.object(watch, "collect", return_value=snapshot), \
                patch.object(watch, "notify", side_effect=self.delivered) as notify:
            watch.run_once()
            watch.run_once()
        self.assertEqual(notify.call_count, 1)
        self.assertEqual(notify.call_args.args[-1]["kind"], "capacity_retry_due")


if __name__ == "__main__":
    unittest.main()
