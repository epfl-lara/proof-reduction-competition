"""Bind a forced native deadline to host-owned process identities and full reaping."""

from __future__ import annotations

from pathlib import Path

from proof_eval.evidence.io import fingerprint, read, write_json


class CleanupEvidenceError(ValueError):
    """A deadline happened, but clean native termination is not established."""


def save_native_stop(
    folder: Path, process: dict, stopped: dict, *, returncode: int
) -> None:
    """Persist a native stop only after the caller reaped its direct supervisor."""
    if type(returncode) is not int:
        raise CleanupEvidenceError("Native supervisor has not been reaped")
    write_json(
        folder / "native_timeout_cleanup.json",
        {
            "schema_version": 1,
            "supervisor": {k: process[k] for k in ("pid", "start_ticks")},
            "supervisor_reaped": True,
            "supervisor_returncode": returncode,
            "stopped": stopped,
            "stopped_sha256": fingerprint(stopped),
        },
    )


def native_stop(folder: Path, process: dict) -> dict | None:
    """Read only this attempt's exact native stop; never borrow the worker's PID."""
    path = folder / "native_timeout_cleanup.json"
    if not path.exists():
        return None
    value = read(path)
    if (
        value.get("schema_version") != 1
        or value.get("supervisor") != {k: process[k] for k in ("pid", "start_ticks")}
        or value.get("supervisor_reaped") is not True
        or type(value.get("supervisor_returncode")) is not int
        or value.get("stopped_sha256") != fingerprint(value.get("stopped"))
    ):
        raise CleanupEvidenceError("Native timeout cleanup identity or hash changed")
    return value["stopped"]


def refusal(folder: Path, process: dict, stopped: dict, error: Exception) -> dict:
    """Keep a rejected cleanup claim durable without certifying or replaying it."""
    value = {
        "schema_version": 1,
        "status": "refused",
        "error": str(error),
        "supervisor": {k: process[k] for k in ("pid", "start_ticks")},
        "stopped": stopped,
        "stopped_sha256": fingerprint(stopped),
    }
    write_json(folder / "deadline_cleanup_refused.json", value)
    return {"schema_version": 1, "sha256": fingerprint(value)}


def record(folder: Path, process: dict, stopped: dict, *, source: str) -> dict:
    """A controlled stop is different from a fabricated successful native exit."""
    supervisor = {k: process[k] for k in ("pid", "start_ticks")}
    identities = stopped.get("process_start_ticks", {})
    cleanup = stopped.get("cleanup", {})
    if (
        identities.get(str(supervisor["pid"])) != supervisor["start_ticks"]
        or cleanup.get("complete") is not True
        or cleanup.get("remaining_pids") != []
        or cleanup.get("freeze_complete") is not True
    ):
        raise CleanupEvidenceError(
            "Native deadline lacks an exact fully reaped process tree"
        )
    started_path = folder / "process_ownership_started.json"
    started = read(started_path) if started_path.exists() else None
    if started is not None and (
        started.get("schema_version") != 2
        or started.get("supervisor") != supervisor
        or started.get("native_exec_gated") is not True
    ):
        raise CleanupEvidenceError("Native deadline start identities changed")
    value = {
        "schema_version": 1,
        "source": source,
        "supervisor": supervisor,
        "native_start": started,
        "stopped": stopped,
        "stopped_sha256": fingerprint(stopped),
        "native_exec_never_released": started is None,
    }
    if source == "native_timeout":
        saved = native_stop(folder, process)
        if saved != stopped:
            raise CleanupEvidenceError("Native timeout has no matching durable stop")
        value["native_timeout_cleanup_sha256"] = fingerprint(
            read(folder / "native_timeout_cleanup.json")
        )
    write_json(folder / "deadline_cleanup.json", value)
    return {"schema_version": 1, "sha256": fingerprint(value)}


def audit(folder: Path, generation: dict) -> None:
    marker = generation.get("host_deadline_cleanup")
    if marker is None:
        return
    value = read(folder / "deadline_cleanup.json")
    process = read(folder / "process.json")
    stopped = value["stopped"]
    if (
        marker != {"schema_version": 1, "sha256": fingerprint(value)}
        or generation.get("status") != "budget_exhausted"
        or value.get("schema_version") != 1
        or value.get("supervisor") != {k: process[k] for k in ("pid", "start_ticks")}
        or value.get("stopped_sha256") != fingerprint(stopped)
        or stopped.get("cleanup", {}).get("complete") is not True
        or stopped["cleanup"].get("remaining_pids") != []
        or stopped["cleanup"].get("freeze_complete") is not True
        or stopped.get("process_start_ticks", {}).get(str(process["pid"]))
        != process["start_ticks"]
    ):
        raise ValueError("Native deadline cleanup evidence changed")
    if value["source"] == "whole_problem_deadline":
        if (
            read(folder.parent / "budget_end.json") != stopped
            or stopped.get("exhausted") is not True
        ):
            raise ValueError("Native cleanup differs from the whole-problem deadline")
    elif value["source"] != "native_timeout":
        raise ValueError("Unknown native deadline cleanup source")
    if value.get("native_timeout_cleanup_sha256") is not None:
        saved = native_stop(folder, process)
        if (
            saved != stopped
            or fingerprint(read(folder / "native_timeout_cleanup.json"))
            != value["native_timeout_cleanup_sha256"]
        ):
            raise ValueError("Native timeout cleanup receipt changed")
    started = value["native_start"]
    path = folder / "process_ownership_started.json"
    if started is not None:
        if (
            not path.exists()
            or read(path) != started
            or value["native_exec_never_released"]
        ):
            raise ValueError("Native start receipt changed after deadline")
    elif path.exists() or value["native_exec_never_released"] is not True:
        raise ValueError("Native startup gate evidence changed")
