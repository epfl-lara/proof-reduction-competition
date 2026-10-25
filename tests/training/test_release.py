"""A deployment is a pinned package snapshot, with no hidden image installs."""

import os
import subprocess
import sys

import pytest

from proof_eval.training.release import BOOTSTRAP


def test_frozen_entrypoint_works_when_pythonpath_was_cleared(tmp_path):
    package = tmp_path / "src/proof_eval/interfaces"
    package.mkdir(parents=True)
    (package.parent / "__init__.py").write_text("")
    (package / "__init__.py").write_text("")
    (package / "training.py").write_text(
        "def main():\n print('frozen-package-loaded'); return 0\n"
    )
    entry = tmp_path / "bootstrap.py"
    entry.write_text(BOOTSTRAP)
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-I", str(entry)],
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "frozen-package-loaded"


def test_release_config_rejects_unfrozen_plan_paths(tmp_path):
    from proof_eval.training.config import TrainingRelease

    with pytest.raises(ValueError, match="frozen release"):
        TrainingRelease(tmp_path, tmp_path / "other.json").plan()
