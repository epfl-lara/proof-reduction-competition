import subprocess
import sys

import pytest

from proof_eval.providers.isolation import abi_version, launch_command


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
