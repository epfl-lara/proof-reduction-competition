"""Host supervision of reported streaming usage, separate from CLI transport."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Callable

from proof_eval.evidence.io import fingerprint, now, read, write_json

from .costs import CostConfig, estimate_token_cost
from .processes import stop_tree

UsageReader = Callable[[list[dict]], dict | None]


def read_events(path: Path, *, allow_partial: bool = False) -> list[dict]:
    """Keep a stopped process's unfinished final line as raw evidence."""
    # JSONL uses LF boundaries. Unicode line separators are legal inside JSON
    # strings and must not split a native event into malformed fragments.
    lines = path.read_text().split("\n")
    events = []
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            if allow_partial and index == len(lines) - 1:
                break
            raise
        if not isinstance(event, dict):
            raise ValueError("Native event must be an object")
        events.append(event)
    return events


def _estimate(guard: dict, usage: dict) -> dict:
    return estimate_token_cost(
        CostConfig(**guard["configuration"]),
        usage,
        budget_usd=guard["remaining_usd"],
    )


def communicate_with_budget(
    child: subprocess.Popen[str],
    prompt: str,
    timeout: float | None,
    folder: Path,
    guard: dict,
    usage_reader: UsageReader,
) -> dict | None:
    """Stop only this child when observed API-equivalent spend reaches its cap.

    Counters arrive at response boundaries. Unreported, in-flight usage remains
    unknown; this supervisor cannot certify an invoice ceiling.
    """
    deadline = None if timeout is None else time.monotonic() + timeout
    events: list[dict] = []
    pending = b""
    previous_usage = None
    first = True
    with (folder / "events.jsonl").open("rb") as stream:
        while True:
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                raise subprocess.TimeoutExpired(child.args, timeout)
            try:
                child.communicate(
                    prompt if first else None,
                    timeout=min(0.2, remaining) if remaining is not None else 0.2,
                )
                running = False
            except subprocess.TimeoutExpired:
                running = child.poll() is None
            first = False
            data = pending + stream.read()
            lines = data.split(b"\n")
            pending = lines.pop()
            for line in lines:
                if line.strip():
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        raise ValueError("Native event must be an object")
                    events.append(event)
            usage = usage_reader(events)
            if usage is not None and usage != previous_usage:
                estimate = _estimate(guard, usage)
                record = {
                    "kind": "host_stream_usd",
                    "pid": child.pid,
                    "cost_budget": guard,
                    "event_count": len(events),
                    "events_sha256": fingerprint(events),
                    "observed_token_usage": usage,
                    "estimate": estimate,
                    "observed_at": now(),
                    "usage_complete": False,
                }
                write_json(folder / "cost_progress.json", record)
                previous_usage = usage
                if running and estimate["total_usd"] >= guard["remaining_usd"] - 1e-12:
                    record["stop_requested_at"] = now()
                    write_json(folder / "cost_stop.json", record)
                    record.update(stop_tree(child.pid))
                    child.communicate(timeout=5)
                    write_json(folder / "cost_stop.json", record)
                    return record
            if not running:
                child.communicate(timeout=5)
                return None


def verified_stream_stop(
    folder: Path, events: list[dict], guard: dict | None, usage_reader: UsageReader
) -> bool:
    """Reconstruct a host stop from its immutable native-event prefix."""
    try:
        stop = read(folder / "cost_stop.json")
        count = stop["event_count"]
        if (
            guard is None
            or guard.get("kind") != "host_stream_usd"
            or stop["kind"] != "host_stream_usd"
            or stop["cost_budget"] != guard
            or type(count) is not int
            or not 0 < count <= len(events)
            or stop["pid"] != read(folder / "process.json")["pid"]
            or not stop.get("stop_requested_at")
        ):
            return False
        prefix = events[:count]
        usage = usage_reader(prefix)
        if usage is None:
            return False
        estimate = _estimate(guard, usage)
        return (
            fingerprint(prefix) == stop["events_sha256"]
            and usage == stop["observed_token_usage"]
            and estimate == stop["estimate"]
            and estimate["total_usd"] >= guard["remaining_usd"] - 1e-12
        )
    except (OSError, ValueError, KeyError, TypeError):
        return False
