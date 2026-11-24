"""Linux process ownership for hard deadlines, including detached tool children."""

from __future__ import annotations

import ctypes
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path


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
    """Freeze owned work, then kill and reap its orphans without stealing siblings."""
    enable_subreaper()
    table = _table()
    owned = _descendants(pid, table)
    identities = {child: table[child][1] for child in owned}
    sources = set()
    metadata_errors = []
    freeze_complete = False
    for _ in range(16):
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
            freeze_complete = True
            break
        identities.update({child: latest[child][1] for child in fresh})
        owned.update(fresh)
    work_stopped = time.time()
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
        except OSError as error:
            # Non-dumpable tool/compiler children can deny /proc cwd access.
            # Optional temporary-file discovery must never skip their termination.
            metadata_errors.append(
                {"pid": child, "type": type(error).__name__, "errno": error.errno}
            )
        try:
            if _table_identity(child) == identities[child]:
                os.kill(child, signal.SIGKILL)
        except ProcessLookupError:
            pass
    # Reparented descendants now belong to this trusted subreaper. Wait only on
    # the exact frozen identities, never waitpid(-1) in a shared batch process.
    # The caller retains ownership of the direct root's Popen.wait().
    reaped = []
    until = time.monotonic() + 5
    remaining = owned - {pid}
    while remaining:
        for child in list(remaining):
            if _table_identity(child) != identities[child]:
                remaining.remove(child)
                continue
            try:
                finished, status = os.waitpid(child, os.WNOHANG)
            except ChildProcessError:
                finished = 0  # Its frozen parent may still be exiting.
            if finished:
                reaped.append({"pid": child, "wait_status": status})
                remaining.remove(child)
        if not remaining or time.monotonic() >= until:
            break
        time.sleep(0.01)
    return {
        "terminated_pids": sorted(owned),
        "temporary_sources": sorted(sources),
        "metadata_errors": metadata_errors,
        "process_start_ticks": {str(p): t for p, t in identities.items()},
        "work_stopped_epoch": work_stopped,
        "cleanup": {
            "complete": freeze_complete and not remaining,
            "freeze_complete": freeze_complete,
            "reaped": reaped,
            "remaining_pids": sorted(remaining),
            "root_wait_owned_by_caller": pid,
        },
    }


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


def owned_command(command: list[str], receipt: Path, pass_fds=()) -> list[str]:
    """Place one native client in a dedicated, host-owned subreaper boundary."""
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        str(receipt),
        json.dumps(list(pass_fds)),
        *command,
    ]


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


def owned_identity(pid: int) -> dict:
    """Pin a Linux PID to its non-reusable process start time."""
    return {"pid": pid, "start_ticks": _table_identity(pid)}


def _reap_native_descendants(timeout: float | None = None) -> dict:
    """Drain this dedicated supervisor, never a theorem worker or its siblings."""
    owner = os.getpid()
    identities: dict[int, str] = {}
    reaped = []
    deadline = time.monotonic() + timeout if timeout is not None else None
    while True:
        table = _table()
        found = _descendants(owner, table) - {owner}
        for pid in found:
            identities.setdefault(pid, table[pid][1])
            if _table_identity(pid) == identities[pid]:
                try:
                    os.kill(pid, signal.SIGSTOP)
                except ProcessLookupError:
                    pass
        # A frozen descendant cannot fork. Include children created while the
        # previous snapshot was being frozen before killing any ancestor.
        latest = _table()
        fresh = (_descendants(owner, latest) - {owner}) - found
        if fresh and (deadline is None or time.monotonic() < deadline):
            continue
        for pid in found:
            if _table_identity(pid) == identities[pid]:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break
            if not pid:
                break
            reaped.append({"pid": pid, "wait_status": status})
        remaining = _descendants(owner, _table()) - {owner}
        if not remaining or (deadline is not None and time.monotonic() >= deadline):
            return {
                "complete": not remaining,
                "terminated_pids": sorted(identities),
                "process_start_ticks": {str(p): t for p, t in identities.items()},
                "reaped": reaped,
                "remaining_pids": sorted(remaining),
            }
        time.sleep(0.01)


