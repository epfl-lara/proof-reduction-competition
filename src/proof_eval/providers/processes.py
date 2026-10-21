"""Linux process ownership for hard deadlines, including detached tool children."""

from __future__ import annotations

import ctypes
import os
import re
import signal
from pathlib import Path


def process_identity(pid: int) -> dict | None:
    """Identify a live process without confusing PID reuse or zombies for life."""
    try:
        fields = (
            (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
        )
        if fields[0] == "Z":
            return None
        return {
            "pid": pid,
            "start_ticks": fields[19],
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        }
    except (OSError, ValueError, IndexError):
        return None


def enable_subreaper() -> None:
    """Keep orphaned agent/Lean descendants attached to their theorem worker."""
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), "Cannot isolate theorem descendants")


def _table() -> dict[int, tuple[int, str]]:
    result = {}
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = path.read_text().rsplit(")", 1)[1].split()
            result[int(path.parent.name)] = (int(fields[1]), fields[19])
        except (OSError, ValueError, IndexError):
            continue
    return result


def _descendants(root: int, table: dict[int, tuple[int, str]]) -> set[int]:
    owned = {root}
    while True:
        children = {pid for pid, (parent, _) in table.items() if parent in owned}
        if children <= owned:
            return owned & table.keys()
        owned.update(children)


def stop_tree(pid: int) -> dict:
    """Freeze and kill only this worker's descendants, checking PID identities."""
    table = _table()
    owned = _descendants(pid, table)
    identities = {child: table[child][1] for child in owned}
    sources = set()
    for _ in range(3):
        for child in owned:
            try:
                if _table_identity(child) == identities[child]:
                    os.kill(child, signal.SIGSTOP)
            except ProcessLookupError:
                pass
        latest = _table()
        found = _descendants(pid, latest)
        fresh = found - owned
        if not fresh:
            break
        identities.update({child: latest[child][1] for child in fresh})
        owned.update(fresh)
    for child in owned:
        proc = Path("/proc") / str(child)
        try:
            args = (proc / "cmdline").read_bytes().split(b"\0")
            for arg in args:
                path = Path(os.fsdecode(arg))
                if re.fullmatch(r"_ProofEval_[a-f0-9]+\.lean", path.name):
                    sources.add(
                        str(
                            path
                            if path.is_absolute()
                            else (proc / "cwd").resolve() / path
                        )
                    )
            if _table_identity(child) == identities[child]:
                os.kill(child, signal.SIGKILL)
        except (ProcessLookupError, FileNotFoundError, PermissionError):
            continue
    return {"terminated_pids": sorted(owned), "temporary_sources": sorted(sources)}


def _table_identity(pid: int) -> str | None:
    try:
        return (
            (Path("/proc") / str(pid) / "stat")
            .read_text()
            .rsplit(")", 1)[1]
            .split()[19]
        )
    except (OSError, IndexError):
        return None
