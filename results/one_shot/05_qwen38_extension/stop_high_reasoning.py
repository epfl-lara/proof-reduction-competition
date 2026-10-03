"""User-authorized stop of the original Qwen3.8 high-effort cohort.

Hold all shared admission slots, drain HTTP and saved responses, then signal
only the two identity-checked extension processes. No model/Lean calls, runtime
edits, fabricated generations, resampling, or signals to the continuation.
"""
from __future__ import annotations

from collections import Counter
import ctypes
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import time


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
GATE = ROOT / ".proof-eval/rcp-admission"
RECEIPT = HERE / "stop_high_reasoning.json"
INITIAL = HERE / "01_context_ablation"
REPAIR = HERE / "03_repaired_context_ablation"
TARGETS = [(425517, 1234605670, "run_one_shot.py", INITIAL),
           (433780, 1234618407, "run_repair_matrix.py", REPAIR)]


def now():
    return datetime.now(timezone.utc).isoformat()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def syscall(number, *args):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    result = libc.syscall(ctypes.c_long(number), *(ctypes.c_long(arg) for arg in args))
    if result < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return result


def pidfd_open(pid):
    require(os.uname().sysname == "Linux" and os.uname().machine == "x86_64", "pidfd syscall architecture is unsupported")
    return syscall(434, pid, 0)


def pidfd_signal(fd, sig):
    return syscall(424, fd, sig, 0, 0)


def exited(fd):
    poll = select.poll()
    poll.register(fd, select.POLLIN)
    return bool(poll.poll(0))


def identity(pid):
    proc = Path("/proc") / str(pid)
    before = (proc / "stat").read_text().rsplit(")", 1)[1].split()
    args = [part.decode() for part in (proc / "cmdline").read_bytes().split(b"\0") if part]
    cwd = str((proc / "cwd").resolve())
    after = (proc / "stat").read_text().rsplit(")", 1)[1].split()
    require(before[19] == after[19], "PID identity changed while reading it")
    return {"pid": pid, "start_ticks": int(after[19]), "arguments": args, "cwd": cwd}


def option(args, name):
    values = [arg.split("=", 1)[1] for arg in args if arg.startswith(name + "=")]
    values += [args[i + 1] for i, arg in enumerate(args[:-1]) if arg == name]
    require(len(values) == 1, "ambiguous process option: " + name)
    return values[0]


def validate_target(target):
    pid, start_ticks, script, output = target
    info = identity(pid)
    args, cwd = info["arguments"], Path(info["cwd"])
    require(info["start_ticks"] == start_ticks and cwd == ROOT, "unexpected PID start identity or working directory")
    require(len(args) > 2 and Path(args[1]).name == "run_with_rcp_limit.py", "target is not the admission wrapper")
    require("--" in args, "wrapper command separator is missing")
    split = args.index("--")
    require(Path(args[split + 1]).name == script, "wrapped script differs")
    require((cwd / option(args[split + 2:], "--output")).resolve() == output, "wrapped output differs")
    require((cwd / option(args[:split], "--gate")).resolve() == GATE, "target uses a different gate")
    require((cwd / option(args[:split], "--log-directory")).resolve() == HERE / "admission", "target log directory differs")
    configurations = [p for p in (HERE / "admission").glob("*.config.json") if read(p).get("pid") == pid]
    require(len(configurations) == 1, "target does not have exactly one invocation configuration")
    cfg = read(configurations[0])
    command = read(configurations[0].with_name(cfg["invocation"] + ".command.json"))
    require(command["arguments"] == args[split + 2:] and Path(command["wrapped_script"]) == ROOT / "src" / script,
            "target command differs from its saved invocation")
    require({k: v for k, v in cfg.items() if k not in {"pid", "invocation", "started_at"}} == read(GATE / "config.json"),
            "target invocation gate configuration differs")
    return {**info, "invocation": cfg["invocation"], "configuration_sha256": sha(configurations[0]),
            "command_sha256": sha(configurations[0].with_name(cfg["invocation"] + ".command.json"))}


def cell_hashes():
    return {str(path.relative_to(HERE)): sha(path) for directory in [INITIAL, REPAIR]
            for path in sorted((directory / "cells").rglob("*")) if path.is_file()}


