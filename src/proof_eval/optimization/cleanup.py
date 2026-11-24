"""Fixed, bounded end-of-search deterministic portfolio with resumable evidence."""

from __future__ import annotations

import fcntl
import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, read, sha, write_json
from proof_eval.verification.feedback import all_versions_passed
from proof_eval.verification.references import require_valid, score, versions

from .engine import Budget, optimize

METHODS = (
    "lint",
    "simp",
    "wrappers",
    "facts",
    "reuse",
    "menu",
    "search",
    "simp_min",
    "arith_min",
    "rw_min",
)
BUDGET = Budget(rounds=3, trials=32, sites=6)
PROOF_THEORY_METHODS = (
    "delete",
    "collapse",
    "consolidate",
    "proof_theory",
    "relax",
    "golf",
)
COUNTERS = (
    "attempts",
    "analysis_requests",
    "lean_candidate_checks",
    "cache_hits",
    "accepted_transitions",
    "elapsed_seconds",
)
COMPLETE_STOPS = {
    "no_new_proposals",
    "no_improving_proposal",
    "trial_limit",
    "round_limit",
}


def append_event(path, event):
    with path.open("a") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()


class AllVersionsEvaluator:
    """Eligibility adapter, never a mutation of the evaluator or its cache."""

    def __init__(self, evaluator, required, emit):
        self.evaluator, self.required, self.emit = evaluator, list(required), emit
        self.latest = {}

    def __getattr__(self, name):
        return getattr(self.evaluator, name)

    def evaluate(self, name, code, *, versions="all"):
        raw = self.evaluator.evaluate(name, code, versions=versions)
        if versions != "all":
            return raw
        eligible = raw.get("status") == "passed" and all_versions_passed(
            raw, self.required
        )
        exposed = deepcopy(raw)
        if raw.get("status") == "passed" and not eligible:
            exposed["status"] = "policy_compatibility_rejected"
        event = {
            "kind": "all_version_eligibility",
            "name": name,
            "proof_sha256": sha(code),
            "required_versions": self.required,
            "eligible": eligible,
            "optimizer_status": exposed.get("status"),
            "authoritative_status": raw.get("status"),
            "reason": (
                None
                if eligible
                else "exact_required_versions_not_all_passed_or_score_unavailable"
            ),
            "evaluation": raw,
        }
        self.latest[sha(code)] = event
        self.emit(event)
        return exposed


