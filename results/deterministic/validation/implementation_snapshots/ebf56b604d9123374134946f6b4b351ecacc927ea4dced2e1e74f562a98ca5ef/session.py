"""Host-owned score feedback and best-proof ledger; references are never measured."""

from __future__ import annotations

import json
import threading
import time
from copy import deepcopy
from pathlib import Path

from proof_eval.evidence.io import fingerprint, now, read, write_json, write_jsonl
from proof_eval.protocol import FIELDS, code_identity, context_for_prompt
from proof_eval.verification.context import build_context
from proof_eval.verification.feedback import (
    all_versions_passed,
    build_validity_feedback,
)
from proof_eval.verification.profile_trace import profile_view
from proof_eval.verification.profiling import ProfileConfig, profile
from proof_eval.verification.references import (
    original_evaluation,
    require_valid,
    required_versions,
)

from .source import SourceTools


class ProofSession:
    def __init__(
        self,
        folder,
        pack,
        evaluator,
        mode,
        guard=lambda: None,
        *,
        seed=None,
        cleanup=None,
        deadline_at=None,
        problem_timeout_seconds=None,
    ):
        if mode not in ("correctness", "score", "score_edges"):
            raise ValueError("Unknown feedback mode")
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.pack, self.evaluator, self.mode, self.guard = pack, evaluator, mode, guard
        self.deadline_at = deadline_at
        self.problem_timeout_seconds = problem_timeout_seconds
        self.row = pack["row"]
        self.versions = required_versions(pack)
        self.source_tools = SourceTools(evaluator, self.row, self.versions)
        self.original = original_evaluation(pack)
        self.seed_code, self.seed_evaluation = seed or (self.row["src"], self.original)
        if seed is not None:
            require_valid(self.seed_evaluation, self.row, self.seed_code)
            if (
                self.seed_evaluation["scores"]["combined_pct"]
                < self.original["scores"]["combined_pct"]
            ):
                raise ValueError("Seed may not regress the original")
        self.best_code = self.seed_code
        self.best_evaluation = deepcopy(self.seed_evaluation)
        self.cleanup = cleanup
        cleanup_log = self.folder / "deterministic.jsonl"
        self.cleanup_calls = (
            [json.loads(s) for s in cleanup_log.read_text().splitlines()]
            if cleanup_log.exists()
            else []
        )
        self.first_valid_code = None
        self.checks = []
        self.cache = {}
        if seed is not None:
            self.cache[code_identity(self.row, self.seed_code)] = self.seed_evaluation
        self.finished = None
        self.lock = threading.RLock()
        ledger = self.folder / "checks.jsonl"
        if ledger.exists():
            for line in ledger.read_text().splitlines():
                record = json.loads(line)
                self._restore(record)
        if (self.folder / "finished.json").exists():
            self.finished = json.loads((self.folder / "finished.json").read_text())
        self._save_state()

    def _restore(self, record):
        self.checks.append(record)
        self.cache[record["code_sha256"]] = record["evaluation"]
        if record["all_versions_passed"] and self.first_valid_code is None:
            self.first_valid_code = record["code"]
        if record["accepted"]:
            self.best_code, self.best_evaluation = record["code"], record["evaluation"]

    def _save_state(self):
        write_json(
            self.folder / "state.json",
            {
                "name": self.pack["name"],
                "mode": self.mode,
                "updated_at": now(),
                "checks": len(self.checks),
                "valid_checks": sum(r["all_versions_passed"] for r in self.checks),
                "improvements": sum(r["accepted"] for r in self.checks),
                "best_proof": self.best_code,
                "best_evaluation": self.best_evaluation,
                "finished": self.finished,
                "deterministic_calls": len(self.cleanup_calls),
            },
        )

    def _score_view(self, evaluation):
        scores = evaluation["scores"]
        checks = evaluation.get("per_version", {})
        passing = sum(checks.get(v, {}).get("passed") is True for v in self.versions)
        return {
            "score_tuple_order": list(FIELDS[:3]),
            "score_tuple": [scores.get(k) for k in FIELDS[:3]],
            "total_score": scores.get("combined_pct"),
            "scores": scores,
            "passing_rate_pct": 100 * passing / len(self.versions),
            "source_tokens": evaluation.get("candidate", {}).get("length"),
            "primary_heartbeats": checks.get(self.versions[0], {}).get("heartbeats"),
            "note": "Local fixed-reference score. A primary failure gates competition components/total to zero; actual passing_rate_pct is reported separately.",
        }

    def check(self, code: str, *, origin: str = "agent_tool") -> dict:
        with self.lock:
            identity = code_identity(self.row, code)
            if self.finished and origin == "agent_tool":
                raise ValueError("Session already finished")
            if self.mode == "correctness" and self.first_valid_code is not None:
                if identity != code_identity(self.row, self.first_valid_code):
                    return {
                        "kind": "proposal_already_valid",
                        "stop": True,
                        "message": "The first valid proposal has been saved. Return that declaration; further optimization belongs to the score experiment.",
                    }
            self.guard()
            started = time.monotonic()
            duplicate = identity in self.cache
            if identity == code_identity(self.row, self.row["src"]):
                evaluation = deepcopy(self.original)
            elif duplicate:
                evaluation = deepcopy(self.cache[identity])
            else:
                evaluation = self.evaluator.evaluate(
                    self.pack["name"], code, versions="all"
                )
            self.guard()
            valid = all_versions_passed(evaluation, self.versions)
            numeric = evaluation.get("scores", {}).get("combined_pct")
            accepted = (
                valid
                and numeric is not None
                and numeric > self.best_evaluation["scores"]["combined_pct"] + 0.05
            )
            feedback = build_validity_feedback(evaluation, self.versions)
            previous = self.best_evaluation["scores"]["combined_pct"]
            record = {
                "number": len(self.checks) + 1,
                "at": now(),
                "origin": origin,
                "code": code,
                "code_sha256": identity,
                "evaluation": evaluation,
                "feedback": feedback,
                "duplicate": duplicate,
                "all_versions_passed": valid,
                "accepted": accepted,
                "previous_best_score": previous,
                "elapsed_seconds": time.monotonic() - started,
            }
            write_jsonl(self.folder / "checks.jsonl", self.checks + [record])
            self._restore(record)
            self._save_state()
            if self.mode == "correctness":
                return feedback
            return {
                "kind": "lean_score_feedback",
                **self._score_view(evaluation),
                "correctness": feedback,
                "all_versions_passed": valid,
                "accepted_as_best": accepted,
                "duplicate": duplicate,
                "delta_from_previous_best_pp": (
                    None if numeric is None else numeric - previous
                ),
                "best_scores": self.best_evaluation["scores"],
                "best_proof": self.best_code,
            }

    def status(self) -> dict:
        if self.mode == "correctness":
            return {
                "kind": "lean_correctness_status",
                "proposal_valid": self.first_valid_code is not None,
                "message": "Stop after the first valid proposal; no candidate scores are exposed.",
            }
        response = {
            "kind": "lean_optimization_status",
            "attempts": len(self.checks),
            **self._score_view(self.best_evaluation),
            "best_proof": self.best_code,
            "finished": self.finished,
        }
        if self.deadline_at is not None:
            response.update(
                time_remaining_seconds=max(0.0, self.deadline_at - time.time()),
                problem_timeout_seconds=self.problem_timeout_seconds,
            )
        return response

    def profile(self, code: str, *, config: ProfileConfig | None = None) -> dict:
        """Record a diagnostic without modifying checks, scores or best proof."""
        with self.lock:
            if self.mode == "correctness":
                raise ValueError("Profiling is unavailable in correctness-only mode")
            if self.finished:
                raise ValueError("Session already finished")
            self.guard()
            result = profile(self.evaluator, self.pack["name"], code, config=config)
            self.guard()
            evidence = {"at": now(), "code": code, "profile": result}
            identity = fingerprint(evidence)
            write_json(self.folder / "profiles" / f"{identity}.json", evidence)
            return {**profile_view(result), "evidence_id": identity}

    def deterministic(self, code: str, *, origin: str = "agent_tool") -> dict:
        """Host-only final cleanup, preserving raw and cleaned evidence."""
        with self.lock:
            if origin != "final_harness" or self.mode != "score_edges":
                raise ValueError(
                    "Deterministic cleanup is available only to the host after search"
                )
            if self.cleanup is None:
                raise ValueError("No deterministic portfolio configured")
            self.guard()
            self.check(code, origin="deterministic_input")
            before = self.checks[-1]
            valid = before["all_versions_passed"]
            pending = self.folder / "cleanup_started.json"
            write_json(
                pending,
                {
                    "input_check": before["number"],
                    "input_code_sha256": before["code_sha256"],
                    "before": {
                        "proof": self.best_code,
                        "evaluation": self.best_evaluation,
                    },
                },
            )
            job = self.cleanup(code) if valid else None
            if job is not None:
                write_json(pending, {**read(pending), "job": job})
            after = None
            if job is not None:
                require_valid(job["evaluation"], self.row, job["proof"])
                identity = code_identity(self.row, job["proof"])
                self.cache[identity] = job["evaluation"]
                after = self.check(job["proof"], origin="deterministic_" + origin)
            record = {
                "number": len(self.cleanup_calls) + 1,
                "at": now(),
                "origin": origin,
                "input_code_sha256": before["code_sha256"],
                "input_check": before["number"],
                "output_check": self.checks[-1]["number"] if job else None,
                "status": job["status"] if job else "skipped_invalid",
                "job_path": job.get("job_path") if job else None,
                "job_result_sha256": job.get("job_result_sha256") if job else None,
                "counters": job.get("counters", {}) if job else {},
                "reused": job.get("reused", False) if job else False,
            }
            write_jsonl(
                self.folder / "deterministic.jsonl", self.cleanup_calls + [record]
            )
            self.cleanup_calls.append(record)
            pending.unlink(missing_ok=True)
            self.guard()
            self._save_state()
            return {
                "kind": "deterministic_feedback",
                "status": record["status"],
                "before": self._score_view(before["evaluation"]),
                "after": self._score_view(job["evaluation"]) if job else None,
                "cleaned_proof": job["proof"] if job else None,
                "gain_over_input_pp": (
                    None
                    if job is None
                    else job["evaluation"]["scores"]["combined_pct"]
                    - before["evaluation"]["scores"]["combined_pct"]
                ),
                "accepted_as_best": after["accepted_as_best"] if after else False,
                "correctness": before["feedback"],
                "reused": record["reused"],
                "best_proof": self.best_code,
                "best_scores": self.best_evaluation["scores"],
            }

    def dispatch(self, request: dict) -> dict:
        op = request.get("op")
        if (
            op == "check"
            and set(request) == {"op", "code"}
            and isinstance(request["code"], str)
        ):
            return self.check(request["code"])
        if op == "status" and set(request) == {"op"}:
            return self.status()
        if (
            op == "profile"
            and {"op", "code"} <= set(request)
            and set(request) <= {"op", "code", "version", "threshold_raw", "limit"}
            and isinstance(request["code"], str)
        ):
            return self.profile(
                request["code"],
                config=ProfileConfig(
                    **{
                        key: value
                        for key, value in request.items()
                        if key not in {"op", "code"}
                    }
                ),
            )
        if op == "finish" and set(request) == {"op", "reason"}:
            if not isinstance(request["reason"], str) or not request["reason"].strip():
                raise ValueError("Provide a short factual stopping reason")
            with self.lock:
                self.finished = {
                    "at": now(),
                    "reason": request["reason"][:2000],
                    "kind": "agent_decision",
                }
                write_json(self.folder / "finished.json", self.finished)
                self._save_state()
                return self.status()
        if (
            op == "goals"
            and set(request) == {"op", "code"}
            and isinstance(request["code"], str)
        ):
            self.guard()
            observed = build_context(
                self.evaluator, self.row, request["code"], measure_costs=False
            )
            self.guard()
            return {
                "kind": "lean_goal_observations",
                **context_for_prompt(observed, costs=False),
            }
        if op in ("search", "read", "outline"):
            return self.source(request)
        raise ValueError("Unknown operation or invalid fields")

    def source(self, request):
        return self.source_tools.source(request)