def invocation_evidence(info, output):
    log = HERE / "admission" / (info["invocation"] + ".jsonl")
    events = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    queued, admitted, released = {}, {}, {}
    for event in events:
        require(event["invocation"] == info["invocation"] and event["pid"] == info["pid"], "admission event identity differs")
        ticket, phase = event["ticket"], event["event"]
        require(phase in {"queued", "admitted", "released"}, "unexpected blocked or unknown ticket during drain")
        if phase == "queued":
            require(ticket not in queued, "duplicate queued ticket")
            queued[ticket] = event
        elif phase == "admitted":
            require(ticket in queued and ticket not in admitted, "invalid admission trajectory")
            admitted[ticket] = event
        else:
            require(ticket in admitted and ticket not in released, "invalid release trajectory")
            released[ticket] = event
    require(set(admitted) == set(released), "a target HTTP admission has not released")
    pending = [value for key, value in queued.items() if key not in admitted]
    calls = [value for value in admitted.values() if value["kind"] == "create_chat_completion"]
    pattern = "*/generation.json" if output == INITIAL else "*/rounds/*/generation.json"
    generations = list((output / "cells").glob(pattern))
    results_ready = []
    generation_counts = Counter()
    for path in generations:
        generation = read(path)
        generation_counts[generation["status"]] += 1
        result_path = path.with_name("result.json")
        if result_path.exists():
            record = read(result_path)
            require(record["generation"] == generation, "saved result and response differ")
            results_ready.append(path)
    outcomes = Counter(released[value["ticket"]]["outcome"] for value in calls)
    ready = (len(calls) == len(generations) == len(results_ready)
             and outcomes["returned"] == generation_counts["received"]
             and outcomes["exception"] == generation_counts["transport_error"])
    return {"pid": info["pid"], "invocation": info["invocation"], "admitted_http": len(admitted),
            "released_http": len(released), "admitted_model_calls": len(calls),
            "saved_generations": len(generations), "saved_generation_results": len(results_ready),
            "generation_status_counts": dict(generation_counts), "ready": ready,
            "queued_never_admitted_tickets": pending, "log_sha256": sha(log) if log.exists() else None}


