"""Read-only cross-run failure detection with durable, deduplicated local alerts.

The watcher never stops workers, changes results, or retries model requests.
It writes only its own output directory and emits new alerts to its service log.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from proof_eval.evidence.io import fingerprint, now, read, write_json
from proof_eval.providers.processes import process_identity


def _evidence_files(root: Path) -> dict[str, list[Path]]:
    names = {
        "generation.json",
        "incident.json",
        "process.json",
        "cell_process.json",
        "run.json",
        "reporter_error.json",
        "result.json",
    }
    files = {name: [] for name in names}
    for directory, children, entries in os.walk(root):
        children[:] = [
            name
            for name in children
            if name
            not in {
                "workspace",
                "evaluation_cache",
                "analysis_cache",
                ".git",
                ".lake",
                "__pycache__",
                "native",
            }
        ]
        for name in names.intersection(entries):
            files[name].append(Path(directory) / name)
    return files


def inspect_runs(roots: list[Path]) -> list[dict]:
    """Inspect saved evidence, including old runs without termination records."""
    findings = []
    exits = []

    def add(kind: str, path: Path, **details) -> None:
        findings.append(dict(kind=kind, path=str(path), **details))

    for root in roots:
        if not root.exists():
            continue  # A queued run need not have written any results yet.
        files = _evidence_files(root)
        for path in files["result.json"]:
            if path.parent.parent.name != "cells":
                continue
            value = read(path)
            if value.get("status") not in {
                "complete",
                "time_limit",
                "discovery_limit",
                "disabled",
            }:
                add(
                    "cell_incomplete",
                    path,
                    status=value.get("status"),
                    name=value.get("name"),
                )
        for path in files["generation.json"]:
            value = read(path)
            status = value.get("status")
            if status in {"received", "budget_exhausted"}:
                continue
            add(
                "native_failure",
                path,
                status=status,
                returncode=value.get("returncode"),
                error=value.get("error"),
            )
            code = value.get("returncode")
            if isinstance(code, int) and (code < 0 or 129 <= code <= 192):
                if value.get("finished_at"):
                    exits.append(
                        (
                            datetime.fromisoformat(value["finished_at"]).timestamp(),
                            path,
                            code,
                        )
                    )
        for path in files["incident.json"]:
            value = read(path)
            if value.get("reason") == "unexpected_exit":
                add(
                    "unexpected_native_exit",
                    path,
                    returncode=value["returncode"],
                    signal=value.get("signal"),
                    signal_basis=value.get("signal_basis"),
                )
        for path in files["process.json"] + files["cell_process.json"]:
            if (
                path.name == "process.json"
                and not (path.parent / "request_started.json").exists()
            ):
                continue  # Deterministic workers have a different terminal contract.
            if (path.parent / "generation.json").exists() or (
                path.parent / "termination.json"
            ).exists():
                continue
            if (
                path.name == "cell_process.json"
                and (path.parent / "result.json").exists()
            ):
                continue
            value = read(path)
            if not isinstance(value.get("pid"), int):
                continue
            # The whole-problem supervisor may stop the native worker before it
            # can write a terminal marker. Its recorded budget stop is expected.
            budget_stopped = False
            for parent in path.parents:
                if not parent.is_relative_to(root):
                    break
                budget_end = parent / "budget_end.json"
                if budget_end.exists() and value["pid"] in read(budget_end).get(
                    "terminated_pids", []
                ):
                    budget_stopped = True
                    break
            if budget_stopped:
                continue
            actual = process_identity(value["pid"])
            expected = value.get("identity")
            if actual is None or (expected is not None and expected != actual):
                add("missing_native_terminal", path, pid=value["pid"])
        for path in files["run.json"]:
            value = read(path)
            if value.get("status") in {"failed", "incomplete"}:
                add("batch_incomplete", path, status=value["status"])
            elif value.get("status") in {"complete", "finished"}:
                add("batch_finished", path, status=value["status"])
        for path in files["reporter_error.json"]:
            add("reporter_failure", path, error=read(path).get("error"))
    # Correlate host-observed exits, without attributing the sender or claiming
    # an exit of 128+N proves signal N (it can also be an explicit exit code).
    exits.sort(key=lambda item: (item[0], str(item[1])))
    cluster = []
    for item in exits:
        if cluster and item[0] - cluster[0][0] > 5:
            if len(cluster) > 1:
                findings.append(_cluster(cluster))
            cluster = []
        cluster.append(item)
    if len(cluster) > 1:
        findings.append(_cluster(cluster))
    return findings


def _cluster(exits: list[tuple[float, Path, int]]) -> dict:
    return {
        "kind": "correlated_native_exits",
        "attempts": [str(path.parent) for _, path, _ in exits],
        "returncodes": [code for _, _, code in exits],
        "span_seconds": exits[-1][0] - exits[0][0],
        "cause": "unknown; inspect evidence, do not automatically resample",
    }


def check_units(units: list[str]) -> list[dict]:
    """Distinguish failed service supervision from normal queued/inactive states."""
    findings = []
    for unit in units:
        result = subprocess.run(
            [
                "systemctl",
                "--user",
                "show",
                unit,
                "--property=ActiveState,Result",
                "--value",
            ],
            text=True,
            capture_output=True,
            timeout=10,
        )
        if result.returncode:
            findings.append(
                dict(
                    kind="unit_inspection_failed",
                    unit=unit,
                    error=result.stderr.strip(),
                )
            )
        elif "failed" in result.stdout.splitlines():
            findings.append(dict(kind="service_failed", unit=unit))
    return findings


def poll(spec: dict, output: Path, *, timestamp: float | None = None) -> dict:
    """One scan; missing terminals must persist 60 seconds before alerting."""
    timestamp = time.time() if timestamp is None else timestamp
    output.mkdir(parents=True, exist_ok=True)
    state_file = output / "state.json"
    state = read(state_file) if state_file.exists() else {"pending": {}, "seen": []}
    try:
        findings = inspect_runs([Path(p) for p in spec["roots"]])
        findings += check_units(spec.get("units", []))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        findings = [dict(kind="watcher_scan_failed", error=str(error))]
    pending = {}
    new = []
    for finding in findings:
        key = fingerprint(finding)
        if finding["kind"] == "missing_native_terminal":
            first = state["pending"].get(key, timestamp)
            pending[key] = first
            if timestamp - first < 60:
                continue
        if key not in state["seen"]:
            alert = dict(id=key, detected_at=now(), **finding)
            write_json(output / "alerts" / f"{key}.json", alert)
            print("PROOF ALERT " + json.dumps(alert), flush=True)
            state["seen"].append(key)
            new.append(alert)
    state["pending"] = pending
    write_json(state_file, state)
    result = dict(
        checked_at=now(),
        findings=len(findings),
        new_alerts=len(new),
        total_alerts=len(state["seen"]),
        read_only=True,
    )
    write_json(output / "status.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--interval", type=float, default=30)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    if args.interval < 1:
        parser.error("interval must be at least one second")
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / ".watch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while True:
            poll(read(args.spec), args.output)
            if args.once:
                return 0
            time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
