"""Read-only Landlock ABI admission before native-client model startup.

This query does not replace the native file, signal and memory guard preflights.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import uuid
from pathlib import Path

from proof_eval.providers import (
    filesystem_probe,
    native_resources,
    readonly_mounts,
    signal_scope,
)
from proof_eval.providers.isolation import abi_version, launch_command

MINIMUM_LANDLOCK_ABI = 3
REMEDY = (
    "Use a Linux host exposing Landlock ABI >= 3: mainline Linux >= 6.2 or an "
    "equivalent backport, with CONFIG_SECURITY_LANDLOCK=y and landlock enabled "
    "in the LSM list. For example, an Ubuntu 24.04 host with its 6.8 kernel and "
    "Landlock enabled. The container policy must permit Landlock syscalls. "
    "A container image cannot supply missing host-kernel support; this "
    "submission has no option that disables its native protections."
)


def require_landlock() -> dict:
    """Query the actual running kernel; reject an absent or older ABI."""
    host = f"{platform.system()} {platform.release()} ({platform.machine()})"
    try:
        observed = abi_version()
    except (OSError, RuntimeError) as error:
        raise RuntimeError(
            f"Native host check failed on {host}: Landlock ABI query failed: "
            f"{error}. {REMEDY}"
        ) from error
    if observed < MINIMUM_LANDLOCK_ABI:
        raise RuntimeError(
            f"Native host check failed on {host}: observed Landlock ABI "
            f"{observed}, required >= {MINIMUM_LANDLOCK_ABI}. {REMEDY}"
        )
    return {
        "status": "landlock_abi_supported",
        "system": platform.system(),
        "kernel_release": platform.release(),
        "architecture": platform.machine(),
        "landlock_abi": observed,
        "minimum_landlock_abi": MINIMUM_LANDLOCK_ABI,
        "scope": "ABI query only; full native protection preflights remain mandatory",
        "model_calls": 0,
        "Lean_calls": 0,
    }


def require_supported(directory: Path | None = None) -> dict:
    """Selected backend admission; never downgrade after a failed check."""
    if readonly_mounts.backend() == "landlock":
        return require_landlock()
    guard = readonly_mounts.identity()
    root = (Path.cwd() / "host-checks" if directory is None else directory).resolve()
    folder = root / ("readonly-mounts-" + uuid.uuid4().hex)
    workspace = folder / "workspace"
    workspace.mkdir(parents=True, mode=0o700)
    runtime = folder / "runtime"
    runtime.mkdir(mode=0o700)
    probe, protected = filesystem_probe.prepare(folder, workspace)
    binary = Path(__file__).resolve().parents[3] / "bin/signal-scope"
    previous = os.environ.get("PROOF_SIGNAL_SCOPE_BINARY")
    try:
        os.environ.setdefault("PROOF_SIGNAL_SCOPE_BINARY", str(binary))
        scope = signal_scope.configured_identity()
    finally:
        if previous is None:
            os.environ.pop("PROOF_SIGNAL_SCOPE_BINARY", None)
    memory = native_resources.identity()
    argv = launch_command(
        probe,
        workspace,
        [protected],
        runtime_paths=(runtime,),
        process_boundary="signal_scope",
        filesystem_backend="readonly-mounts",
    )
    receipt = folder / "signal_scope_preflight/native_resources.json"
    native = signal_scope.preflight(
        native_resources.wrap(argv, receipt, memory),
        folder / "signal_scope_preflight",
        scope,
        (workspace, runtime),
        dict(os.environ),
    )
    report = {
        "status": "readonly_mounts_protections_verified",
        "filesystem_guard": guard,
        "system": platform.system(),
        "kernel_release": platform.release(),
        "architecture": platform.machine(),
        "evidence_directory": str(folder),
        "filesystem_preflight": filesystem_probe.verify(folder),
        "signal_preflight": native,
        "memory_preflight": native_resources.evidence(receipt, memory),
        "scope": "CPU protection checks on this host/runtime; not a model or benchmark run",
        "model_calls": 0,
        "Lean_calls": 0,
    }
    (folder / "host-check.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=readonly_mounts.BACKENDS)
    parser.add_argument(
        "--directory", type=Path, help="Retain CPU-only namespace check receipts here"
    )
    args = parser.parse_args()
    if args.backend:
        os.environ[readonly_mounts.ENVIRONMENT] = args.backend
    try:
        report = require_supported(args.directory)
    except (OSError, RuntimeError, ValueError) as error:
        print(
            json.dumps(
                {
                    "status": "unsupported_host",
                    "error": str(error),
                    "backend": readonly_mounts.backend(),
                    "model_calls": 0,
                    "Lean_calls": 0,
                }
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
