"""Build missing task-context imports before references, rollouts, or clocks."""

from __future__ import annotations

import fcntl
import os
import signal
import subprocess
import time
from pathlib import Path

from proof_eval.evidence.immutable import immutable, read, sha
from proof_eval.training.data import validate_reserve


def task_context(row: dict, project: Path) -> str:
    if not row.get("file_path"):
        return row.get("header", "")
    path = (project / row["file_path"]).resolve()
    if not path.is_relative_to(project.resolve()):
        raise ValueError("Task context escapes original source project")
    return path.read_text()


def restore_imports(plan, root, home, dataset_dir, environments):
    from proof_eval.training.import_assets import (
        _facade,
        _imports,
        _libraries,
        _missing,
    )
    from proof_eval.verification.backend import LeanBackend

    rows = validate_reserve(dataset_dir)
    policy = plan["import_preparation"]
    deadline = time.monotonic() + policy["deadline_seconds"]
    records = []
    support = root / "import-preparation"
    for entry in read(environments)["projects"]:
        selected = [
            r
            for r in rows
            if r["source"] == entry["source"]
            and any(entry["version"] in v for v in r["version_info"])
        ]
        if not selected:
            continue
        project = Path(entry["path"]).resolve()
        version = entry["version"]
        label = entry["source"] + "-" + version
        compiler = (
            Path(os.environ["ELAN_HOME"])
            / "toolchains"
            / ("leanprover--lean4---" + version)
        ).resolve()
        # Do not wait for or replace an existing lock.
        with (project / ".lake/arena-rl-repair.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            original = LeanBackend(timeout=300)._environment(
                selected[0], version, project
            )
            texts = {
                str((project / r["file_path"]).resolve()): sha(project / r["file_path"])
                for r in selected
                if r.get("file_path")
            }
            modules = set().union(
                *[_imports(task_context(r, project)) for r in selected]
            )
            libraries = _libraries(project, compiler)
            missing = _missing(modules, libraries)
            record = {
                "project": str(project),
                "version": version,
                "original_environment": original,
                "task_context_sha256": texts,
                "required_imports": sorted(modules),
                "missing_before": missing,
                "model_calls": 0,
                "at_epoch": time.time(),
            }
            for base in (root, home):
                immutable(
                    base / "import-preparation" / (label + "-started.json"), record
                )
            if missing:
                facade = _facade(compiler, support, policy["jobs"])
                env = dict(
                    os.environ,
                    LEAN_NUM_THREADS=str(policy["jobs"]),
                    LAKE_OVERRIDE_LEAN="true",
                    LEAN_SYSROOT=str(facade),
                    ELAN_TOOLCHAIN="leanprover/lean4:" + version,
                )
                command = [
                    str(compiler / "bin/lake"),
                    "build",
                    *["+" + m + ":olean" for m in missing],
                ]
                seconds = min(
                    policy["per_project_seconds"], deadline - time.monotonic()
                )
                if seconds <= 0:
                    raise TimeoutError("Finite import restoration deadline")
                log_path = home / "import-preparation" / (label + ".log")
                with log_path.open("xb") as stream:
                    child = subprocess.Popen(
                        command,
                        cwd=project,
                        env=env,
                        stdout=stream,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                        pass_fds=(lock.fileno(),),
                    )
                    process = {
                        "pid": child.pid,
                        "start_ticks": Path(f"/proc/{child.pid}/stat")
                        .read_text()
                        .rsplit(")", 1)[1]
                        .split()[19],
                        "command": command,
                        "deadline_seconds": seconds,
                        "at_epoch": time.time(),
                    }
                    for base in (root, home):
                        immutable(
                            base / "import-preparation" / (label + "-process.json"),
                            process,
                        )
                    try:
                        code = child.wait(timeout=seconds)
                    except BaseException:
                        os.killpg(child.pid, signal.SIGTERM)
                        try:
                            child.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid, signal.SIGKILL)
                            child.wait(timeout=5)
                        raise
                record.update(
                    returncode=code,
                    log_sha256=sha(log_path),
                    log_bytes=log_path.stat().st_size,
                )
                if code:
                    raise RuntimeError(
                        "Original dependency build failed: " + str(log_path)
                    )
            if _missing(modules, libraries):
                raise RuntimeError("Original task imports remain unavailable: " + label)
            if texts != {p: sha(p) for p in texts}:
                raise RuntimeError(
                    "Original source bytes changed during dependency build"
                )
            if (
                LeanBackend(timeout=300)._environment(selected[0], version, project)
                != original
            ):
                raise RuntimeError(
                    "Original source environment changed during dependency build"
                )
            record.update(
                status="passed", missing_after=[], source_environment_unchanged=True
            )
            for base in (root, home):
                immutable(
                    base / "import-preparation" / (label + "-finished.json"), record
                )
            records.append(record)
    report = {
        "status": "passed",
        "projects": records,
        "dataset_sha256": sha(dataset_dir / "rl-reserved.jsonl"),
        "model_calls": 0,
        "source_proofs_modified": False,
        "at_epoch": time.time(),
    }
    for base in (root, home):
        immutable(base / "import-preparation" / "finished.json", report)
    return report
