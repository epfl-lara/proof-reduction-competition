"""One finite CPU search call, isolated from training-library global patches."""

from __future__ import annotations

import os
import signal
import sys
import time
import traceback
from pathlib import Path

from proof_eval.evidence.immutable import immutable, read, sha


def run(folder: Path) -> int:
    request_path = folder / "request.json"
    request = read(request_path)
    started = {
        "pid": os.getpid(),
        "start_ticks": Path("/proc/self/stat")
        .read_text()
        .rsplit(")", 1)[1]
        .split()[19],
        "parent_pid": os.getppid(),
        "source_sha256": sha(Path(__file__)),
        "request_sha256": sha(request_path),
        "at_epoch": time.time(),
        "deadline_seconds": request["timeout_seconds"],
        "policy_model_calls": 0,
        "embedding_device": "cpu",
    }
    immutable(folder / "started.json", started)

    class BoundedStop(BaseException):
        pass

    def expired(*_args):
        raise BoundedStop("Finite isolated semantic tool deadline")

    signal.signal(signal.SIGALRM, expired)
    signal.alarm(request["timeout_seconds"])
    try:
        from proof_eval.harness import semantic

        if any(
            name == "mcore_bridge" or name.startswith("mcore_bridge.")
            for name in sys.modules
        ):
            raise RuntimeError("Training library leaked into isolated semantic process")
        response = semantic.search(
            request["config"],
            Path(request["project"]),
            request["request"],
            request["version"],
        )
        result_sha = immutable(folder / "result.json", response)
        immutable(
            folder / "finished.json",
            {
                **started,
                "status": "passed",
                "at_epoch": time.time(),
                "result_sha256": result_sha,
            },
        )
        return 0
    except BaseException as error:
        immutable(
            folder / "failed.json",
            {
                **started,
                "at_epoch": time.time(),
                "type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
            },
        )
        return 2
    finally:
        signal.alarm(0)


def main() -> int:
    if len(sys.argv) != 2:
        raise ValueError("Expected one owned semantic request directory")
    return run(Path(sys.argv[1]).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
