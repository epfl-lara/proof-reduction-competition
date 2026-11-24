"""Hard-bounded initial optimization, retaining only fully verified improvements."""

from __future__ import annotations

import multiprocessing
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, now, read, write_json
from proof_eval.providers.processes import enable_subreaper, stop_tree
from proof_eval.verification.feedback import all_versions_passed
from proof_eval.verification.references import require_valid, score
from proof_eval.verification.references import versions as required_versions

from .cleanup import BUDGET, METHODS, PROOF_THEORY_METHODS, cleanup_proof
from .limits import discovery_limit_evidence

MAX_SECONDS = 300.0
ALL_METHODS = METHODS + PROOF_THEORY_METHODS


def validate_methods(methods: tuple[str, ...], seconds: float) -> None:
    if len(set(methods)) != len(methods) or set(methods) - set(ALL_METHODS):
        raise ValueError("Select unique supported deterministic methods")
    if type(seconds) not in (int, float) or not 0 < seconds <= MAX_SECONDS:
        raise ValueError(
            "Initial deterministic work must be limited to at most 300 seconds"
        )


class _Recorder:
    def __init__(self, evaluator, row: dict, folder: Path, deadline: float):
        self.evaluator, self.row, self.folder, self.deadline = (
            evaluator,
            row,
            folder,
            deadline,
        )
        self.certificates = read(folder / "certificates.json")

    def __getattr__(self, name):
        return getattr(self.evaluator, name)

    def evaluate(self, name, code, *, versions="all"):
        result = self.evaluator.evaluate(name, code, versions=versions)
        completed_epoch = time.time()
        if (
            versions == "all"
            and completed_epoch < self.deadline
            and result.get("status") == "passed"
            and all_versions_passed(result, required_versions(self.row))
            and score(result)
            > score(self.certificates[-1]["evaluation"]) + BUDGET.min_gain
        ):
            require_valid(result, self.row, code)
            self.certificates.append(
                {
                    "proof": code,
                    "evaluation": result,
                    "at": datetime.fromtimestamp(
                        completed_epoch, timezone.utc
                    ).isoformat(),
                }
            )
            write_json(self.folder / "certificates.json", self.certificates)
        return result


def _worker(evaluator, row, proof, folder, methods, provenance, deadline):
    os.setsid()
    enable_subreaper()
    try:
        cleanup_proof(
            evaluator=_Recorder(evaluator, row, folder, deadline),
            row=row,
            proof=proof,
            folder=folder / "job",
            provenance=provenance,
            methods=methods,
        )
    except BaseException as error:
        write_json(
            folder / "worker_error.json",
            {"at": now(), "error": f"{type(error).__name__}: {error}"},
        )
        raise


def run_bounded(
    *,
    evaluator,
    row: dict,
    proof: str,
    evaluation: dict,
    folder: Path,
    methods: tuple[str, ...],
    seconds: float = MAX_SECONDS,
    deadline_epoch: float | None = None,
    provenance: dict | None = None,
) -> dict:
    """Stop the optimizer and its Lean children at one nonrenewable deadline.

    Original measurement is supplied by the caller and precedes this phase.
    The outer problem clock includes both phases. Completed within-run results
    can be read again, but an indeterminate optimizer is never restarted.
    """
    validate_methods(methods, seconds)
    require_valid(evaluation, row, proof)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    spec = {
        "name": row["name"],
        "proof_sha256": fingerprint(proof),
        "methods": list(methods),
        "seconds": seconds,
        "provenance": provenance or {},
        "discovery_limit_policy": "retain_verified_proof_on_terminal_timeout",
    }
    if (folder / "result.json").exists():
        result = read(folder / "result.json")
        if result["spec"] != spec:
            raise ValueError("Initial optimization configuration changed")
        return result
    if (folder / "started.json").exists():
        raise RuntimeError("Initial optimizer is indeterminate; not restarted")
    started = time.time()
    deadline = (
        min(started + seconds, deadline_epoch)
        if deadline_epoch is not None
        else started + seconds
    )
    write_json(
        folder / "started.json",
        {"spec": spec, "started_epoch": started, "deadline_epoch": deadline},
    )
    write_json(
        folder / "certificates.json",
        [{"proof": proof, "evaluation": evaluation, "at": now()}],
    )
    status, stopped = "disabled", started
    if methods and deadline > started:
        process = multiprocessing.get_context("fork").Process(
            target=_worker,
            args=(evaluator, row, proof, folder, methods, provenance or {}, deadline),
        )
        process.start()
        write_json(folder / "process.json", {"pid": process.pid, "at": now()})
        process.join(max(0.0, deadline - time.time()))
        if process.is_alive():
            stopped = time.time()
            owned = stop_tree(process.pid)
            process.join(5)
            write_json(
                folder / "stopped.json",
                {"at": now(), "work_stopped_epoch": stopped, **owned},
            )
            for source in owned["temporary_sources"]:
                path = Path(source)
                if path.parent in set(evaluator.projects.values()):
                    path.unlink(missing_ok=True)
            status = "time_limit"
        else:
            stopped = time.time()
            status = "complete" if process.exitcode == 0 else "failed"
            if status == "complete" and (folder / "job/result.json").exists():
                status = read(folder / "job/result.json")["status"]
                if status == "incomplete_discovery" and discovery_limit_evidence(
                    folder
                ):
                    status = "discovery_limit"
    elif methods:
        status = "time_limit"
    return finish_bounded(folder, row, status=status, stopped=stopped)


def finish_bounded(folder: Path, row: dict, *, status: str, stopped: float) -> dict:
    """Finalize saved certificates after the owner has stopped the worker; no Lean."""
    marker = read(folder / "started.json")
    spec, started, deadline = (
        marker["spec"],
        marker["started_epoch"],
        marker["deadline_epoch"],
    )
    certificates = read(folder / "certificates.json")
    best = certificates[-1]
    require_valid(best["evaluation"], row, best["proof"])
    result = {
        "spec": spec,
        "status": status,
        "started_epoch": started,
        "deadline_epoch": deadline,
        "work_stopped_epoch": stopped,
        "elapsed_seconds": max(0.0, stopped - started),
        "certificates_sha256": digest(folder / "certificates.json"),
        "proof": best["proof"],
        "evaluation": best["evaluation"],
        "gain_pp": score(best["evaluation"]) - score(certificates[0]["evaluation"]),
        "accepted_improvements": len(certificates) - 1,
        "stage_result_sha256": {
            str(p.relative_to(folder)): digest(p)
            for p in sorted((folder / "job/stages").glob("*/result.json"))
        },
        "discovery_limit_evidence": discovery_limit_evidence(folder),
    }
    write_json(folder / "result.json", result)
    return result
