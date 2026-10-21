import fcntl
import os
import subprocess
import sys
import time

import pytest

from proof_eval.providers import agy
from proof_eval.providers.isolation import abi_version, launch_command
from proof_eval.providers.processes import stop_tree


@pytest.fixture
def landlock():
    try:
        version = abi_version()
    except (OSError, RuntimeError) as exc:
        pytest.skip(str(exc))
    if version < 3:
        pytest.skip("Landlock ABI >= 3 required")


def test_tools_can_read_sources_but_cannot_write_truncate_remove_or_escape(
    tmp_path, landlock
):
    project = tmp_path / "source"
    workspace = tmp_path / "attempt"
    project.mkdir()
    workspace.mkdir()
    (project / "Original.lean").write_text("original")
    (workspace / "source_link").symlink_to(project, target_is_directory=True)
    script = """
from pathlib import Path
import os
source, work = Path(__import__('sys').argv[1]), Path(__import__('sys').argv[2])
assert (source / 'Original.lean').read_text() == 'original'
(work / 'candidate.lean').write_text('candidate')
for operation in [lambda: (source / 'candidate.lean').write_text('bad'),
                  lambda: (source / 'Original.lean').write_text('bad'),
                  lambda: os.truncate(source / 'Original.lean', 0),
                  lambda: (source / 'Original.lean').unlink(),
                  lambda: (work / 'source_link/candidate.lean').write_text('bad')]:
    try:
        operation()
    except PermissionError:
        pass
    else:
        raise AssertionError('Source write was allowed')
"""
    cmd = launch_command(
        [sys.executable, "-c", script, str(project), str(workspace)],
        workspace,
        [project],
    )
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert (project / "Original.lean").read_text() == "original"
    assert not (project / "candidate.lean").exists()
    assert (workspace / "candidate.lean").read_text() == "candidate"


def test_misconfigured_writable_ancestor_is_rejected(tmp_path, landlock):
    project = tmp_path / "source"
    project.mkdir()
    cmd = launch_command(
        [sys.executable, "-c", 'raise AssertionError("must not execute")'],
        tmp_path,
        [project],
    )
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    assert result.returncode != 0
    assert "overlaps a protected source tree" in result.stderr


def test_agy_can_allocate_a_pty_while_sources_and_host_evidence_stay_readonly(
    tmp_path, landlock
):
    source = tmp_path / "source"
    workspace = tmp_path / "workspace"
    source.mkdir()
    workspace.mkdir()
    protected_file = source / "Original.lean"
    protected_file.write_text("original")
    evidence = tmp_path / "generation.json"
    evidence.write_text("host evidence")
    script = """
import os, pty, sys
from pathlib import Path
master, slave = pty.openpty()
slave_name = os.ttyname(slave)
reopened = os.open(slave_name, os.O_RDWR)
os.write(master, b'command output\\n')
assert os.read(slave, 100) == b'command output\\n'
for fd in (reopened, master, slave): os.close(fd)
for filename in sys.argv[1:]:
    try: Path(filename).write_text('bad')
    except PermissionError: pass
    else: raise AssertionError('protected write was allowed')
"""
    command = launch_command(
        [sys.executable, "-c", script, str(protected_file), str(evidence)],
        workspace,
        [source],
        runtime_paths=agy.runtime_paths(),
    )
    result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert protected_file.read_text() == "original"
    assert evidence.read_text() == "host evidence"


def test_job_cannot_signal_sibling_but_can_clean_own_children(tmp_path, landlock):
    source, workspace = tmp_path / "source", tmp_path / "workspace"
    source.mkdir()
    workspace.mkdir()
    # Every target in this test is a disposable fixture. The dangerous group
    # operation runs only after verifying a different kernel PID namespace.
    sibling = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    script = """
import os, signal, subprocess, sys
from pathlib import Path
assert os.readlink('/proc/self/ns/pid') != sys.argv[2]
assert int(os.readlink('/proc/self')) == os.getpid()
assert not Path('/proc/' + sys.argv[1]).exists()
try: os.kill(int(sys.argv[1]), signal.SIGTERM)
except ProcessLookupError: pass
else: raise AssertionError('Host sibling was visible')
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
child.terminate()
assert child.wait(timeout=5) == -signal.SIGTERM
# Even kill(-1), which crosses process groups, stays inside this namespace.
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
signal.signal(signal.SIGTERM, signal.SIG_IGN)
os.kill(-1, signal.SIGTERM)
assert child.wait(timeout=5) == -signal.SIGTERM
print('contained', flush=True)
"""
    try:
        command = launch_command(
            [
                sys.executable,
                "-c",
                script,
                str(sibling.pid),
                os.readlink("/proc/self/ns/pid"),
            ],
            workspace,
            [source],
            runtime_paths=(),
        )
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        assert "contained" in result.stdout
        assert sibling.poll() is None
    finally:
        sibling.kill()
        sibling.wait(timeout=5)


def test_host_can_stop_namespace_and_detached_children(tmp_path, landlock):
    source, workspace = tmp_path / "source", tmp_path / "workspace"
    source.mkdir()
    workspace.mkdir()
    script = """
import subprocess, sys, time
from pathlib import Path
subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
Path(sys.argv[1]).write_text('ready')
time.sleep(60)
"""
    child = subprocess.Popen(
        launch_command(
            [sys.executable, "-c", script, str(workspace / "ready")],
            workspace,
            [source],
            runtime_paths=(),
        )
    )
    try:
        deadline = time.monotonic() + 10
        while not (workspace / "ready").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (workspace / "ready").exists()
        stopped = stop_tree(child.pid)
        assert len(stopped["terminated_pids"]) >= 4
        assert child.wait(timeout=5) != 0
        # Descendants may briefly be zombies pending their host reaper.
        from proof_eval.providers.processes import process_identity

        for pid in stopped["terminated_pids"]:
            deadline = time.monotonic() + 5
            while process_identity(pid) and time.monotonic() < deadline:
                time.sleep(0.02)
            assert process_identity(pid) is None
    finally:
        if child.poll() is None:
            stop_tree(child.pid)
            child.wait(timeout=5)


def test_missing_namespace_tool_fails_before_execution(tmp_path, monkeypatch):
    monkeypatch.setattr("proof_eval.providers.isolation.shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="bubblewrap is required"):
        launch_command([sys.executable, "-c", "pass"], tmp_path, [])


def test_namespace_retains_shared_admission_lock_until_exit(tmp_path, landlock):
    source, workspace = tmp_path / "source", tmp_path / "workspace"
    source.mkdir()
    workspace.mkdir()
    path = tmp_path / "capacity.lock"
    lock = path.open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    script = "from pathlib import Path; import sys,time; Path(sys.argv[1]).touch(); time.sleep(60)"
    child = subprocess.Popen(
        launch_command(
            [sys.executable, "-c", script, str(workspace / "ready")],
            workspace,
            [source],
            runtime_paths=(),
            lifetime_fd=lock.fileno(),
        ),
        pass_fds=(lock.fileno(),),
    )
    try:
        deadline = time.monotonic() + 10
        while not (workspace / "ready").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (workspace / "ready").exists()
        lock.close()
        with path.open("a") as contender:
            with pytest.raises(BlockingIOError):
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
            stop_tree(child.pid)
            child.wait(timeout=5)
            deadline = time.monotonic() + 5
            while True:
                try:
                    fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.02)
    finally:
        lock.close()
        if child.poll() is None:
            stop_tree(child.pid)
            child.wait(timeout=5)
