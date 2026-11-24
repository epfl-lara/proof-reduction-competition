"""Safe canary checks for the explicit read-only-mount native backend.

All mutation attempts target this check's own disposable canaries, never a real
source project, ledger or unrelated process. The host keeps and verifies them.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import resource
import signal
import subprocess
import sys
from pathlib import Path

CANARY = b"protected-source-and-ledger-canary\n"
CHECKS = (
    "allowed_write",
    "protected_write_denied",
    "protected_truncate_denied",
    "protected_unlink_denied",
    "protected_rename_denied",
    "hardlink_denied",
    "symlink_write_denied",
    "proc_root_escape_denied",
    "proc_fd_escape_denied",
    "child_signal_allowed",
    "inherited_memory_limits",
    "hard_limit_raise_denied",
    "own_executable_path_available",
    "kernel_guard_survives_without_compatibility_library",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(folder: Path, workspace: Path) -> tuple[list[str], Path]:
    root = folder / "filesystem-probe"
    root.mkdir(mode=0o700, exist_ok=False)
    for name in ("source.txt", "ledger.txt"):
        (root / name).write_bytes(CANARY)
    request = {
        "protected": str(root),
        "workspace": str(workspace),
        "checks": list(CHECKS),
    }
    (root / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    return [
        sys.executable,
        "-I",
        str(Path(__file__).resolve()),
        str(root / "request.json"),
    ], root


def verify(folder: Path, *, recorded_folder: Path | None = None) -> dict:
    root = folder / "filesystem-probe"
    raw = (folder / "signal_scope_preflight/stdout.log").read_bytes()
    report = json.loads(raw)
    if report != {"checks": {name: True for name in CHECKS}}:
        raise ValueError("Filesystem protection preflight did not pass every check")
    if any(
        (root / name).read_bytes() != CANARY for name in ("source.txt", "ledger.txt")
    ):
        raise ValueError("Filesystem preflight changed a protected host canary")
    request = json.loads((root / "request.json").read_text())
    original = folder if recorded_folder is None else recorded_folder
    if request != {
        "protected": str(original / "filesystem-probe"),
        "workspace": str(original / "workspace"),
        "checks": list(CHECKS),
    }:
        raise ValueError("Filesystem canary paths changed")
    return {
        "status": "verified",
        **report,
        "stdout_sha256": hashlib.sha256(raw).hexdigest(),
        "request_sha256": _sha(root / "request.json"),
        "source_sha256": _sha(root / "source.txt"),
        "ledger_sha256": _sha(root / "ledger.txt"),
    }


def _denied(operation) -> bool:
    try:
        operation()
    except OSError as error:
        if error.errno in (
            errno.EROFS,
            errno.EACCES,
            errno.EPERM,
            errno.EXDEV,
            errno.ENOENT,
        ):
            return True
        raise
    raise RuntimeError("A protected filesystem operation unexpectedly succeeded")


def run(request_path: Path) -> dict:
    request = json.loads(request_path.read_text())
    root, workspace = Path(request["protected"]), Path(request["workspace"])
    source = root / "source.txt"
    results = {}
    writable = workspace / "filesystem-probe-write.txt"
    writable.write_bytes(b"approved\n")
    results["allowed_write"] = writable.read_bytes() == b"approved\n"
    results["protected_write_denied"] = _denied(lambda: source.open("r+b"))
    results["protected_truncate_denied"] = _denied(
        lambda: os.truncate(root / "ledger.txt", 0)
    )
    results["protected_unlink_denied"] = _denied(source.unlink)
    results["protected_rename_denied"] = _denied(
        lambda: source.rename(workspace / "escaped.txt")
    )
    results["hardlink_denied"] = _denied(
        lambda: os.link(source, workspace / "linked.txt")
    )
    link = workspace / "filesystem-probe-link"
    link.symlink_to(source)
    results["symlink_write_denied"] = _denied(lambda: link.open("r+b"))
    results["proc_root_escape_denied"] = _denied(
        lambda: Path("/proc/1/root").resolve(strict=True)
    )
    results["proc_fd_escape_denied"] = _denied(
        lambda: Path("/proc/self/fd").resolve(strict=True)
    )
    results["own_executable_path_available"] = (
        Path(os.readlink("/proc/self/exe")).resolve() == Path(sys.executable).resolve()
    )
    plain = dict(os.environ)
    plain.pop("LD_PRELOAD", None)
    independent = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import errno,os,sys\ntry: os.truncate(sys.argv[1],0)\nexcept OSError as e: assert e.errno==errno.EROFS\nelse: raise AssertionError('write guard disappeared')\nassert not os.path.exists('/proc/self/fd')",
            str(source),
        ],
        env=plain,
        capture_output=True,
        timeout=3,
    )
    results["kernel_guard_survives_without_compatibility_library"] = (
        independent.returncode == 0
    )
    child = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(5)"])
    try:
        child.send_signal(signal.SIGTERM)
        results["child_signal_allowed"] = child.wait(timeout=3) == -signal.SIGTERM
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
    results["inherited_memory_limits"] = all(
        resource.getrlimit(kind) == (limit, limit)
        for kind, limit in (
            (resource.RLIMIT_DATA, 4 * 1024**3),
            (resource.RLIMIT_AS, 32 * 1024**3),
            (resource.RLIMIT_CORE, 0),
        )
    )
    try:
        resource.setrlimit(resource.RLIMIT_DATA, (8 * 1024**3, 8 * 1024**3))
    except (ValueError, OSError):
        results["hard_limit_raise_denied"] = True
    else:
        raise RuntimeError("Native client raised its hard memory limit")
    if results != {name: True for name in CHECKS}:
        raise RuntimeError("Native protection probe failed: " + repr(results))
    return {"checks": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    print(json.dumps(run(parser.parse_args().request)))
