"""Explicit filesystem confinement without Landlock; Linux namespaces required.

The signal broker stays outside the mount namespace, in the same PID namespace.
Procfs is deliberately hidden so its root/fd magic links cannot expose another
process's writable mount tree. No capability or new user namespace may survive.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import os
import platform
import stat
import sys
from pathlib import Path

POLICY = "readonly-mounts-hidden-proc-seccomp-v2"
NAMESPACE_POLICY = "inherited-seccomp-no-new-namespaces-v1"
BWRAP_SHA256 = "e318903862396f96de3df57264e0158682b952fd3fb53ac23d876413e7b30f71"
SHIM_SHA256 = "bd391b3fdab6feabc7704785e32814267567da9a5c1373c817ed65f9acd9332e"
SHIM_SOURCE_SHA256 = "d5708efff1f61a171e1f51458e61dee3c53617d3a2417da82a227d5c86186aa3"
ENVIRONMENT = "PROOF_EVAL_FILESYSTEM_BACKEND"
BACKENDS = ("landlock", "readonly-mounts")
LIBC = ctypes.CDLL(None, use_errno=True)


def backend() -> str:
    value = os.environ.get(ENVIRONMENT, "landlock")
    if value not in BACKENDS:
        raise ValueError("Unknown filesystem backend: " + value)
    return value


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(selected: str | None = None) -> dict:
    value = {"backend": backend() if selected is None else selected}
    if value["backend"] not in BACKENDS:
        raise ValueError("Unknown filesystem backend")
    if value["backend"] == "landlock":
        return {**value, "policy": "landlock-write-abi3-v1"}
    binary = Path(__file__).resolve().parents[3] / "bin/bwrap"
    info = binary.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_mode & 0o6022
        or not os.access(binary, os.X_OK)
    ):
        raise ValueError("Namespace guard binary must be a protected executable")
    if _digest(binary) != BWRAP_SHA256:
        raise ValueError("Namespace guard binary differs from the pinned build")
    shim = binary.with_name("proc-exe.so")
    source = Path(__file__).with_name("proc_exe.c")
    info = shim.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_mode & 0o6022
        or _digest(shim) != SHIM_SHA256
        or _digest(source) != SHIM_SOURCE_SHA256
    ):
        raise ValueError("Executable-path compatibility library changed")
    return {
        **value,
        "policy": POLICY,
        "binary": str(binary),
        "binary_sha256": BWRAP_SHA256,
        "launcher": str(Path(__file__).resolve()),
        "launcher_sha256": _digest(Path(__file__)),
        "probe_sha256": _digest(Path(__file__).with_name("filesystem_probe.py")),
        "compatibility_library": str(shim),
        "compatibility_library_sha256": SHIM_SHA256,
        "compatibility_source_sha256": SHIM_SOURCE_SHA256,
        "procfs": "hidden",
        "new_user_namespaces": "disabled",
        "namespace_creation_guard": NAMESPACE_POLICY,
        "process_boundary": "existing_descendant_signal_broker",
    }


def validate_identity(value: dict) -> None:
    if value != identity():
        raise ValueError("Filesystem backend or trusted launcher changed")


def audit(
    folder: Path, request: dict, command_record: dict, recorded_folder: Path
) -> None:
    """Require saved guarded argv and canary evidence for the new backend only."""
    saved = request.get("cli", {}).get("filesystem_guard")
    if saved is None:  # Historical requests keep their original contracts.
        return
    if command_record.get("filesystem_guard") != saved:
        raise ValueError("Filesystem command identity changed")
    argv = command_record["isolated_argv"]
    if saved.get("backend") == "landlock":
        if "--filesystem-backend" in argv:
            raise ValueError("Landlock request changed its filesystem backend")
        return
    if (
        saved.get("backend") != "readonly-mounts"
        or saved.get("policy") != POLICY
        or saved.get("binary_sha256") != BWRAP_SHA256
        or saved.get("compatibility_library_sha256") != SHIM_SHA256
        or saved.get("compatibility_source_sha256") != SHIM_SOURCE_SHA256
        or argv.count("--filesystem-backend") != 1
        or argv[argv.index("--filesystem-backend") + 1] != "readonly-mounts"
    ):
        raise ValueError("Missing explicit read-only mount boundary")
    from . import filesystem_probe

    if command_record.get("filesystem_preflight") != filesystem_probe.verify(
        folder, recorded_folder=recorded_folder
    ):
        raise ValueError("Filesystem preflight evidence changed")


def checked_paths(
    writable: list[Path], protected: list[Path]
) -> tuple[list[Path], list[Path]]:
    denied = [Path(p).resolve(strict=True) for p in protected]
    allowed = sorted({Path(p).resolve(strict=True) for p in writable})
    for path in allowed:
        if str(path) == "/" or any(
            path == p or path.is_relative_to(p) or p.is_relative_to(path)
            for p in denied
        ):
            raise ValueError("Writable path overlaps protected data: " + str(path))
        if (
            path == Path("/proc")
            or path.is_relative_to("/proc")
            or Path("/proc").is_relative_to(path)
        ):
            raise ValueError("Procfs cannot be exposed through a writable bind")
    return allowed, denied


def command(
    argv: list[str], writable: list[Path], protected: list[Path], temporary: Path
) -> list[str]:
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("This namespace guard build requires Linux x86-64")
    value = identity("readonly-mounts")
    # A caller cannot make this launcher or its dependency model-writable.
    bundle = Path(__file__).resolve().parents[3]
    allowed, denied = checked_paths(
        writable,
        [
            *protected,
            bundle,
            Path(value["binary"]),
            Path(value["launcher"]),
            Path(value["compatibility_library"]),
        ],
    )
    args = [
        value["binary"],
        "--unshare-user",
        "--die-with-parent",
        "--new-session",
        "--ro-bind",
        "/",
        "/",
        "--tmpfs",
        "/proc",
        "--remount-ro",
        "/proc",
        "--dev",
        "/dev",
        "--remount-ro",
        "/dev",
        "--cap-drop",
        "ALL",
    ]
    for path in allowed:
        args += ["--bind", str(path), str(path)]
    args += ["--", sys.executable, "-I", str(Path(__file__).resolve()), "--enter"]
    for path in allowed:
        args += ["--writable", str(path)]
    for path in denied:
        args += ["--protected", str(path)]
    return args + ["--temporary-directory", str(temporary), "--", *argv]


class _CapHeader(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]


class _CapData(ctypes.Structure):
    _fields_ = [
        ("effective", ctypes.c_uint32),
        ("permitted", ctypes.c_uint32),
        ("inheritable", ctypes.c_uint32),
    ]


def deny_namespace_creation() -> None:
    """Restrict descendants without writing the container's read-only proc sysctls.

    Bubblewrap has already created the trusted mount/user view. Install this
    irreversible filter before any client or tool executes. Normal fork/threads
    remain usable; clone3 returns ENOSYS so libc can use the checked clone ABI.
    """
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("Namespace syscall guard requires Linux x86-64")

    class Instruction(ctypes.Structure):
        _fields_ = [
            ("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
            ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint),
        ]

    class Program(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ushort),
            ("filter", ctypes.POINTER(Instruction)),
        ]

    deny = 0x00050000 | errno.EPERM
    unavailable = 0x00050000 | errno.ENOSYS
    instructions = [
        (0x20, 0, 0, 4),              # seccomp_data.arch
        (0x15, 1, 0, 0xC000003E),     # AUDIT_ARCH_X86_64
        (0x06, 0, 0, 0x80000000),     # kill a foreign syscall ABI
        (0x20, 0, 0, 0),              # seccomp_data.nr
        (0x45, 0, 1, 0x40000000),     # x32 must not bypass syscall matching
        (0x06, 0, 0, unavailable),
        (0x15, 0, 1, 272),            # unshare
        (0x06, 0, 0, deny),
        (0x15, 0, 1, 308),            # setns
        (0x06, 0, 0, deny),
        (0x15, 0, 1, 435),            # clone3: opaque user-space flags
        (0x06, 0, 0, unavailable),
        (0x15, 0, 3, 56),             # clone: inspect its first argument
        (0x20, 0, 0, 16),             # low 32 bits of clone flags
        (0x45, 0, 1, 0x7E020080),     # all CLONE_NEW* namespace flags
        (0x06, 0, 0, deny),
        (0x06, 0, 0, 0x7FFF0000),     # allow ordinary process/thread work
    ]
    filters = (Instruction * len(instructions))(
        *(Instruction(*row) for row in instructions)
    )
    program = Program(len(filters), filters)
    if LIBC.prctl(38, 1, 0, 0, 0) != 0 or LIBC.prctl(
        22, 2, ctypes.byref(program), 0, 0
    ) != 0:
        raise OSError(ctypes.get_errno(), "Cannot restrict namespace creation")


def validate_entry(writable: list[Path], protected: list[Path]) -> dict:
    allowed, denied = checked_paths(writable, protected)
    deny_namespace_creation()
    if LIBC.prctl(39, 0, 0, 0, 0) != 1:  # PR_GET_NO_NEW_PRIVS
        raise RuntimeError("Namespace guard requires no_new_privs")
    header, data = _CapHeader(0x20080522, 0), (_CapData * 2)()
    if LIBC.capget(ctypes.byref(header), ctypes.byref(data)) != 0:
        raise OSError(ctypes.get_errno(), "capget")
    if any(v.effective or v.permitted or v.inheritable for v in data):
        raise RuntimeError("Namespace guard retained capabilities")
    for flag in (0x10000000, 0x00020000):  # CLONE_NEWUSER, CLONE_NEWNS
        if LIBC.unshare(flag) == 0:
            raise RuntimeError("Namespace guard permitted a new user/mount namespace")
        if ctypes.get_errno() != errno.EPERM:
            raise OSError(ctypes.get_errno(), "Unexpected namespace denial")
    if not os.statvfs("/").f_flag & os.ST_RDONLY:
        raise RuntimeError("Namespace root filesystem is writable")
    if os.listdir("/proc") or not os.statvfs("/proc").f_flag & os.ST_RDONLY:
        raise RuntimeError("Host procfs must be hidden and read-only")
    if not os.statvfs("/dev").f_flag & os.ST_RDONLY:
        raise RuntimeError("Private device directory must be read-only")
    if any(not os.statvfs(p).f_flag & os.ST_RDONLY for p in denied):
        raise RuntimeError("Protected source has a writable mount")
    if any(os.statvfs(p).f_flag & os.ST_RDONLY for p in allowed):
        raise RuntimeError("An approved writable path is read-only")
    return {
        "policy": POLICY,
        "root_readonly": True,
        "proc_hidden_readonly": True,
        "capabilities_empty": True,
        "no_new_privs": True,
        "new_user_and_mount_namespaces_denied": True,
        "namespace_creation_guard": NAMESPACE_POLICY,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enter", action="store_true", required=True)
    parser.add_argument("--writable", type=Path, action="append", required=True)
    parser.add_argument("--protected", type=Path, action="append", default=[])
    parser.add_argument("--temporary-directory", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not argv:
        parser.error("A guarded command is required")
    validate_entry(args.writable, args.protected)
    # Compatibility for dynamically linked clients only; the kernel write guard
    # is already active and does not depend on this library or environment.
    os.environ["LD_PRELOAD"] = identity("readonly-mounts")["compatibility_library"]
    os.environ["TMPDIR"] = str(args.temporary_directory.resolve(strict=True))
    os.execvp(argv[0], argv)


if __name__ == "__main__":
    main()
