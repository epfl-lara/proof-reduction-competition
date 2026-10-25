"""Importing or requesting help never starts a model or compiler."""

import os
import subprocess
import sys
from pathlib import Path


def test_training_cli_help_has_explicit_non_dispatching_modes():
    source = Path(__file__).resolve().parents[2] / "src"
    if not source.is_dir():
        source = Path(__file__).resolve().parents[3] / "src"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from proof_eval.interfaces.training import main; main(['--help'])",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        env={**os.environ, "PYTHONPATH": str(source)},
    )
    assert result.returncode == 0, result.stderr
    assert "prepare-imports" in result.stdout and "preflight" in result.stdout
