"""Real local processes prove cleanup ownership survives coordinator interruption."""

from __future__ import annotations

import fcntl
import os
import signal
import subprocess
import sys
import time

import pytest

from proof_eval.evidence.io import read
from proof_eval.providers.processes import process_identity

COORDINATOR = r"""
import fcntl, sys, threading
from pathlib import Path
from proof_eval.optimization.supervision import interruption_signals, run_owned_worker
folder, worker, mode = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
cancellation = threading.Event()
with (folder / "owner.lock").open("a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with interruption_signals():
        run_owned_worker([sys.executable, worker, str(folder), mode],
                         folder=folder, lock_fd=lock.fileno(), cancellation=cancellation)
"""

WORKER = r'''
import json, os, signal, subprocess, sys, time
from pathlib import Path
from proof_eval.providers.processes import enable_subreaper
enable_subreaper()
folder, mode = Path(sys.argv[1]), sys.argv[2]
intermediary = """
import json, os, subprocess, sys
from pathlib import Path
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3600)'], start_new_session=True)
Path(sys.argv[1]).write_text(json.dumps({'pid':child.pid}))
os._exit(0)
"""
subprocess.Popen([sys.executable, '-c', intermediary, str(folder / 'leaf.json')], start_new_session=True).wait()
(folder / 'ready.json').write_text(json.dumps({'pid':os.getpid()}))
if mode == 'success':
    sys.exit(0)
if mode == 'crash':
    os.kill(os.getpid(), signal.SIGKILL)
time.sleep(3600)
'''


def wait_for(predicate, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.03)
    raise AssertionError("Owned worker did not reach the expected terminal state")


@pytest.fixture
def processes(tmp_path):
    worker = tmp_path / "worker.py"
    worker.write_text(WORKER)
    outsider = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True
    )
    controllers, folders = [], []

    def launch(mode):
        folder = tmp_path / ("cell_" + str(len(folders)))
        folder.mkdir()
        controller = subprocess.Popen(
            [sys.executable, "-c", COORDINATOR, str(folder), str(worker), mode],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        folders.append(folder)
        controllers.append(controller)
        wait_for(lambda: (folder / "ready.json").exists())
        return controller, folder, outsider

    yield launch
    for controller, folder in zip(controllers, folders):
        started = folder / "supervision_started.json"
        if started.exists():
            identity = read(started)["supervisor"]
            if process_identity(identity["pid"]) == identity:
                os.kill(identity["pid"], signal.SIGCONT)
        if controller.poll() is None:
            controller.kill()
        controller.wait(timeout=10)
        wait_for(lambda: (folder / "worker_termination.json").exists())
    outsider.terminate()
    outsider.wait(timeout=10)


def assert_drained(folder, outsider):
    terminal = read(folder / "worker_termination.json")
    worker = read(folder / "ready.json")["pid"]
    leaf = read(folder / "leaf.json")["pid"]
    wait_for(
        lambda: process_identity(worker) is None and process_identity(leaf) is None
    )
    assert outsider.poll() is None
    assert outsider.pid not in terminal["terminated_pids"]
    with (folder / "owner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return terminal


@pytest.mark.parametrize(
    "mode,reason", [("success", "completed"), ("crash", "worker_failed")]
)
def test_worker_exit_drains_detached_orphans_and_preserves_unrelated_processes(
    processes, mode, reason
):
    controller, folder, outsider = processes(mode)
    controller.wait(timeout=10)
    assert controller.returncode == (0 if mode == "success" else 1)
    terminal = assert_drained(folder, outsider)
    assert terminal["reason"] == reason
    assert read(folder / "leaf.json")["pid"] in terminal["terminated_pids"]


def test_coordinator_sigkill_closes_liveness_pipe_and_lock_survives_until_drain(
    processes,
):
    controller, folder, outsider = processes("blocking")
    supervisor = read(folder / "supervision_started.json")["supervisor"]
    os.kill(supervisor["pid"], signal.SIGSTOP)
    controller.kill()
    controller.wait(timeout=5)
    with (folder / "owner.lock").open("a") as lock:
        with pytest.raises(BlockingIOError):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    os.kill(supervisor["pid"], signal.SIGCONT)
    wait_for(lambda: (folder / "worker_termination.json").exists())
    assert assert_drained(folder, outsider)["reason"] == "coordinator_lost"


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_coordinator_signal_cancels_and_awaits_its_worker_tree(processes, signum):
    controller, folder, outsider = processes("blocking")
    os.kill(controller.pid, signum)
    controller.wait(timeout=10)
    assert controller.returncode != 0
    assert assert_drained(folder, outsider)["reason"] == "cancelled"
