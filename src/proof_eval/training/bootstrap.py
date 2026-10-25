"""Restore verified harness imports after the image activation sanitizes paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def configure_imports(release: Path) -> Path:
    source = release / "src"
    if not (source / "proof_eval/__init__.py").is_file():
        raise FileNotFoundError("The verified Arena harness source package is absent")
    paths = [str(source)]
    for path in reversed(paths):
        if path not in sys.path:
            sys.path.insert(0, path)
    # In-process preparation and spawned training workers need the same sources.
    os.environ["PYTHONPATH"] = os.pathsep.join(paths)
    return source
