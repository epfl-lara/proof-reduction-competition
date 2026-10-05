"""Saved-evidence audit catches tampering without invoking any Lean process."""

import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from proof_eval.evidence.audit import audit
from proof_eval.verification.metrics import token_count, validate_candidate


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def lines(path, values):
    path.write_text("".join(json.dumps(value) + "\n" for value in values))


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.backend_source = "original backend source\n"
        self.backend_hash = sha(self.backend_source)
        self.stage = self.root / "stage"
        self.stage.mkdir()
        self.dataset = self.root / "dataset.jsonl"
        self.references = self.root / "references.jsonl"
        self.row = {
            "name": "example",
            "source": "fixture",
            "statement": "theorem example : True",
            "version_info": [{"v1": "commit1"}, {"v2": "commit2"}],
        }
        self.row["src"] = (
            self.row["statement"] + " := by\n  have h : True := by trivial\n  exact h"
        )
        self.row["proof_length"] = token_count(
            validate_candidate(self.row, self.row["src"])[1]
        )
        lines(self.dataset, [self.row])
        self.dataset_hash = sha(self.dataset.read_text())
        self.reference = {
            "name": "example",
            "status": "prepared",
            "dataset_sha256": self.dataset_hash,
            "reference_length_tokens": self.row["proof_length"],
            "reference_code_sha256": sha(self.row["src"]),
            "per_version": {},
        }
        for version, heartbeats in [("v1", 100), ("v2", 200)]:
            provenance = {
                "environment_fingerprint": "env-" + version,
                "reference_code_sha256": sha(self.row["src"]),
                "measured_at": "fixed",
                "machine": {"host": "fixture"},
                "details": {"backend_implementation_sha256": self.backend_hash},
            }
            self.reference["per_version"][version] = {
                "status": "prepared",
                "heartbeats": heartbeats,
                "heartbeats_raw": heartbeats * 1000,
                "provenance": provenance,
            }
            write(
                self.root / "cache" / "references" / ("context-" + version + ".json"),
                {
                    "name": "example",
                    "version": version,
                    "status": "prepared",
                    "heartbeats": heartbeats,
                    "heartbeats_raw": heartbeats * 1000,
                    **provenance,
                },
            )
        lines(self.references, [self.reference])
        self.proof = " \n" + self.row["statement"] + " :=\n  by trivial\n"
        self.record = {
            "name": "example",
            "source": "fixture",
            "proof": self.proof,
            "initial": self.evaluation(self.row["src"], 100, 200),
            "final": self.evaluation(self.proof, 50, 60),
            "accepted_edits": 1,
            "accepted_transitions": 1,
            "changed": True,
            "stop_reason": "no_new_proposals",
        }
        self.problem = self.stage / ("problem_" + sha("example")[:16] + ".json")
        write(self.problem, self.record)
        lines(
            self.stage / "candidates.jsonl", [{"name": "example", "proof": self.proof}]
        )
        self.config = {
            "dataset_sha256": self.dataset_hash,
            "names": ["example"],
            "input_sha256": None,
            "code_sha256": {"src/proof_eval/lean_backend.py": self.backend_hash},
            "contexts": {"example": {"v1": "context-v1", "v2": "context-v2"}},
            "budget": {"min_gain": 0.05},
        }
        write(self.stage / "config.json", self.config)
        self.events = [
            {
                "name": "example",
                "kind": "candidate",
                "round": 0,
                "trial": 1,
                "parent_sha256": sha(self.row["src"]),
                "proof": self.proof,
                "edits": [
                    {
                        "start": 0,
                        "end": len(self.row["src"]),
                        "replacement": self.proof,
                        "reason": "fixture",
                    }
                ],
                "evaluation": self.record["final"],
                "all_versions_requested": True,
                "improves_incumbent": True,
            }
        ]
        self.events.append(
            {
                "name": "example",
                "kind": "accepted",
                "round": 0,
                "trial": 1,
                "score": self.record["final"]["scores"]["combined_pct"],
                "edits": self.events[0]["edits"],
            }
        )
        self.log = self.stage / ("trials_" + sha("example")[:16] + ".jsonl")
        lines(self.log, self.events)
        write(
            self.stage / "summary.json",
            {
                "full_benchmark_combined_pct": self.record["final"]["scores"][
                    "combined_pct"
                ],
                "full_benchmark_delta_pp": self.record["final"]["scores"][
                    "combined_pct"
                ]
                - 100 / 3,
            },
        )

    def evaluation(self, code, hb1, hb2):
        normalized, body = validate_candidate(self.row, code)
        length = token_count(body)
        scores = {
            "length_reduction_pct": 100 * (1 - length / self.row["proof_length"]),
            "heartbeat_reduction_pct": 100 * (1 - hb1 / 100),
            "compatibility_pct": 100,
        }
        scores["combined_pct"] = sum(scores.values()) / 3
        return {
            "status": "passed",
            "primary_version": "v1",
            "candidate": {"length": length, "code_sha256": sha(normalized)},
            "scores": scores,
            "per_version": {
                v: {
                    "status": "passed",
                    "passed": True,
                    "heartbeats": hb,
                    "heartbeat_reduction_pct": 100 * (1 - hb / ref),
                    "environment_fingerprint": "env-" + v,
                }
                for v, hb, ref in [("v1", hb1, 100), ("v2", hb2, 200)]
            },
        }

    def check(self, **kwargs):
        return audit(
            [self.stage], dataset=self.dataset, references=self.references, **kwargs
        )

    def test_normalized_hash_and_reference_cache_audit_never_spawn_process(self):
        self.assertNotEqual(
            sha(self.proof), self.record["final"]["candidate"]["code_sha256"]
        )
        with (
            patch(
                "subprocess.run", side_effect=AssertionError("No subprocess allowed")
            ),
            patch(
                "subprocess.Popen", side_effect=AssertionError("No subprocess allowed")
            ),
        ):
            report = self.check(check_cache=True, cache=self.root / "cache")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["cached_reference_records_checked"], 2)
        self.assertEqual(report["stages"][0]["accepted_transitions_checked"], 1)

    def test_selected_proof_and_record_must_agree(self):
        lines(
            self.stage / "candidates.jsonl",
            [{"name": "example", "proof": self.row["src"]}],
        )
        with self.assertRaisesRegex(ValueError, "selected proof differs"):
            self.check()

    def test_tampered_heartbeat_arithmetic_is_rejected(self):
        self.record["final"]["per_version"]["v1"]["heartbeats"] += 1
        write(self.problem, self.record)
        with self.assertRaisesRegex(ValueError, "heartbeat reduction"):
            self.check()

    def test_missing_version_and_wrong_environment_are_rejected(self):
        for corruption in ("missing", "fingerprint"):
            with self.subTest(corruption=corruption):
                record = deepcopy(self.record)
                if corruption == "missing":
                    del record["final"]["per_version"]["v2"]
                else:
                    record["final"]["per_version"]["v2"][
                        "environment_fingerprint"
                    ] = "wrong"
                write(self.problem, record)
                with self.assertRaisesRegex(
                    ValueError, "version keys differ|fingerprint mismatch"
                ):
                    self.check()

    def test_margin_and_accepted_parent_are_audited(self):
        self.config["budget"]["min_gain"] = 100
        write(self.stage / "config.json", self.config)
        with self.assertRaisesRegex(ValueError, "configured margin"):
            self.check()
        self.config["budget"]["min_gain"] = 0.05
        write(self.stage / "config.json", self.config)
        self.events[0]["parent_sha256"] = "wrong"
        lines(self.log, self.events)
        with self.assertRaisesRegex(ValueError, "wrong parent"):
            self.check()

    def test_duplicate_selection_and_changed_reference_cache_are_rejected(self):
        rows = [{"name": "example", "proof": self.proof}]
        lines(self.stage / "candidates.jsonl", rows * 2)
        with self.assertRaisesRegex(ValueError, "exactly 1 rows"):
            self.check()
        lines(self.stage / "candidates.jsonl", rows)
        path = self.root / "cache" / "references" / "context-v1.json"
        value = json.loads(path.read_text())
        value["measured_at"] = "remeasured"
        write(path, value)
        with self.assertRaisesRegex(ValueError, "measured_at changed"):
            self.check(check_cache=True, cache=self.root / "cache")

    def test_recorded_input_hash_must_resolve(self):
        self.config["input_sha256"] = "missing"
        write(self.stage / "config.json", self.config)
        with self.assertRaisesRegex(ValueError, "input artifact"):
            self.check()

    def test_successive_stage_chain_and_code_snapshot_are_checked(self):
        second = self.root / "second"
        second.mkdir()
        config = deepcopy(self.config)
        config["input_path"] = str(self.stage / "candidates.jsonl")
        config["input_sha256"] = sha((self.stage / "candidates.jsonl").read_text())
        write(second / "config.json", config)
        record = deepcopy(self.record)
        record.update(
            initial=deepcopy(record["final"]),
            accepted_edits=0,
            accepted_transitions=0,
            changed=False,
        )
        write(second / self.problem.name, record)
        lines(second / "candidates.jsonl", [{"name": "example", "proof": self.proof}])
        lines(second / self.log.name, [])
        write(
            second / "summary.json",
            {
                "full_benchmark_combined_pct": record["final"]["scores"][
                    "combined_pct"
                ],
                "full_benchmark_delta_pp": 0,
            },
        )
        report = audit(
            [self.stage, second], dataset=self.dataset, references=self.references
        )
        self.assertEqual(len(report["stages"]), 2)
        config["input_sha256"] = None
        write(second / "config.json", config)
        with self.assertRaisesRegex(ValueError, "chain unexpectedly restarts"):
            audit(
                [self.stage, second], dataset=self.dataset, references=self.references
            )
        source = self.root / "code" / "src" / "proof_eval" / "lean_backend.py"
        source.parent.mkdir(parents=True)
        source.write_text("changed implementation")
        with self.assertRaisesRegex(ValueError, "implementation hash changed"):
            self.check(check_code=True, code_root=self.root / "code")

    def test_exact_archived_source_is_accepted_when_current_source_changed(self):
        source = self.root / "code" / "src" / "proof_eval" / "lean_backend.py"
        source.parent.mkdir(parents=True)
        source.write_text("updated source")
        snapshots = self.root / "snapshots"
        archived = snapshots / self.backend_hash / "lean_backend.py"
        archived.parent.mkdir(parents=True)
        archived.write_text(self.backend_source)
        with (
            patch(
                "subprocess.run", side_effect=AssertionError("No subprocess allowed")
            ),
            patch(
                "subprocess.Popen", side_effect=AssertionError("No subprocess allowed")
            ),
        ):
            report = self.check(
                check_code=True, code_root=self.root / "code", snapshots=snapshots
            )
        checks = report["stages"][0]["implementation_checks"]
        self.assertEqual(checks[0]["verification"], "snapshot")
        self.assertEqual(checks[0]["sha256"], self.backend_hash)
        self.assertEqual(checks[0]["path"], str(archived))

    def test_snapshot_directory_name_does_not_certify_wrong_or_missing_bytes(self):
        snapshots = self.root / "snapshots"
        archived = snapshots / self.backend_hash / "lean_backend.py"
        archived.parent.mkdir(parents=True)
        archived.write_text("wrong source in correctly named directory")
        for exists in (True, False):
            with self.subTest(snapshot_exists=exists):
                if not exists:
                    archived.unlink()
                with self.assertRaisesRegex(ValueError, "no matching snapshot"):
                    self.check(
                        check_code=True,
                        code_root=self.root / "missing-current",
                        snapshots=snapshots,
                    )

    def test_current_source_reports_current_verification(self):
        source = self.root / "code" / "src" / "proof_eval" / "lean_backend.py"
        source.parent.mkdir(parents=True)
        source.write_text(self.backend_source)
        report = self.check(
            check_code=True,
            code_root=self.root / "code",
            snapshots=self.root / "missing-snapshots",
        )
        self.assertEqual(
            report["stages"][0]["implementation_checks"][0]["verification"], "current"
        )


if __name__ == "__main__":
    unittest.main()
