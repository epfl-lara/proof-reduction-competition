"""Regression for the real image activation clearing inherited PYTHONPATH."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from proof_eval.training.bootstrap import configure_imports


def test_imports_work_after_entrypoint_removes_pythonpath(tmp_path):
    package = tmp_path / "src/proof_eval"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("identity = 'verified-private-harness'\n")
    helper = Path(configure_imports.__code__.co_filename)
    code = (
        "import os,importlib.util;from pathlib import Path;os.environ.pop('PYTHONPATH',None);"
        f"s=importlib.util.spec_from_file_location('bootstrap',{str(helper)!r});"
        "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
        f"m.configure_imports(Path({str(tmp_path)!r}));"
        "import proof_eval;assert proof_eval.identity=='verified-private-harness'"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr


def test_missing_sealed_package_is_not_replaced_with_another_install(tmp_path):
    with pytest.raises(FileNotFoundError, match="verified Arena"):
        configure_imports(tmp_path / "missing")
