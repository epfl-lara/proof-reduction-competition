"""Supervise one whole theorem independently of the native provider and its tools."""

from __future__ import annotations

import fcntl
import multiprocessing
import os
import subprocess
import sys
import time
from pathlib import Path

from proof_eval.evidence.io import fingerprint, now, read, write_json
from proof_eval.paths import ROOT
from proof_eval.providers.contracts import AgentGenerator
from proof_eval.providers.processes import stop_tree
from proof_eval.verification.api import Evaluator

from .limits import native_deadline_reached, start_budget
from .recovery import recover_cell


class _CustomWorker:
    """Fork an explicitly supplied Python generator without serializing it."""

    def __init__(self, arguments: tuple, generator: AgentGenerator, out, err):
        self.process = multiprocessing.get_context("fork").Process(
            target=_custom_worker,
            args=(arguments, generator, out.fileno(), err.fileno()),
        )
        self.process.start()
        self.pid = self.process.pid

    @property
    def returncode(self) -> int | None:
        return self.process.exitcode

    def wait(self, timeout: float | None) -> None:
        self.process.join(timeout)
        if self.process.is_alive():
            raise subprocess.TimeoutExpired("custom theorem worker", timeout)


def _custom_worker(
    arguments: tuple, generator: AgentGenerator, out: int, err: int
) -> None:
    from proof_eval.providers.processes import enable_subreaper

    from .search import _run_cell

    os.setsid()
    os.dup2(out, 1)
    os.dup2(err, 2)
    enable_subreaper()
    _run_cell(*arguments, generator=generator)


def run_cell(
    output: Path,
    config: dict,
    pack: dict,
    model: str,
    effort: str,
    evaluator: Evaluator,
    *,
    generator: AgentGenerator | None = None,
) -> dict:
    """Isolate the worker; enforce a whole-problem deadline only when configured."""
    folder = (
        output / "cells" / fingerprint((pack["name"], model, effort, config["mode"]))
    )
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".budget.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (folder / "result.json").exists():
            return read(folder / "result.json")
        if (folder / "budget_end.json").exists():
            return recover_cell(folder, config, pack, model, effort, evaluator)
        if (folder / "cell_process.json").exists():
            raise RuntimeError(
                "Started theorem worker has no terminal result; not restarted or resampled"
            )
        if config["problem_timeout_seconds"] is None and (
            config.get("budget_tracking") != "cost"
            or (folder / "budget_started.json").exists()
        ):
            raise ValueError("Cost-only search requires no saved wall-time deadline")
        request = {
            "output": str(output),
            "config": config,
            "pack": pack,
            "model": model,
            "effort": effort,
            "evaluator": {
                "dataset_path": str(evaluator.dataset.path),
                "environments_path": config.get(
                    "environments_path", str(ROOT / "environments.local.json")
                ),
                "cache_dir": str(evaluator.store.root),
                "timeout": evaluator.timeout,
                "version_workers": evaluator.version_workers,
            },
        }
        manifest = folder / "cell_request.json"
        write_json(manifest, request)
        seconds = config["problem_timeout_seconds"]
        budget = (
            start_budget(
                folder, seconds, announce=config.get("provider") == "lemex-local"
            )
            if seconds is not None
            else None
        )
        if (
            config.get("initial_pipeline_version")
            and not (folder / "problem_started.json").exists()
        ):
            write_json(
                folder / "problem_started.json",
                {
                    "at": now(),
                    "started_epoch": budget["started_epoch"] if budget else time.time(),
                    "scope": (
                        "model_phase_prepared_original_admission_search"
                        if config.get("original_measurement_policy") == "prepared"
                        else (
                            "model_phase_original_and_selected_measurement_admission_search"
                            if config.get("model_phase_version")
                            else "original_measurement_initial_optimization_model_search"
                        )
                    ),
                },
            )
        with (
            (folder / "worker.stdout.log").open("w") as out,
            (folder / "worker.stderr.log").open("w") as err,
        ):
            if generator is None:
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "proof_eval.interfaces.worker",
                        str(manifest),
                    ],
                    stdout=out,
                    stderr=err,
                    start_new_session=True,
                    pass_fds=(lock.fileno(),),
                )
            else:
                child = _CustomWorker(
                    (output, config, pack, model, effort, evaluator),
                    generator,
                    out,
                    err,
                )
            write_json(
                folder / "cell_process.json", {"pid": child.pid, "started_at": now()}
            )
            try:
                child.wait(
                    timeout=(
                        max(0.0, budget["deadline_epoch"] - time.time())
                        if budget is not None
                        else None
                    )
                )
            except subprocess.TimeoutExpired:
                expired = True
                worker_exited = False
            else:
                worker_exited = True
                # The native timeout can finish the worker before wait() notices
                # the problem deadline. Require its durable stop evidence.
                expired = (
                    budget is not None
                    and child.returncode == 0
                    and native_deadline_reached(folder)
                )
            if expired:
                stopped = time.time()
                # A successfully waited process has been reaped; its PID must
                # never be used for signalling after possible reuse.
                owned = (
                    {"terminated_pids": [], "temporary_sources": []}
                    if worker_exited
                    else stop_tree(child.pid)
                )
                if not worker_exited:
                    child.wait(timeout=5)
                write_json(
                    folder / "budget_end.json",
                    {
                        "exhausted": True,
                        "work_stopped_epoch": stopped,
                        "at": now(),
                        "worker_reaped_before_deadline_recovery": worker_exited,
                        **owned,
                    },
                )
                # Only delete compiler temporaries belonging to this worker in pinned projects.
                projects = set(evaluator.projects.values())
                for source in owned["temporary_sources"]:
                    path = Path(source)
                    if path.parent in projects:
                        path.unlink(missing_ok=True)
                # A worker can save its result while stop_tree drains descendants.
                # Finalize only after the supervisor's deadline evidence is saved.
                return recover_cell(folder, config, pack, model, effort, evaluator)
        if child.returncode:
            raise RuntimeError(
                f"Theorem worker exited {child.returncode}; inspect {folder / 'worker.stderr.log'}"
            )
        return read(folder / "result.json")