def main():
    lock = (HERE / ".stop_high_reasoning.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    require(not RECEIPT.exists(), "a stop receipt already exists; refusing another stop attempt")
    own_fd = pidfd_open(os.getpid())
    try:
        pidfd_signal(own_fd, 0)  # Harmless kernel/ABI check, never sends a real signal.
        require(not exited(own_fd), "own pidfd unexpectedly reports exited")
    finally:
        os.close(own_fd)
    record = {"schema_version": 1, "status": "preparing", "started_at": now(),
              "authorization": "User requested stopping Qwen3.8 and testing lower reasoning separately.",
              "initial_pid": TARGETS[0][0], "repair_pid": TARGETS[1][0], "coordinator_pid": os.getpid(),
              "gate_directory": str(GATE), "script_sha256": sha(__file__),
              "signals": [], "slots": [], "barrier_released_at": None, "snapshots": {}}
    streams, descriptors = [], []
    succeeded = False
    try:
        gate_config = read(GATE / "config.json")
        record["gate_config_sha256"] = sha(GATE / "config.json")
        record["gate_reservations_sha256_before"] = sha(GATE / "reservations.json")
        sources = {**gate_config["legacy_code_sha256"], "src/run_with_rcp_limit.py": gate_config["wrapper_sha256"]}
        require(all(sha(ROOT / path) == expected for path, expected in sources.items()), "a frozen source pin changed")
        record["frozen_source_sha256"] = sources
        record["targets"] = []
        for target in TARGETS:
            fd = pidfd_open(target[0])
            descriptors.append(fd)
            info = validate_target(target)
            require(not exited(fd), "target exited during identity verification")
            record["targets"].append(info)
        original_hashes = cell_hashes()
        record["cell_sha256_before"] = original_hashes
        record["status"] = "acquiring_barrier"
        write(RECEIPT, record)
        pending = {}
        for slot in range(5):
            path = GATE / f"slot_{slot}.lock"
            existed = path.exists()
            stream = path.open("a")
            streams.append(stream)
            pending[slot] = stream
            stat = os.fstat(stream.fileno())
            record["slots"].append({"slot": slot, "path": str(path), "device": stat.st_dev,
                                    "inode": stat.st_ino, "existed_before": existed, "acquired_at": None})
        while pending:
            for slot, stream in list(pending.items()):
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue
                require(os.stat(GATE / f"slot_{slot}.lock").st_ino == os.fstat(stream.fileno()).st_ino,
                        "slot path inode changed during barrier acquisition")
                record["slots"][slot]["acquired_at"] = now()
                del pending[slot]
                write(RECEIPT, record)
                print(json.dumps({"event": "slot_acquired", "slot": slot, "remaining_slots": sorted(pending), "at": now()}), flush=True)
            if pending:
                time.sleep(.05)
        record["status"], record["barrier_acquired_at"] = "draining_saved_responses", now()
        write(RECEIPT, record)
        print(json.dumps({"event": "barrier_acquired", "at": now()}), flush=True)
        while True:
            evidence = [invocation_evidence(info, target[3]) for info, target in zip(record["targets"], TARGETS)]
            initial_results = {p.parent.name: read(p) for p in (INITIAL / "cells").glob("*/result.json")}
            repair_results = {p.parent.name for p in (REPAIR / "cells").glob("*/result.json")}
            no_call_finalizable = {key for key, value in initial_results.items()
                                  if not value["generation"].get("content", "").strip() or value["all_versions_passed"]}
            if all(item["ready"] for item in evidence) and no_call_finalizable <= repair_results:
                break
            time.sleep(.1)
        record["drained_at"], record["drain_evidence"] = now(), evidence
        record["initial_terminal_cells"] = len(initial_results)
        record["repair_terminal_cells"] = len(repair_results)
        record["nonempty_initial_cells"] = sorted(key for key, value in initial_results.items() if value["generation"].get("content", "").strip())
        record["unfinished_initial_markers"] = sorted(str(p.relative_to(HERE)) for p in (INITIAL / "cells").glob("*/request_started.json") if not p.with_name("generation.json").exists())
        record["unfinished_repair_markers"] = sorted(str(p.relative_to(HERE)) for p in (REPAIR / "cells").glob("*/rounds/*/request_started.json") if not p.with_name("generation.json").exists())
        require(all(sha(ROOT / path) == expected for path, expected in sources.items()) and sha(GATE / "config.json") == record["gate_config_sha256"], "source or gate configuration changed before stop")
        snapshot_dir = HERE / "validation/stop_high_reasoning"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        for _, _, _, output in TARGETS:
            destination = snapshot_dir / (output.name + ".run_before.json")
            require(not destination.exists(), "run snapshot already exists")
            destination.write_bytes((output / "run.json").read_bytes())
            record["snapshots"][output.name] = {"path": str(destination.relative_to(HERE)), "sha256": sha(destination)}
        write(RECEIPT, record)
        print(json.dumps({"event": "responses_drained", "initial_terminal_cells": len(initial_results),
                          "queued_never_admitted": sum(len(item["queued_never_admitted_tickets"]) for item in evidence), "at": now()}), flush=True)
        for target, expected, fd in zip(TARGETS, record["targets"], descriptors):
            current = validate_target(target)
            require(current == expected and not exited(fd), "target identity changed before its signal")
            pidfd_signal(fd, signal.SIGTERM)
            record["signals"].append({"pid": target[0], "signal": "SIGTERM", "method": "pidfd_send_signal", "at": now()})
            write(RECEIPT, record)
        deadline = time.monotonic() + 30
        while not all(exited(fd) for fd in descriptors):
            require(time.monotonic() < deadline, "target did not exit after its sole SIGTERM")
            time.sleep(.05)
        record["processes_exited_at"] = now()
        final_hashes = cell_hashes()
        require(all(final_hashes.get(path) == expected for path, expected in original_hashes.items()), "pre-existing source cell bytes changed")
        record["cell_sha256_after"] = final_hashes
        record["drain_evidence_after_exit"] = [invocation_evidence(info, target[3]) for info, target in zip(record["targets"], TARGETS)]
        require(all(item["ready"] for item in record["drain_evidence_after_exit"]), "saved HTTP evidence changed at exit")
        for _, _, _, output in TARGETS:
            last_snapshot = snapshot_dir / (output.name + ".run_before_external_stop.json")
            require(not last_snapshot.exists(), "final run snapshot already exists")
            last_snapshot.write_bytes((output / "run.json").read_bytes())
            record["snapshots"][output.name].update(pre_publication_path=str(last_snapshot.relative_to(HERE)),
                                                     pre_publication_sha256=sha(last_snapshot))
            previous = read(output / "run.json")
            previous.update(status="interrupted", interrupted_at=now(), interruption_origin="external_user_stop",
                            stop_receipt=str(RECEIPT), stop_reason="User requested stopping Qwen3.8 high reasoning and a separate lower-effort test.")
            write(output / "run.json", previous)
        record["status"] = "stopped_barrier_held"
        succeeded = True
    except BaseException as exc:
        record.update(status="failed", failure_type=type(exc).__name__, failure=str(exc), failed_at=now())
        raise
    finally:
        for stream in streams:
            stream.close()
        record["barrier_released_at"] = now()
        record["gate_reservations_sha256_after"] = sha(GATE / "reservations.json")
        for fd in descriptors:
            os.close(fd)
        if succeeded:
            record["status"] = "stopped"
        write(RECEIPT, record)
        print(json.dumps({"event": "stop_coordinator_finished", "status": record["status"], "barrier_released_at": record["barrier_released_at"]}), flush=True)
        lock.close()


if __name__ == "__main__":
    main()
