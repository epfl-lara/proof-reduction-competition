"""Own one cleanup process tree even when its batch coordinator disappears.

The coordinator alone holds a pipe's write end. A separate subreaper owns the
worker and its detached Lean descendants, holds the output lock, and drains only
its own children on cancellation, coordinator death, or worker termination.
"""

from __future__ import annotations

import fcntl
import os
import select
import signal
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

from proof_eval.evidence.io import fingerprint, read, write_json
from proof_eval.providers.processes import enable_subreaper, process_identity, stop_tree


@contextmanager
def interruption_signals() -> Iterator[None]:
    """Give a main-thread coordinator time to cancel its owned workers on SIGTERM."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    previous = signal.getsignal(signal.SIGTERM)

    def interrupt(signum, frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupt)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def run_owned_worker(
    command: Sequence[str],
    *,
    folder: Path,
    lock_fd: int,
    cancellation: threading.Event,
) -> None:
    """Wait for an isolated supervisor; closing its pipe cancels only this worker."""
    if cancellation.is_set():
        raise RuntimeError("Cleanup cancelled before worker admission")
    request = folder / "worker_launch.json"
    if request.exists():
        raise RuntimeError("Cleanup supervisor already started; not replayed")
    write_json(
        request,
        {
            "version": 1,
            "command": list(command),
            "command_sha256": fingerprint(list(command)),
            "owner": process_identity(os.getpid()),
            "started_epoch": time.time(),
        },
    )
    reader, writer = os.pipe()
    supervisor = None
    try:
        with (folder / "worker.log").open("ab") as log:
            supervisor = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "proof_eval.optimization.supervision",
                    str(request),
                    str(reader),
                    str(lock_fd),
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                pass_fds=(reader, lock_fd),
            )
        os.close(reader)
        reader = -1
        while supervisor.poll() is None:
            if cancellation.wait(0.1):
                _cancel(writer)
                os.close(writer)
                writer = -1
                supervisor.wait()
                raise RuntimeError("Cleanup cancelled; owned worker tree stopped")
        if supervisor.returncode:
            raise RuntimeError(
                f"Cleanup worker supervisor exited {supervisor.returncode}; "
                "inspect worker_termination.json and worker.log"
            )
        terminal = read(folder / "worker_termination.json")
        if terminal["reason"] != "completed" or terminal["worker_returncode"] != 0:
            raise RuntimeError("Cleanup worker did not complete successfully")
    finally:
        if reader >= 0:
            os.close(reader)
        if writer >= 0:
            if supervisor is not None and supervisor.poll() is None:
                _cancel(writer)
            os.close(writer)
        if supervisor is not None and supervisor.poll() is None:
            # Never kill the supervisor before it has captured and stopped its
            # worker tree. Its retained lock prevents competing cleanup writers.
            supervisor.wait()


def _cancel(writer: int) -> None:
    try:
        os.write(writer, b"cancel\n")
    except BrokenPipeError:
        pass


def _direct_children() -> list[int]:
    pid = os.getpid()
    path = Path(f"/proc/{pid}/task/{pid}/children")
    return [int(value) for value in path.read_text().split()]


def _drain_owned_children() -> dict:
    """Stop adopted descendants; never target the supervisor itself or siblings."""
    terminated, sources = set(), set()
    while children := _direct_children():
        for pid in children:
            # This dedicated supervisor is the sole reaper. An exited child stays
            # a zombie until waitpid below, so its PID cannot be reused here.
            identity = process_identity(pid)
            if identity is not None:
                stopped = stop_tree(pid)
                terminated.update(stopped["terminated_pids"])
                sources.update(stopped["temporary_sources"])
        for pid in children:
            try:
                os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                pass
        if _direct_children():
            time.sleep(0.02)
    return {
        "terminated_pids": sorted(terminated),
        "temporary_sources": sorted(sources),
    }


def _supervise(request_path: Path, reader: int, lock_fd: int) -> int:
    request, folder = read(request_path), request_path.parent
    if (
        request["version"] != 1
        or fingerprint(request["command"]) != request["command_sha256"]
    ):
        raise ValueError("Cleanup worker launch identity changed")
    # The inherited descriptor refers to the coordinator's already-held flock;
    # its lifetime extends through draining all descendants after parent death.
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    enable_subreaper()
    stop_signal = []
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda number, frame: stop_signal.append(number))
    worker = None
    reason, returncode = "supervisor_error", None
    terminated, sources = set(), set()
    started = time.time()
    try:
        ready, _, _ = select.select([reader], [], [], 0)
        if ready:
            reason = "cancelled" if os.read(reader, 4096) else "coordinator_lost"
            return 1
        worker = subprocess.Popen(
            request["command"], start_new_session=True, pass_fds=(lock_fd,)
        )
        write_json(
            folder / "supervision_started.json",
            {
                "version": 1,
                "owner": request["owner"],
                "supervisor": process_identity(os.getpid()),
                "worker": process_identity(worker.pid),
                "command_sha256": request["command_sha256"],
                "started_epoch": started,
            },
        )
        while True:
            if stop_signal:
                reason = "supervisor_signal"
                break
            ready, _, _ = select.select([reader], [], [], 0.1)
            if ready:
                reason = "cancelled" if os.read(reader, 4096) else "coordinator_lost"
                break
            returncode = worker.poll()
            if returncode is not None:
                reason = "completed" if returncode == 0 else "worker_failed"
                break
        return 0 if reason == "completed" else 1
    finally:
        if worker is not None:
            if worker.poll() is None:
                # Popen owns this unreaped child, so its PID remains reserved.
                stopped = stop_tree(worker.pid)
                terminated.update(stopped["terminated_pids"])
                sources.update(stopped["temporary_sources"])
            returncode = worker.wait()
        stopped = _drain_owned_children()
        terminated.update(stopped["terminated_pids"])
        sources.update(stopped["temporary_sources"])
        write_json(
            folder / "worker_termination.json",
            {
                "version": 1,
                "reason": reason,
                "worker_returncode": returncode,
                "owner": request["owner"],
                "supervisor": process_identity(os.getpid()),
                "command_sha256": request["command_sha256"],
                "started_epoch": started,
                "finished_epoch": time.time(),
                "terminated_pids": sorted(terminated),
                "temporary_sources": sorted(sources),
            },
        )
        os.close(reader)
        os.close(lock_fd)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(
            "Internal cleanup supervisor needs request, liveness pipe and lock"
        )
    raise SystemExit(_supervise(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])))
