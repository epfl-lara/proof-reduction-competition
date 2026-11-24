"""Host-owned score feedback and best-proof ledger; references are never measured."""

from __future__ import annotations

import json
import math
import threading
import time
from copy import deepcopy
from pathlib import Path

from proof_eval.defaults import DEFAULT_SELECTION_MARGIN_PP
from proof_eval.evidence.io import (
    digest,
    fingerprint,
    now,
    read,
    write_json,
    write_jsonl,
)
from proof_eval.protocol import FIELDS, code_identity, context_for_prompt
from proof_eval.verification.context import build_context
from proof_eval.verification.feedback import (
    all_versions_passed,
    build_validity_feedback,
)
from proof_eval.verification.metrics import validate_candidate
from proof_eval.verification.profile_trace import profile_view
from proof_eval.verification.profiling import ProfileConfig, profile
from proof_eval.verification.references import (
    original_evaluation,
    require_valid,
    required_versions,
)

from . import web
from .proof_history import best_check_id, query_history, read_queries
from .restart_history import RestartHistory
from .score_feedback import component_deltas, remaining_score_loss
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
        semantic_config=None,
        web_config=None,
        restart_scope=None,
        proof_history_scope=None,
        original_measurement=None,
        selection_margin_pp=DEFAULT_SELECTION_MARGIN_PP,
    ):
        if mode not in ("correctness", "score", "score_edges"):
            raise ValueError("Unknown feedback mode")
        if (
            type(selection_margin_pp) not in (int, float)
            or not math.isfinite(selection_margin_pp)
            or not 0 <= selection_margin_pp < 100
        ):
            raise ValueError("Selection margin must be finite and in [0, 100)")
        self.selection_margin_pp = selection_margin_pp
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.pack, self.evaluator, self.mode, self.guard = pack, evaluator, mode, guard
        self.deadline_at = deadline_at
        self.problem_timeout_seconds = problem_timeout_seconds
        self.web_config = web_config
        if proof_history_scope is not None and mode == "correctness":
            raise ValueError("Proof history is unavailable in correctness-only mode")
        self.proof_history_scope = deepcopy(proof_history_scope)
        self.proof_history = None
        self.history_queries = []
        self._tool_request = None
        self.restart_history = (
            RestartHistory(self.folder, restart_scope)
            if restart_scope is not None
            else None
        )
        self.row = pack["row"]
        self.versions = required_versions(pack)
        self.source_tools = SourceTools(
            evaluator, self.row, self.versions, semantic_config=semantic_config
        )
        self.original = (
            original_measurement
            if original_measurement is not None
            else original_evaluation(pack)
        )
        require_valid(self.original, self.row, self.row["src"])
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
        if proof_history_scope is not None:
            from proof_eval.evidence.proof_history import ProofHistory

            self.proof_history = ProofHistory(
                self.folder,
                self.proof_history_scope,
                self.seed_code,
                self.seed_evaluation,
                self.versions,
            )
            # A killed process may leave a query-created fragment in SQLite
            # before its journal commit. Reconstruct from the two authoritative
            # ledgers on reopen so those orphan IDs cannot become visible.
            self.proof_history.invalidate()
            self.proof_history.sync(self.checks)
            self.history_queries = read_queries(self.folder)
            self.proof_history.restore_queries(self.history_queries)
        self._save_state()

    def _restore(self, record):
        self.checks.append(record)
        self.cache[record["code_sha256"]] = record["evaluation"]
        if record["all_versions_passed"] and self.first_valid_code is None:
            self.first_valid_code = record["code"]
        if record["accepted"]:
            self.best_code, self.best_evaluation = record["code"], record["evaluation"]

    def reset_for_attempt(self) -> None:
        """Clear the previous finish decision in memory and durable state."""
        with self.lock:
            self.finished = None
            (self.folder / "finished.json").unlink(missing_ok=True)
            self._save_state()

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

    def check(
        self,
        code: str,
        *,
        origin: str = "agent_tool",
        base_check_id: int | None = None,
        base_unknown: bool = False,
    ) -> dict:
        with self.lock:
            if not isinstance(code, str):
                raise ValueError("Candidate code must be text")
            history_metadata = None
            if self.proof_history is not None:
                self.guard()
                if type(base_unknown) is not bool or (
                    base_check_id is not None and base_unknown
                ):
                    raise ValueError("Declare one base check or explicitly unknown")
                if (
                    origin == "agent_tool"
                    and base_check_id is None
                    and not base_unknown
                ):
                    raise ValueError(
                        "Proof history checks require --base-check ID or --base-unknown"
                    )
                self.proof_history.sync(self.checks)
                base = self.proof_history.validate_base(base_check_id, len(self.checks))
                try:
                    evaluated_code = validate_candidate(self.row, code)[0]
                except ValueError:
                    evaluated_code = None
                history_metadata = self.proof_history.check_metadata(
                    code=code,
                    base_check=base,
                    base_provenance="model_declared" if base is not None else "unknown",
                    evaluated_code=evaluated_code,
                )
            elif base_check_id is not None or base_unknown:
                raise ValueError("Proof history is disabled")
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
                and numeric
                > self.best_evaluation["scores"]["combined_pct"]
                + self.selection_margin_pp
            )
            feedback = build_validity_feedback(evaluation, self.versions)
            previous = self.best_evaluation["scores"]["combined_pct"]
            deltas = component_deltas(evaluation, self.best_evaluation, self.versions)
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
            if history_metadata is not None:
                record["history"] = history_metadata
                record["tool_request"] = deepcopy(self._tool_request)
            write_jsonl(self.folder / "checks.jsonl", self.checks + [record])
            self._restore(record)
            self._save_state()
            if self.mode == "correctness":
                return feedback
            response = {
                "kind": "lean_score_feedback",
                **self._score_view(evaluation),
                "correctness": feedback,
                "all_versions_passed": valid,
                "accepted_as_best": accepted,
                "duplicate": duplicate,
                "delta_from_previous_best_pp": (
                    None if numeric is None else numeric - previous
                ),
                "component_delta_from_previous_best_pp": deltas,
                "best_remaining_score_loss_pp": remaining_score_loss(
                    self.best_evaluation, self.versions
                ),
                "best_scores": self.best_evaluation["scores"],
                "best_proof": self.best_code,
            }
            if history_metadata is not None:
                response.update(
                    history_check_id=record["number"],
                    history_base_check_id=history_metadata["base_check"],
                    history_base_provenance=history_metadata["base_provenance"],
                    history_snapshot_id=history_metadata["snapshot_id"],
                    history_best_check_id=best_check_id(
                        self.checks, self.seed_code, self.best_code
                    ),
                    history_available_checks=len(self.checks),
                )
            return response

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
            "best_remaining_score_loss_pp": remaining_score_loss(
                self.best_evaluation, self.versions
            ),
            "finished": self.finished,
        }
        if self.deadline_at is not None:
            response.update(
                time_remaining_seconds=max(0.0, self.deadline_at - time.time()),
                problem_timeout_seconds=self.problem_timeout_seconds,
            )
        if self.proof_history is not None:
            response.update(
                history_best_check_id=best_check_id(
                    self.checks, self.seed_code, self.best_code
                ),
                history_available_checks=len(self.checks),
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

    def deterministic(
        self, code: str, *, origin: str = "agent_tool", cleanup=None
    ) -> dict:
        """Host cleanup at search boundaries, preserving raw and cleaned evidence."""
        with self.lock:
            if (
                origin not in ("initial_harness", "final_harness")
                or self.mode != "score_edges"
            ):
                raise ValueError(
                    "Deterministic cleanup is available only to the host at search boundaries"
                )
            cleanup_fn = cleanup if cleanup is not None else self.cleanup
            if cleanup_fn is None:
                raise ValueError("No deterministic portfolio configured")
            self.guard()
            self.check(code, origin="deterministic_input")
            before = self.checks[-1]
            valid = before["all_versions_passed"]
            pending = self.folder / "cleanup_started.json"
            write_json(
                pending,
                {
                    **({"origin": origin} if origin == "initial_harness" else {}),
                    "input_check": before["number"],
                    "input_code_sha256": before["code_sha256"],
                    "before": {
                        "proof": self.best_code,
                        "evaluation": self.best_evaluation,
                    },
                },
            )
            job = cleanup_fn(code) if valid else None
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

    def dispatch_tool_request(
        self, request: dict, *, request_id: str, service_id: str
    ) -> dict:
        """Attach the host RPC identity to committed history, including lost replies."""
        if self.proof_history is None:
            return self.dispatch(request)
        with self.lock:
            previous = self._tool_request
            self._tool_request = {"request_id": request_id, "service_id": service_id}
            try:
                return self.dispatch(request)
            finally:
                self._tool_request = previous

    def dispatch(self, request: dict) -> dict:
        if not isinstance(request, dict):
            raise ValueError("Tool request must be an object")
        op = request.get("op")
        if (
            op == "check"
            and {"op", "code"} <= set(request)
            and set(request) <= {"op", "code", "base_check_id", "base_unknown"}
            and isinstance(request["code"], str)
        ):
            if "base_unknown" in request and request["base_unknown"] is not True:
                raise ValueError("base_unknown must be true when supplied")
            if "base_check_id" in request and request["base_check_id"] is None:
                raise ValueError("Use base_unknown for an unknown editing base")
            return self.check(
                request["code"],
                base_check_id=request.get("base_check_id"),
                base_unknown=request.get("base_unknown", False),
            )
        if op == "history":
            with self.lock:
                if self.proof_history is None:
                    raise ValueError("Proof history is disabled")
                self.guard()
                response = query_history(
                    self.proof_history,
                    self.proof_history_scope,
                    self.folder,
                    self.history_queries,
                    self.checks,
                    request,
                    self._tool_request,
                )
                self.guard()
                return response
        if op == "remember" and set(request) == {"op", "kind", "text"}:
            with self.lock:
                if self.restart_history is None or self.finished:
                    raise ValueError("Restart notes are unavailable in this session")
                return self.restart_history.remember(request["kind"], request["text"])
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
        if op in ("web_search", "web_open"):
            with self.lock:
                self.guard()
                web.guard(self.web_config)
                path = self.folder / "web_requests.jsonl"
                records = (
                    [json.loads(line) for line in path.read_text().splitlines()]
                    if path.exists()
                    else []
                )
                record = {
                    "number": len(records) + 1,
                    "at": now(),
                    "request": request,
                    "status": "started",
                    "config_sha256": fingerprint(self.web_config),
                }
                records.append(record)
                write_jsonl(path, records)
                try:
                    response = web.retrieve(
                        self.web_config,
                        request,
                        self.folder,
                        record["number"],
                        remaining_seconds=(
                            (self.deadline_at - time.time())
                            if self.deadline_at is not None
                            else None
                        ),
                    )
                except Exception as error:
                    response = {
                        "kind": "tool_error",
                        "error": f"{type(error).__name__}: {error}",
                    }
                record.update(status="completed", finished_at=now(), response=response)
                body = self.folder / "web_responses" / f"{record['number']:04d}.body"
                if body.exists():
                    record["body_path"] = str(body.relative_to(self.folder))
                    record["body_sha256"] = digest(body)
                write_jsonl(path, records)
                self.guard()
                return response
        if op in ("search", "read", "outline", "semantic_search"):
            with self.lock:
                self.guard()
                response = self.source(request)
                if self.restart_history is not None:
                    self.restart_history.record(
                        "source_observation",
                        {
                            "request": request,
                            "response": response,
                        },
                    )
                if op == "semantic_search":
                    path = self.folder / "semantic_searches.jsonl"
                    records = (
                        [json.loads(line) for line in path.read_text().splitlines()]
                        if path.exists()
                        else []
                    )
                    records.append(
                        {"at": now(), "request": request, "response": response}
                    )
                    write_jsonl(path, records)
                return response
        raise ValueError("Unknown operation or invalid fields")

    def source(self, request):
        return self.source_tools.source(request)