def cleanup_proof(
    *,
    evaluator,
    row,
    proof,
    folder,
    provenance,
    optimize_fn=optimize,
    guard=None,
    methods: tuple[str, ...] = METHODS,
):
    """Run/resume ten bounded methods once, retaining checkpoints and raw checks.

    ``provenance`` must identify the dataset, contexts, reference records and
    implementation. The matrix supplies a read-only guard before each method.
    Incomplete discovery is terminal evidence for this invocation, never a claim
    that the full portfolio found no improvement. Reusing a completed job makes
    no evaluator calls. A crashed method resumes its exact saved optimizer state.
    """
    if (
        not methods
        or len(set(methods)) != len(methods)
        or set(methods) - set(METHODS + PROOF_THEORY_METHODS)
    ):
        raise ValueError("Select nonempty, unique cleanup methods")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    spec = {
        "schema_version": 1,
        "name": row["name"],
        "row_sha256": fingerprint(row),
        "input_proof_sha256": sha(proof),
        "methods": list(methods),
        "budget": asdict(BUDGET),
        "required_versions": versions(row),
        "provenance": provenance,
    }
    with (folder / ".job.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        config = folder / "job_config.json"
        if config.exists() and read(config) != spec:
            raise ValueError("Cleanup job configuration changed")
        write_json(config, spec)
        if (folder / "result.json").exists():
            result = read(folder / "result.json")
            require_valid(result["evaluation"], row, result["proof"])
            if result["input_proof_sha256"] != sha(proof) or result[
                "job_config_sha256"
            ] != fingerprint(spec):
                raise ValueError("Completed cleanup identity changed")
            for relative, expected in result["stage_result_sha256"].items():
                if digest(folder / relative) != expected:
                    raise ValueError("Completed cleanup method evidence changed")
            return result
        if guard:
            guard()
        initial_path = folder / "initial_evaluation.json"
        initial = (
            read(initial_path)
            if initial_path.exists()
            else evaluator.evaluate(row["name"], proof, versions="all")
        )
        require_valid(initial, row, proof)
        if not initial_path.exists():
            write_json(initial_path, initial)
        (folder / "input.lean").write_text(proof)
        adapter = AllVersionsEvaluator(
            evaluator,
            versions(row),
            lambda event: append_event(folder / "policy_events.jsonl", event),
        )
        code, stages = proof, []
        for index, method in enumerate(methods, 1):
            if guard:
                guard()
            stage = folder / "stages" / f"{index:02d}_{method}"
            stage.mkdir(parents=True, exist_ok=True)
            stage_config = {
                "method": method,
                "input_sha256": sha(code),
                "job_config_sha256": fingerprint(spec),
            }
            if (stage / "config.json").exists() and read(
                stage / "config.json"
            ) != stage_config:
                raise ValueError("Cleanup method input changed")
            write_json(stage / "config.json", stage_config)
            if (stage / "result.json").exists():
                result = read(stage / "result.json")
            else:
                checkpoint = stage / "checkpoint.json"

                def emit(event):
                    if event.get("kind") == "candidate" and event.get(
                        "all_versions_requested"
                    ):
                        policy = adapter.latest.get(sha(event["proof"]))
                        if policy is not None:
                            event = {
                                **event,
                                "eligibility_policy": {
                                    key: policy[key]
                                    for key in (
                                        "eligible",
                                        "optimizer_status",
                                        "authoritative_status",
                                        "reason",
                                    )
                                },
                                "authoritative_evaluation": policy["evaluation"],
                            }
                    append_event(stage / "trials.jsonl", event)

                result = optimize_fn(
                    adapter,
                    row,
                    code,
                    method,
                    BUDGET,
                    emit,
                    lambda state: write_json(checkpoint, state),
                    state=read(checkpoint) if checkpoint.exists() else None,
                )
                require_valid(result["final"], row, result["proof"])
                write_json(stage / "result.json", result)
            require_valid(result["final"], row, result["proof"])
            require_valid(result["initial"], row, code)
            if (
                result["method"] != method
                or result["name"] != row["name"]
                or result["source"] != row["source"]
            ):
                raise ValueError("Cleanup method result identity changed")
            if score(result["final"]) < score(result["initial"]):
                raise ValueError("Cleanup method regressed its valid input")
            stages.append(result)
            code = result["proof"]
        if guard:
            guard()
        final = evaluator.evaluate(row["name"], code, versions="all")
        require_valid(final, row, code)
        incomplete = [
            stage["method"]
            for stage in stages
            if stage.get("stop_reason") not in COMPLETE_STOPS
        ]
        result = {
            "name": row["name"],
            "source": row["source"],
            "input_proof": proof,
            "input_proof_sha256": sha(proof),
            "proof": code,
            "initial_evaluation": initial,
            "evaluation": final,
            "all_versions_valid": True,
            "status": "incomplete_discovery" if incomplete else "complete",
            "incomplete_methods": incomplete,
            "job_config_sha256": fingerprint(spec),
            "stage_result_sha256": {
                str(path.relative_to(folder)): digest(path)
                for path in sorted((folder / "stages").glob("*/result.json"))
            },
            "stages": stages,
            "counters": {
                key: sum(stage.get(key, 0) for stage in stages) for key in COUNTERS
            },
            "verification_accounting": "Optimizer counters exclude initial/final whole-proof validation; these checks use the existing evaluator cache.",
            "changed": code != proof,
        }
        write_json(folder / "result.json", result)
        return result
