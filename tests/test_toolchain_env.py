"""Prepared Lean selection survives container changes without implicit host state."""

import os
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "toolchain-env.sh"


def invoke(work, mode, commands, *, elan_home=None):
    env = {key: value for key, value in os.environ.items() if key != "ELAN_HOME"}
    env["PATH"] = str(commands) + os.pathsep + env["PATH"]
    if elan_home is not None:
        env["ELAN_HOME"] = str(elan_home)
    return subprocess.run(
        [
            "/bin/bash",
            "-c",
            f"set -euo pipefail; source {shlex.quote(str(HELPER))}; "
            'submission_toolchain_env "$1" "$2"; printf "%s\\n" "$ELAN_HOME"',
            "toolchain-test",
            mode,
            str(work),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


def proxies(tmp_path):
    commands = tmp_path / "provided launchers"
    commands.mkdir()
    for name in ("elan", "lake", "lean"):
        path = commands / name
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)
    return commands


def test_default_toolchains_are_shared_and_persisted(tmp_path):
    work = tmp_path / "shared work"
    work.mkdir()
    commands = proxies(tmp_path)
    prepared = invoke(work, "prepare", commands)
    assert prepared.returncode == 0, prepared.stderr
    assert (work / "elan-home.txt").read_text() == str(work / "elan") + "\n"
    resumed = invoke(work, "prepared", commands)
    assert resumed.returncode == 0, resumed.stderr
    assert resumed.stdout == prepared.stdout


def test_explicit_toolchains_cannot_silently_change_between_allocations(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    provided = tmp_path / "provided toolchains without a bin directory"
    commands = proxies(tmp_path)
    assert invoke(work, "prepare", commands, elan_home=provided).returncode == 0
    assert invoke(work, "prepared", commands).stdout.strip() == str(provided)
    other = tmp_path / "other"
    other.mkdir()
    result = invoke(work, "prepared", commands, elan_home=other)
    assert result.returncode == 2
    assert "differs from setup" in result.stderr


def test_runtime_never_installs_or_invents_a_prepared_selection(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    result = invoke(work, "prepared", proxies(tmp_path))
    assert result.returncode == 2
    assert "run setup.sh" in result.stderr
    assert not (work / "elan-home.txt").exists()
