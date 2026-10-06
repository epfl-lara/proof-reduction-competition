"""Supervise one whole theorem independently of the native provider and its tools."""

from __future__ import annotations

import fcntl
import subprocess
import sys
import time
from pathlib import Path

from proof_eval.evidence.io import fingerprint, now, read, write_json
from proof_eval.providers.processes import stop_tree
from proof_eval.verification.api import Evaluator

from .limits import start_budget
from .recovery import recover_cell


def run_cell(
    output: Path,
    config: dict,
    pack: dict,
    model: str,
    effort: str,
    evaluator: Evaluator,
) -> dict:
    """A fixed deadline includes provider admission, Lean calls and final cleanup."""
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
        request = {
            "output": str(output),
            "config": config,
            "pack": pack,
            "model": model,
            "effort": effort,
            "evaluator": {
                "dataset_path": str(evaluator.dataset.path),
                "environments_path": config["environments_path"],
                "cache_dir": str(evaluator.store.root),
                "timeout": evaluator.timeout,
            },
        }
        manifest = folder / "cell_request.json"
        write_json(manifest, request)
        budget = start_budget(folder, config["problem_timeout_seconds"])
        with (
            (folder / "worker.stdout.log").open("w") as out,
            (folder / "worker.stderr.log").open("w") as err,
        ):
            child = subprocess.Popen(
                [sys.executable, "-m", "proof_eval.interfaces.worker", str(manifest)],
                stdout=out,
                stderr=err,
                start_new_session=True,
                pass_fds=(lock.fileno(),),
            )
            write_json(
                folder / "cell_process.json", {"pid": child.pid, "started_at": now()}
            )
            try:
                child.wait(timeout=max(0.0, budget["deadline_epoch"] - time.time()))
            except subprocess.TimeoutExpired:
                stopped = time.time()
                owned = stop_tree(child.pid)
                child.wait(timeout=5)
                write_json(
                    folder / "budget_end.json",
                    {
                        "exhausted": True,
                        "work_stopped_epoch": stopped,
                        "at": now(),
                        **owned,
                    },
                )
                # Only delete compiler temporaries belonging to this worker in pinned projects.
                projects = set(evaluator.projects.values())
                for source in owned["temporary_sources"]:
                    path = Path(source)
                    if path.parent in projects:
                        path.unlink(missing_ok=True)
                if (folder / "result.json").exists():
                    return read(folder / "result.json")
                return recover_cell(folder, config, pack, model, effort, evaluator)
        if child.returncode:
            raise RuntimeError(
                f"Theorem worker exited {child.returncode}; inspect {folder / 'worker.stderr.log'}"
            )
        return read(folder / "result.json")
