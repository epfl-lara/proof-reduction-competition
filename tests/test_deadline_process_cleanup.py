"""Real Linux deadline cleanup must not depend on readable process metadata."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from proof_eval.providers import processes

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux process custody")


def test_nondumpable_compiler_child_is_killed_and_reaped(tmp_path):
    ready = tmp_path / "ready.json"
    script = r"""
import ctypes, json, os, subprocess, sys, time
from pathlib import Path
leaf_code = '''import ctypes, sys, time
from pathlib import Path
assert ctypes.CDLL(None).prctl(4, 0, 0, 0, 0) == 0
Path(sys.argv[1]).write_text('ready')
time.sleep(60)
'''
leaf = subprocess.Popen([sys.executable, '-c', leaf_code, sys.argv[1] + '.leaf',
                         '_ProofEval_deadbeef.lean'], start_new_session=True)
while not Path(sys.argv[1] + '.leaf').exists():
    assert leaf.poll() is None
    time.sleep(0.01)
Path(sys.argv[1]).write_text(json.dumps({'leaf': leaf.pid}))
time.sleep(60)
"""
    peer = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    child = subprocess.Popen([sys.executable, "-c", script, str(ready)])
    leaf = None
    try:
        until = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < until:
            assert child.poll() is None
            time.sleep(0.01)
        leaf = json.loads(ready.read_text())["leaf"]
        leaf_ticks = processes._table_identity(leaf)
        stopped = processes.stop_tree(child.pid)
        child.wait(timeout=5)
        assert stopped["cleanup"]["complete"], stopped
        assert stopped["cleanup"]["remaining_pids"] == []
        assert any(e["pid"] == leaf for e in stopped["metadata_errors"])
        assert not Path(
            f"/proc/{leaf}"
        ).exists(), "A stopped child or zombie is not cleanup"
        assert peer.poll() is None
    finally:
        # Only fixture identities are touched, including the intentionally broken
        # baseline's stopped non-dumpable child. No waitpid(-1) or process group kill.
        if leaf is not None and processes._table_identity(leaf) == leaf_ticks:
            os.kill(leaf, signal.SIGKILL)
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)
        if leaf is not None:
            until = time.monotonic() + 5
            while Path(f"/proc/{leaf}").exists() and time.monotonic() < until:
                try:
                    if os.waitpid(leaf, os.WNOHANG)[0]:
                        break
                except ChildProcessError:
                    pass
                time.sleep(0.01)
        peer.terminate()
        peer.wait(timeout=5)


@pytest.mark.parametrize("error", [PermissionError, FileNotFoundError])
def test_unreadable_command_does_not_skip_the_direct_root(tmp_path, monkeypatch, error):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    command = Path(f"/proc/{child.pid}/cmdline")
    original = Path.read_bytes

    def read(path):
        if path == command:
            raise error(13, "Fixture process metadata is inaccessible")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    try:
        stopped = processes.stop_tree(child.pid)
        assert child.wait(timeout=5) == -signal.SIGKILL
        assert stopped["cleanup"]["complete"], stopped
        assert stopped["metadata_errors"] == [
            {"pid": child.pid, "type": error.__name__, "errno": 13}
        ]
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)


def test_ten_concurrent_deadlines_reap_only_their_own_children(tmp_path):
    script = r"""
import ctypes, json, os, subprocess, sys, time
from pathlib import Path
from proof_eval.providers.processes import enable_subreaper
enable_subreaper()
leaf_code = '''import ctypes, sys, time
from pathlib import Path
assert ctypes.CDLL(None).prctl(4, 0, 0, 0, 0) == 0
Path(sys.argv[1]).write_text('ready')
time.sleep(60)
'''
leaves = [subprocess.Popen([sys.executable, '-c', leaf_code,
                           sys.argv[1] + '.' + str(i), '_ProofEval_deadbeef.lean'],
                          start_new_session=True) for i in range(2)]
while not all(Path(sys.argv[1] + '.' + str(i)).exists() for i in range(2)):
    assert all(p.poll() is None for p in leaves)
    time.sleep(0.01)
Path(sys.argv[1]).write_text(json.dumps([p.pid for p in leaves]))
time.sleep(60)
"""
    peer = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    children = []
    leaves = {}
    try:
        for index in range(10):
            ready = tmp_path / f"ready-{index}.json"
            child = subprocess.Popen([sys.executable, "-c", script, str(ready)])
            children.append((child, ready))
        until = time.monotonic() + 10
        while not all(p.exists() for _, p in children) and time.monotonic() < until:
            assert all(c.poll() is None for c, _ in children)
            time.sleep(0.01)
        for _, ready in children:
            for pid in json.loads(ready.read_text()):
                leaves[pid] = processes._table_identity(pid)
        with ThreadPoolExecutor(max_workers=10) as pool:
            receipts = list(pool.map(processes.stop_tree, [c.pid for c, _ in children]))
        for (child, _), receipt in zip(children, receipts):
            assert child.wait(timeout=5) == -signal.SIGKILL
            assert receipt["cleanup"]["complete"], receipt
            assert receipt["cleanup"]["remaining_pids"] == []
            assert len(receipt["metadata_errors"]) == 2
            assert peer.pid not in receipt["terminated_pids"]
        owned = [p for r in receipts for p in r["terminated_pids"]]
        assert len(owned) == len(set(owned)) == 30
        assert all(not Path(f"/proc/{pid}").exists() for pid in leaves)
        assert peer.poll() is None
    finally:
        for pid, ticks in leaves.items():
            if processes._table_identity(pid) == ticks:
                os.kill(pid, signal.SIGKILL)
        for child, _ in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
        until = time.monotonic() + 5
        for pid, ticks in leaves.items():
            while processes._table_identity(pid) == ticks and time.monotonic() < until:
                try:
                    if os.waitpid(pid, os.WNOHANG)[0]:
                        break
                except ChildProcessError:
                    pass
                time.sleep(0.01)
        peer.terminate()
        peer.wait(timeout=5)
