"""Run a tool process with filesystem writes limited by Linux Landlock.

Reads, execution and networking remain available. The trusted Lean evaluator
runs outside this process. Require ABI 3 so truncation is also restricted.
See https://www.kernel.org/doc/html/v6.10/userspace-api/landlock.html.
"""

from __future__ import annotations

import argparse
import ctypes
import os
import platform
import sys
from pathlib import Path

WRITE_FILE = 1 << 1
TRUNCATE = 1 << 14
WRITE_ACCESS = WRITE_FILE | sum(1 << bit for bit in range(4, 15))
LIBC = ctypes.CDLL(None, use_errno=True)


class PathRule(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


def checked(result):
    if result < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return result


def abi_version():
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "aarch64"}:
        raise RuntimeError("This launcher supports Linux x86_64/aarch64 only")
    return checked(LIBC.syscall(444, 0, 0, 1))


def restrict_writes(writable, protected):
    if abi_version() < 3:
        raise RuntimeError(
            "Landlock ABI >= 3 is required; refusing unrestricted fallback"
        )
    protected = [Path(p).resolve(strict=True) for p in protected]
    allowed = sorted({Path(p).resolve(strict=True) for p in writable})
    for path in allowed:
        if any(
            path == p or path.is_relative_to(p) or p.is_relative_to(path)
            for p in protected
        ):
            raise ValueError(f"Writable path overlaps a protected source tree: {path}")
    rights = ctypes.c_uint64(WRITE_ACCESS)
    ruleset = checked(LIBC.syscall(444, ctypes.byref(rights), ctypes.sizeof(rights), 0))
    try:
        for path in allowed:
            fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = PathRule(
                    WRITE_ACCESS if path.is_dir() else WRITE_FILE | TRUNCATE, fd
                )
                checked(LIBC.syscall(445, ruleset, 1, ctypes.byref(rule), 0))
            finally:
                os.close(fd)
        checked(LIBC.prctl(38, 1, 0, 0, 0))  # PR_SET_NO_NEW_PRIVS
        checked(LIBC.syscall(446, ruleset, 0))
    finally:
        os.close(ruleset)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--writable", type=Path, action="append", required=True)
    parser.add_argument("--protected", type=Path, action="append", required=True)
    parser.add_argument("--temporary-directory", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("A command after -- is required")
    restrict_writes(args.writable, args.protected)
    if args.temporary_directory:
        os.environ["TMPDIR"] = str(args.temporary_directory.resolve())
    os.execvp(command[0], command)


def launch_command(command, folder, protected, *, runtime_paths=None):
    folder = Path(folder).resolve()
    temporary = folder / "runtime_tmp"
    temporary.mkdir(exist_ok=True)
    # Preserve the user's existing Codex authentication/runtime location.
    # Source projects are never among the writable roots.
    runtime_paths = (
        [Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))]
        if runtime_paths is None
        else runtime_paths
    )
    writable = [folder, *runtime_paths, Path.home() / ".cache", Path("/dev/null")]
    arguments = [sys.executable, str(Path(__file__).resolve())]
    for path in writable:
        if path.exists():
            arguments += ["--writable", str(path.resolve())]
    for path in protected:
        arguments += ["--protected", str(Path(path).resolve())]
    return arguments + ["--temporary-directory", str(temporary), "--", *command]


if __name__ == "__main__":
    main()
