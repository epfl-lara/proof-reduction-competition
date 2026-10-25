"""Original context imports and bounded compiler facades, without source edits."""

from __future__ import annotations

import fcntl
import os
import re
import sys
from pathlib import Path

from proof_eval.evidence.io import fingerprint, read
from proof_eval.verification.backend import _masked_comments


class ImportPreparationUnavailable(RuntimeError):
    """Required original imports cannot be prepared; never a model reward zero."""


def _imports(text: str) -> set[str]:
    result = {"Lean"}  # The unchanged verifier injects its Lean measurement wrapper.
    for line in _masked_comments(text).splitlines():
        line = line.strip()
        if not line or line in {"module", "prelude"}:
            continue
        match = re.match(r"(?:(?:public|meta|private)\s+)*import\s+(.+)", line)
        if not match:
            break
        result.update(value for value in match[1].split() if value != "all")
    return result


def _module_path(module: str) -> Path:
    if not module or any(part in {"", ".", ".."} for part in module.split(".")):
        raise ValueError("Unsafe Lean import target")
    if any(character in module for character in "/\\\n\r\x00:") or module.startswith(
        "-"
    ):
        raise ValueError("Unsafe Lean import target")
    return Path(*module.split(".")).with_suffix(".olean")


def _libraries(project: Path, compiler: Path) -> list[Path]:
    manifest = read(project / "lake-manifest.json")
    packages = project / manifest.get("packagesDir", ".lake/packages")
    roots = [project]
    if packages.exists():
        roots.extend(sorted(path for path in packages.iterdir() if path.is_dir()))
    for package in manifest.get("packages", []):
        if package.get("type") == "path" and package.get("dir"):
            roots.extend([project / package["dir"], packages / package["dir"]])
    libraries = [
        root / suffix
        for root in roots
        for suffix in (".lake/build/lib/lean", ".lake/build/lib")
    ]
    return [*libraries, compiler / "lib/lean"]


def _missing(modules: set[str], libraries: list[Path]) -> list[str]:
    return [
        module
        for module in sorted(modules)
        if not any((library / _module_path(module)).is_file() for library in libraries)
    ]


def _immutable(path: Path, data: bytes, mode: int = 0o600) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("Immutable build facade changed: " + str(path))
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _facade(compiler: Path, root: Path, jobs: int) -> Path:
    """Isolate build-only compiler limits without modifying a real toolchain.

    Lake has no ``-j`` option in these pinned releases. Its own task pool uses
    LEAN_NUM_THREADS. A private Lean sysroot is explicitly supported by Lake's
    LAKE_OVERRIDE_LEAN/LEAN_SYSROOT; its compiler wrapper forces one child thread
    and holds a host-wide compiler slot until exec'd Lean exits.
    """
    facade = root / "compiler-facades" / fingerprint((str(compiler), jobs))
    facade.mkdir(parents=True, exist_ok=True)
    with (facade / "facade.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _configure_facade(compiler, root, jobs, facade)


def _configure_facade(compiler: Path, root: Path, jobs: int, facade: Path) -> Path:
    support = compiler / "src/lean/lake/Lake/Config/InstallPath.lean"
    if not support.exists() or "LAKE_OVERRIDE_LEAN" not in support.read_text():
        raise ImportPreparationUnavailable(
            "Pinned Lake has no verified build-facade override"
        )
    binary = facade / "bin"
    binary.mkdir(exist_ok=True)
    for child in compiler.iterdir():
        if child.name == "bin":
            continue
        target = facade / child.name
        if not target.exists():
            target.symlink_to(child, target_is_directory=child.is_dir())
        elif not target.is_symlink() or target.resolve() != child.resolve():
            raise ValueError("Build facade contains a changed compiler path")
    for child in (compiler / "bin").iterdir():
        if child.name == "lean":
            continue
        target = binary / child.name
        if not target.exists():
            target.symlink_to(child)
        elif not target.is_symlink() or target.resolve() != child.resolve():
            raise ValueError("Build facade contains a changed compiler binary")
    wrapper = f"""#!{sys.executable}
import fcntl,os,socket,sys,time
from pathlib import Path
root=Path({str(root / "compiler-slots")!r})/socket.gethostname()
root.mkdir(parents=True,exist_ok=True)
slot=None
while slot is None:
 for index in range({jobs}):
  descriptor=os.open(root/(str(index)+'.lock'),os.O_RDWR|os.O_CREAT,0o600)
  try:
   fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:
   os.close(descriptor)
  else:
   slot=descriptor
   break
 if slot is None:time.sleep(0.1)
os.set_inheritable(slot,True)
args=[]
iterator=iter(sys.argv[1:])
for arg in iterator:
 if arg in ('-j','--threads'):
  next(iterator,None)
 elif arg.startswith('-j') or arg.startswith('--threads='):
  continue
 else:args.append(arg)
os.environ['LEAN_NUM_THREADS']='1'
real={str(compiler / "bin/lean")!r}
os.execv(real,[real,'--threads=1',*args])
""".encode()
    _immutable(binary / "lean", wrapper, 0o700)
    return facade
