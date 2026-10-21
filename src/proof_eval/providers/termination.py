"""Immediate host evidence for native process exits, independent of event parsing."""

from __future__ import annotations

import signal
import sys
from pathlib import Path

from proof_eval.evidence.io import now, write_json


def record_exit(
    folder: Path,
    returncode: int,
    *,
    timed_out: bool = False,
    cost_stopped: bool = False,
    monitor_error: str | None = None,
) -> dict:
    """Record controlled stops separately; a shell-style exit is only suggestive."""
    signum = -returncode if returncode < 0 else returncode - 128
    try:
        signal_name = signal.Signals(signum).name
    except ValueError:
        signal_name = None
    controlled = timed_out or cost_stopped or monitor_error is not None
    record = {
        "at": now(),
        "returncode": returncode,
        "signal": signal_name,
        "signal_basis": (
            "kernel_wait_status"
            if returncode < 0
            else "shell_exit_convention_only" if signal_name else None
        ),
        "controlled": controlled,
        "reason": (
            "deadline"
            if timed_out
            else (
                "cost_limit"
                if cost_stopped
                else (
                    "monitor_error"
                    if monitor_error is not None
                    else "unexpected_exit" if returncode else "normal_exit"
                )
            )
        ),
        "monitor_error": monitor_error,
    }
    write_json(folder / "termination.json", record)
    if returncode and not controlled:
        write_json(folder / "incident.json", record)
        print(
            f"PROOF ALERT: unexpected native exit {returncode}; {folder}",
            file=sys.stderr,
            flush=True,
        )
    return record