def _supervise(receipt: Path, pass_fds: tuple[int, ...], command: list[str]) -> int:
    """A native exit is observed and its orphans reaped before releasing a slot."""
    enable_subreaper()
    supervisor = owned_identity(os.getpid())
    # A signal to the whole native process group must not kill the owner before
    # it records the exit and reaps detached tools. Hard theorem deadlines use
    # stop_tree/SIGKILL and remain authoritative. The native child retains its
    # normal signal behavior; only this single-threaded owner blocks signals.
    watched = {signal.SIGTERM, signal.SIGINT, signal.SIGHUP}
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, watched)
    gate_read, gate_write = os.pipe()
    try:
        child = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--native-child",
                str(gate_read),
                *command,
            ],
            pass_fds=(*pass_fds, gate_read),
            preexec_fn=lambda: signal.pthread_sigmask(
                signal.SIG_SETMASK, previous_mask
            ),
        )
        os.close(gate_read)
        gate_read = -1
        native = owned_identity(child.pid)
        startup = {
            "schema_version": 2,
            "supervisor": supervisor,
            "native": native,
            "native_exec_gated": True,
            "at_epoch": time.time(),
        }
        _write_receipt(receipt.with_name("process_ownership_started.json"), startup)
        # No native model or tool command may run before both identities are
        # durable. Closing an unreleased pipe aborts the child without exec.
        os.write(gate_write, b"1")
    except BaseException:
        if "child" in locals():
            child.kill()
            child.wait()
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        raise
    finally:
        if gate_read >= 0:
            os.close(gate_read)
        os.close(gate_write)
    received = []
    signal_deadline = None
    while True:
        notice = signal.sigtimedwait(watched, 0.05 if child.poll() is None else 0)
        if notice is not None:
            sender = owned_identity(notice.si_pid)
            try:
                sender["comm"] = (
                    (Path("/proc") / str(notice.si_pid) / "comm").read_text().strip()
                )
            except OSError:
                sender["comm"] = None
            received.append(
                {
                    "signal": notice.si_signo,
                    "sender": sender,
                    "sender_uid": notice.si_uid,
                    "code": notice.si_code,
                    "at_epoch": time.time(),
                }
            )
            signal_path = receipt.with_name("process_signals.json")
            temporary = signal_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(received, indent=2) + "\n")
            os.replace(temporary, signal_path)
            # Preserve operator cancellation, including a signal sent only to
            # this owner. Bound shutdown if the native CLI ignores SIGTERM.
            if child.poll() is None:
                child.send_signal(notice.si_signo)
            if signal_deadline is None:
                signal_deadline = time.monotonic() + 2.0
        if child.poll() is not None:
            if notice is None:
                break
            continue  # Drain pending owner signals even when the native exited first.
        if signal_deadline is not None and time.monotonic() >= signal_deadline:
            stop_tree(child.pid)
    returncode = child.wait()
    # Keep ownership and the capacity descriptor until every descendant has
    # actually gone. The theorem's existing supervisor still enforces its
    # original whole-problem deadline if an uninterruptible child cannot exit.
    cleanup = _reap_native_descendants()
    record = {
        "schema_version": 1,
        "supervisor": supervisor,
        "native": native,
        "native_returncode": returncode,
        "native_exited": True,
        "cleanup": cleanup,
        "startup": startup,
    }
    if received:
        record["supervisor_signals"] = received
    # The native Landlock boundary cannot write this host-owned receipt.
    _write_receipt(receipt, record)
    return 0 if cleanup["complete"] else 125


def _write_receipt(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


if __name__ == "__main__":
    if sys.argv[1] == "--native-child":
        gate = int(sys.argv[2])
        try:
            ready = os.read(gate, 1)
        finally:
            os.close(gate)
        if ready != b"1":
            raise SystemExit(125)
        os.execvpe(sys.argv[3], sys.argv[3:], os.environ)
    raise SystemExit(
        _supervise(Path(sys.argv[1]), tuple(json.loads(sys.argv[2])), sys.argv[3:])
    )
