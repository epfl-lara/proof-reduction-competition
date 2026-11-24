"""Inherited Linux limits for native agents and their shell descendants only.

The host verifier and model server are siblings, outside these limits. These
are per-process allocation ceilings, not an aggregate process-tree RAM quota.
Linux >= 4.7 applies RLIMIT_DATA to anonymous mmap as well as the heap. A separate
address-space ceiling leaves room for the native client's thread reservations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path

POLICY = "native-data4g-address32g-v1"
DATA_BYTES = 4 * 1024**3
ADDRESS_BYTES = 32 * 1024**3


def identity() -> dict:
    source = Path(__file__).resolve()
    return {
        "policy": POLICY,
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "data_bytes": DATA_BYTES,
        "address_space_bytes": ADDRESS_BYTES,
        "scope": "native_agent_and_descendants_per_process",
        "host_verifier_and_model_server_limited": False,
    }


def validate(value: dict) -> None:
    if value != identity():
        raise ValueError("Native memory policy or launcher changed")


def wrap(argv: list[str], receipt: Path, value: dict) -> list[str]:
    validate(value)
    if receipt.exists():
        raise ValueError("Refusing to reuse native memory-limit evidence")
    return [
        sys.executable,
        "-I",
        value["source"],
        "--receipt",
        str(receipt),
        "--",
        *argv,
    ]


def _limit(kind: int, ceiling: int) -> list[int]:
    soft, hard = resource.getrlimit(kind)
    finite = [x for x in (soft, hard, ceiling) if x != resource.RLIM_INFINITY]
    target = min(finite)
    resource.setrlimit(kind, (target, target))
    actual = list(resource.getrlimit(kind))
    if actual != [target, target]:
        raise RuntimeError("Kernel did not apply the native hard memory limit")
    return actual


def enter(receipt: Path, command: list[str]) -> None:
    if sys.platform != "linux":
        raise RuntimeError("Native memory containment requires Linux")
    version = platform.release().split(".")
    if tuple(int(x) for x in version[:2]) < (4, 7):
        raise RuntimeError("Native heap/mmap containment requires Linux >= 4.7")
    limits = {
        "RLIMIT_DATA": _limit(resource.RLIMIT_DATA, DATA_BYTES),
        "RLIMIT_AS": _limit(resource.RLIMIT_AS, ADDRESS_BYTES),
        "RLIMIT_CORE": _limit(resource.RLIMIT_CORE, 0),
    }
    stat = Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()
    value = {
        **identity(),
        "at_epoch": time.time(),
        "pid": os.getpid(),
        "start_ticks": stat[19],
        "limits": limits,
        "command": command,
        "model_calls": 0,
        "Lean_calls": 0,
    }
    # This runs before Landlock. The receipt is outside the model-writable roots.
    with receipt.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.execvp(command[0], command)


def evidence(receipt: Path, value: dict) -> dict:
    validate(value)
    saved = json.loads(receipt.read_text())
    if any(saved.get(k) != v for k, v in value.items()):
        raise ValueError("Native memory-limit identity changed")
    for key, maximum in (("RLIMIT_DATA", DATA_BYTES), ("RLIMIT_AS", ADDRESS_BYTES)):
        limits = saved.get("limits", {}).get(key)
        if (
            not isinstance(limits, list)
            or len(limits) != 2
            or type(limits[0]) is not int
            or not 0 < limits[0] == limits[1] <= maximum
        ):
            raise ValueError("Native hard memory limit is absent or excessive")
    if saved.get("limits", {}).get("RLIMIT_CORE") != [0, 0]:
        raise ValueError("Native core-file limit changed")
    return {
        "status": "verified",
        "receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
        "receipt": saved,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("A native command after -- is required")
    enter(args.receipt, command)


if __name__ == "__main__":
    main()
