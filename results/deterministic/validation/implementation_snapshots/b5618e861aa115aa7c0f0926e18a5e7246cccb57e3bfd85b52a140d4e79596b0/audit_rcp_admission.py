"""Audit saved admission evidence without importing an RCP client or making calls.

This checks the supplied wrapped invocations, not all traffic using an API key.
Wall-clock intervals are evidence, not a distributed tracing clock. The frozen
wrapper's invocation records do not identify the lock directory/inode; launcher
evidence must establish that all processes used the supplied shared gate.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
SEMANTICS = "New list_models and create_chat_completion HTTP calls share five slots minus unresolved legacy repair models; requests and responses unchanged."
TERMINAL = {"finished", "complete", "interrupted", "paused_at_call_budget", "incomplete_base_terminal"}
IDENTIFIER = re.compile(r"[0-9a-f]{32}\Z")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def timestamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return result.timestamp()


def number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit_events(events, configurations, *, unresolved_models, complete=False):
    """Validate per-ticket order, then conservatively compare event intervals.

    Events must be supplied in each invocation's file order. Equal-time
    endpoints are treated as possibly overlapping. A strict overlap on one
    slot is contradictory only if local wall/monotonic duration checks agree.
    A live missing-release tail can instead make a snapshot inconclusive.
    """
    errors, uncertainty = [], []
    tickets, counts = {}, Counter()
    known_models = set(next(iter(configurations.values()))["legacy_models"]) if configurations else set()
    for event in events:
        invocation, ticket = event.get("invocation"), event.get("ticket")
        label = f"{invocation}/{ticket}"
        try:
            cfg = configurations[invocation]
            require(isinstance(ticket, str) and IDENTIFIER.fullmatch(ticket), "bad ticket")
            require(event.get("pid") == cfg["pid"], "PID differs from invocation")
            require(type(event.get("thread")) is int, "missing thread")
            kind = event.get("kind")
            require(kind in {"create_chat_completion", "list_models"}, "unknown HTTP kind")
            at = timestamp(event["at"])
            require(at >= timestamp(cfg["started_at"]), "event predates invocation")
            phase = event.get("event")
            require(phase in {"queued", "admitted", "released", "blocked"}, "unknown event")
            if phase == "queued":
                require(ticket not in tickets, "duplicate ticket or queue")
                tickets[ticket] = {"invocation": invocation, "kind": kind, "thread": event["thread"], "queued": event}
            else:
                require(ticket in tickets, "event has no queue")
                item = tickets[ticket]
                require((invocation, kind, event["thread"]) == (item["invocation"], item["kind"], item["thread"]), "ticket identity changed")
                require("released" not in item and "blocked" not in item, "event follows terminal ticket")
                if phase == "admitted":
                    require("admitted" not in item, "duplicate admission")
                    reserved = event.get("reserved_legacy_models")
                    require(isinstance(reserved, list) and len(set(reserved)) == len(reserved), "bad reservations")
                    require(set(reserved) <= known_models, "unknown reserved model")
                    require(set(unresolved_models) <= set(reserved), "unresolved legacy model was not reserved")
                    require(type(event.get("slot")) is int and len(reserved) <= event["slot"] < 5, "slot violates reserved legacy bound")
                    require(number(event.get("queue_seconds")), "bad monotonic queue duration")
                elif phase == "released":
                    require("admitted" in item, "release without admission")
                    require(event.get("slot") == item["admitted"]["slot"], "release slot changed")
                    require(event.get("outcome") in {"returned", "exception"}, "bad release outcome")
                    require(number(event.get("admitted_seconds")), "bad monotonic admission duration")
                else:
                    require("admitted" not in item, "admitted ticket cannot become blocked")
                    require(isinstance(event.get("exception_type"), str) and event["exception_type"], "missing blocked exception type")
                    if at < timestamp(item["queued"]["at"]):
                        uncertainty.append(f"{ticket}: blocked timestamp precedes queue (wall-clock uncertainty)")
                item[phase] = event
            counts[phase] += 1
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"{label}: {exc}")

    intervals, pending = [], []
    for ticket, item in tickets.items():
        if "released" not in item and "blocked" not in item:
            pending.append({"ticket": ticket, "invocation": item["invocation"], "state": "admitted" if "admitted" in item else "queued"})
        if "admitted" not in item:
            continue
        admitted, released = item["admitted"], item.get("released")
        try:
            start = timestamp(admitted["at"])
            queue_wall = start - timestamp(item["queued"]["at"])
            if abs(queue_wall - admitted["queue_seconds"]) > 0.1:
                uncertainty.append(f"{ticket}: wall-clock queue interval differs from monotonic duration")
            end = timestamp(released["at"]) if released else math.inf
            if released and abs(end - start - released["admitted_seconds"]) > 0.1:
                uncertainty.append(f"{ticket}: wall-clock admitted interval differs from monotonic duration")
            intervals.append({"ticket": ticket, "start": start, "end": end, "slot": admitted["slot"],
                              "reserved": set(admitted["reserved_legacy_models"]), "open": released is None})
        except (KeyError, TypeError, ValueError):
            errors.append(f"{ticket}: malformed interval")
    clock_uncertain = bool(uncertainty)
    for i, left in enumerate(intervals):
        for right in intervals[i + 1:]:
            if left["slot"] != right["slot"]:
                continue
            overlap = min(left["end"], right["end"]) - max(left["start"], right["start"])
            if overlap < 0:
                continue
            detail = f"slot {left['slot']} intervals {left['ticket']} / {right['ticket']}"
            if overlap == 0 or clock_uncertain or ((left["open"] or right["open"]) and not complete):
                uncertainty.append(detail + ": tie, clock uncertainty, or open snapshot tail")
            else:
                errors.append(detail + ": overlapping admissions")

    max_http, max_bound = 0, 0
    # At each admission, closed endpoints give an upper bound. Reserved-model
    # snapshots can lag a concurrent monotone release, so retain that ambiguity.
    seen_released = set()
    for start in sorted({row["start"] for row in intervals}):
        starting = [row for row in intervals if row["start"] == start]
        active = [row for row in intervals if row["start"] <= start <= row["end"]]
        max_http = max(max_http, len(active))
        for row in starting:
            bound = len(active) + len(row["reserved"])
            max_bound = max(max_bound, bound)
            if bound > 5:
                tied = any(other["end"] == start for other in active)
                stale = bool(row["reserved"] & seen_released)
                tail = any(other["open"] for other in active) and not complete
                if tied or stale or clock_uncertain or tail:
                    uncertainty.append(f"{row['ticket']}: conservative observed bound {bound} exceeds five under timing/snapshot ambiguity")
                else:
                    errors.append(f"{row['ticket']}: observed admission plus legacy bound {bound} exceeds five")
        for row in starting:
            seen_released |= known_models - row["reserved"]
    if complete and pending:
        errors.append(f"complete audit has {len(pending)} unterminated tickets")
    return {"event_counts": dict(counts), "tickets": len(tickets), "pending_tickets": pending,
            "max_observed_http_interval_upper_bound": max_http,
            "max_observed_http_plus_legacy_upper_bound": max_bound,
            "errors": errors, "uncertainties": uncertainty}


def audit(log_directories, gate, *, complete=False, root=ROOT):
    hashes, errors, uncertainty = {}, [], []
    snapshot_at = datetime.now(timezone.utc).isoformat()
    cutoff = timestamp(snapshot_at)

    def read(path):
        path = Path(path)
        data = path.read_bytes()
        hashes[str(path.resolve())] = {"sha256": sha(data), "bytes": len(data)}
        return json.loads(data)

    try:
        gate = Path(gate).resolve()
        config = read(gate / "config.json")
        require(config.get("schema_version") == 1 and config.get("capacity") == 5, "unexpected gate schema/capacity")
        require(config.get("legacy_per_model_reservation") == 1 and config.get("semantics") == SEMANTICS, "gate semantics changed")
        require(number(config.get("poll_seconds")) and 0 < config["poll_seconds"] <= 1, "invalid gate poll interval")
        initial, repair = Path(config["legacy_initial_directory"]), Path(config["legacy_repair_directory"])
        initial_config, matrix = read(initial / "config.json"), read(repair / "matrix_config.json")
        require(sha((initial / "config.json").read_bytes()) == config["legacy_initial_config_sha256"], "legacy initial config hash changed")
        require(sha((repair / "matrix_config.json").read_bytes()) == config["legacy_repair_matrix_sha256"], "legacy repair matrix hash changed")
        require(matrix["per_model"] == 1 and Path(matrix["base_directory"]).resolve() == initial.resolve(), "legacy reservation contract changed")
        require(matrix["base_config_sha256"] == config["legacy_initial_config_sha256"], "legacy base pin differs")
        models = config["legacy_models"]
        require(0 < len(models) < 5 and len(set(models)) == len(models) and models == matrix["models"] == initial_config["models"], "legacy model cohort differs")
        expected = {(name, arm, model) for name in initial_config["names"] for arm in initial_config["arms"] for model in models}
        cells = matrix["cells"]
        require(len(cells) == len(expected) and {tuple(c["logical"]) for c in cells} == expected and len({c["key"] for c in cells}) == len(cells), "legacy cell cohort differs")
        source_map = {**initial_config.get("code_sha256", {}), **matrix.get("code_sha256", {})}
        require(config["legacy_code_sha256"] == source_map, "legacy runtime pin map differs")
        for path, expected_hash in {**source_map, "src/run_with_rcp_limit.py": config["wrapper_sha256"]}.items():
            require(sha((root / path).read_bytes()) == expected_hash, "source hash changed: " + path)
        initial_run = read(initial / "run.json")
        require(initial_run.get("status") == "finished", "original initial run is not finished")
        state = read(gate / "reservations.json")
        completed = state["completed_models"]
        require(set(completed) <= set(models), "unknown completed legacy model")
        for model, saved in completed.items():
            selected = [c for c in cells if c["logical"][2] == model]
            require(set(saved) == {c["key"] for c in selected}, "released legacy cohort is incomplete")
            for cell in selected:
                path = repair / "cells" / cell["key"] / "result.json"
                record = read(path)
                require(hashes[str(path.resolve())]["sha256"] == saved[cell["key"]], "released legacy result hash changed")
                require([record.get("name"), record.get("arm"), record.get("model")] == cell["logical"] and record.get("base_request_sha256") == cell["key"] and isinstance(record.get("outcome"), str) and bool(record["outcome"]), "released legacy result identity differs")
        unresolved = set(models) - set(completed)
        configurations, commands, events, run_status = {}, {}, [], {}
        deferred_events = 0
        for directory in log_directories:
            directory = Path(directory).resolve()
            require(directory.is_dir(), "missing admission directory: " + str(directory))
            local_invocations = set()
            for path in sorted(directory.glob("*.config.json")):
                cfg = read(path)
                invocation = cfg["invocation"]
                require(IDENTIFIER.fullmatch(invocation) is not None and path.name == invocation + ".config.json", "invocation filename/identity differs")
                require(invocation not in configurations, "duplicate invocation supplied")
                require({k: v for k, v in cfg.items() if k not in {"invocation", "pid", "started_at"}} == config, "invocation gate config differs")
                require(type(cfg["pid"]) is int and cfg["pid"] > 0, "bad invocation PID")
                timestamp(cfg["started_at"])
                configurations[invocation] = cfg
                local_invocations.add(invocation)
                command_path = directory / (invocation + ".command.json")
                require(command_path.is_file(), "missing invocation command record")
                command = read(command_path)
                script = Path(command["wrapped_script"])
                require(script in {root / "src/run_one_shot.py", root / "src/run_repair_matrix.py",
                                   root / "src/run_reasoning_probe.py"}, "unsupported wrapped script")
                require(command["invocation"] == invocation and command["wrapper_sha256"] == config["wrapper_sha256"], "command identity/wrapper pin differs")
                require(sha(script.read_bytes()) == command["wrapped_script_sha256"], "wrapped source hash changed")
                args = command["arguments"]
                require(isinstance(args, list) and all(isinstance(x, str) for x in args), "bad wrapped arguments")
                outputs = [arg.split("=", 1)[1] for arg in args if arg.startswith("--output=")]
                outputs += [args[i + 1] for i, arg in enumerate(args[:-1]) if arg == "--output"]
                require(len(outputs) == 1, "cannot identify wrapped output")
                output = (root / outputs[0]).resolve()
                command_run = read(output / "run.json") if (output / "run.json").exists() else {}
                run_status[invocation] = {"output": str(output), "status": command_run.get("status", "missing")}
                if complete:
                    require(command_run.get("status") in TERMINAL, "wrapped run is not terminal")
                commands[invocation] = command
                log = directory / (invocation + ".jsonl")
                if not log.exists():
                    require(not complete or script.name != "run_one_shot.py" or "--prepare-only" in args,
                            "complete one-shot invocation is missing its startup HTTP log")
                    continue  # A repair watcher need not have made any HTTP call.
                data = log.read_bytes()
                hashes[str(log)] = {"sha256": sha(data), "bytes": len(data)}
                if data and not data.endswith(b"\n"):
                    require(not complete, "complete log has an incomplete trailing line")
                    data = data.rsplit(b"\n", 1)[0] + b"\n" if b"\n" in data else b""
                    uncertainty.append(str(log) + ": incomplete trailing snapshot line omitted")
                for line in data.splitlines():
                    event = json.loads(line)
                    require(event.get("invocation") == invocation, "log invocation differs")
                    if timestamp(event["at"]) > cutoff:
                        deferred_events += 1
                        continue
                    events.append(event)
                if complete and script.name == "run_one_shot.py" and "--prepare-only" not in args:
                    require(any(e["invocation"] == invocation and e.get("kind") == "list_models" and e.get("event") == "queued" for e in events),
                            "complete one-shot invocation is missing its startup list_models attempt")
            for path in directory.glob("*.jsonl"):
                require(path.stem in local_invocations, "event log without invocation configuration in the same directory")
        require(bool(configurations), "no invocation configurations found")
        result = audit_events(events, configurations, unresolved_models=unresolved, complete=complete)
        errors += result.pop("errors")
        uncertainty += result.pop("uncertainties")
        require(not complete or deferred_events == 0, "events arrived during complete audit")
        for event in events:
            if event["event"] == "admitted" and initial_run.get("finished_at"):
                require(timestamp(event["at"]) >= timestamp(initial_run["finished_at"]), "admission predates original initial completion")
        result.update(invocations=len(configurations), invocation_runs=run_status, unresolved_legacy_models=sorted(unresolved),
                      deferred_after_snapshot_events=deferred_events)
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        errors.append(str(exc))
        result = {}
    return {"schema_version": 1, "status": "failed" if errors else "inconclusive" if uncertainty else "passed",
            "complete_required": complete, "snapshot_at": snapshot_at, **result,
            "errors": errors, "uncertainties": uncertainty, "artifact_sha256": hashes,
            "scope": "Saved evidence from the supplied gated invocations only; no model, Lean, network, or process-control calls.",
            "limitations": [
                "No retroactive bound is claimed for the earlier ungated initial/repair pools.",
                "Other clients or omitted invocation directories using the same API key are outside this evidence.",
                "Invocation records pin shared semantics but omit the gate path/inode; launcher evidence must independently establish use of the same supplied gate.",
                "Wall timestamps share a host clock, not a globally ordered monotonic trace. Equal endpoints are possible overlap; clock jumps, event-stamping delays and live non-atomic snapshots can make the count inconclusive.",
                "A logged admitted-to-released interval encloses the HTTP call, not its exact network lifetime. Pending tickets in a snapshot are not presumed released; kernel crash-release is not inferred from missing log events.",
                "Terminal run records and closed tickets establish saved-log completion, not independent proof that a historical process exited. Argument/response preservation relies on the pinned reviewed wrapper and its separate offline tests.",
            ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-directory", type=Path, action="append", required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--complete", action="store_true")
    args = parser.parse_args()
    result = audit(args.log_directory, args.gate, complete=args.complete)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ["status", "complete_required", "errors", "uncertainties"]} | {k: result[k] for k in ["invocations", "event_counts", "tickets", "max_observed_http_plus_legacy_upper_bound"] if k in result}))
    return 1 if result["errors"] else 2 if result["uncertainties"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
