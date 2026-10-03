"""Drain the old repair scheduler at a cell boundary, then reuse its exact work."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from run_with_rcp_limit import legacy_initial_alive

OUT = ROOT / "results/one_shot/06_parallel_continuation"
BASE = ROOT / "results/one_shot/01_context_ablation"
SOURCE = ROOT / "results/one_shot/03_repaired_context_ablation"
EXPECTED_PID = 3585312
COMMAND = [sys.executable, "src/run_with_rcp_limit.py",
    "--legacy-initial", str(BASE), "--legacy-repair", str(SOURCE),
    "--gate", str(ROOT / ".proof-eval/rcp-admission"),
    "--log-directory", str(OUT / "admission"), "--", "src/run_repair_matrix.py",
    "--input", str(BASE), "--output", str(OUT / "03_repaired_context_ablation"),
    "--reuse", str(SOURCE), "--per-model", "4"]


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_process_alive():
    proc = Path("/proc") / str(EXPECTED_PID)
    try:
        args = [part.decode() for part in (proc / "cmdline").read_bytes().split(b"\0") if part]
        if not args:  # Exited process awaiting its parent's wait().
            return False
        cwd = Path(os.readlink(proc / "cwd"))
    except (FileNotFoundError, ProcessLookupError):
        return False
    if "src/run_repair_matrix.py" not in args or "--output" not in args:
        raise RuntimeError("Expected repair PID now belongs to a different command")
    if (cwd / args[args.index("--output") + 1]).resolve() != SOURCE:
        raise RuntimeError("Expected repair PID has a different output directory")
    return True


def terminal_source_files():
    """Reject every partial source cell before the runner can skip it in reuse."""
    files = {}
    folders = sorted(path for path in (SOURCE / "cells").iterdir() if path.is_dir())
    for folder in folders:
        if folder.is_symlink() or not (folder / "result.json").is_file():
            raise RuntimeError("Nonterminal or symlink source cell: " + folder.name)
        if not (folder / "cell_config.json").is_file():
            raise RuntimeError("Terminal cell lacks configuration: " + folder.name)
        for marker in folder.rglob("request_started.json"):
            if not (marker.parent / "generation.json").is_file():
                raise RuntimeError("Started request lacks saved generation: " + str(marker))
        for path in sorted(folder.rglob("*")):
            if path.is_symlink():
                raise RuntimeError("Symlink source evidence: " + str(path))
            if path.is_file() and not path.name.endswith(".lock"):
                files[str(path.relative_to(SOURCE / "cells"))] = digest(path)
    return folders, files


def main():
    path = OUT / "launch.json"
    if path.exists():
        raise RuntimeError("Continuation launch already recorded; inspect it before manual resume")
    record = {"status": "waiting_for_initial_completion", "created_at": now(),
              "command": COMMAND, "launcher_sha256": digest(Path(__file__))}

    def save():
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        tmp.replace(path)

    save()
    try:
        while (read(BASE / "run.json").get("status") != "finished"
               or legacy_initial_alive(BASE) or not (SOURCE / "config.json").exists()):
            time.sleep(5)
        if source_process_alive():
            record.update(status="draining_original_repair", signal_intended_at=now(),
                          signal="SIGINT to PID only", signal_pid=EXPECTED_PID,
                          source_run_before_drain=read(SOURCE / "run.json"))
            save()  # Refuse a second launch even if interrupted after this point.
            try:
                os.kill(EXPECTED_PID, signal.SIGINT)
            except ProcessLookupError:
                record["process_exited_before_signal_at"] = now()
            else:
                record["signal_sent_at"] = now()
            save()
            print(json.dumps({"status": record["status"], "pid": EXPECTED_PID}), flush=True)
            while source_process_alive():
                time.sleep(5)
        source_run = read(SOURCE / "run.json")
        if source_run.get("status") not in {"interrupted", "complete"}:
            raise RuntimeError("Original repair has no expected terminal run state")
        folders, files = terminal_source_files()
        record.update(status="drained", drained_at=now(), source_run_after_drain=source_run,
                      source_terminal_cells=len(folders), source_cell_files_sha256=files,
                      source_matrix_config_sha256=digest(SOURCE / "matrix_config.json"),
                      source_config_sha256=digest(SOURCE / "config.json"))
        save()
        destination = OUT / "03_repaired_context_ablation"
        destination.mkdir(exist_ok=True)
        with (destination / "execution.log").open("a") as log:
            child = subprocess.Popen(COMMAND, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            record.update(status="running", started_at=now(), pid=child.pid)
            save()
            print(json.dumps({"launched_pid": child.pid, "reused_terminal_cells": len(folders)}), flush=True)
            code = child.wait()
        # Completed reused cells must remain exact copies throughout continuation.
        for relative, expected in files.items():
            if digest(SOURCE / "cells" / relative) != expected or digest(destination / "cells" / relative) != expected:
                raise RuntimeError("Source or reused cell evidence changed: " + relative)
        record.update(status="exited", returncode=code, finished_at=now(), reused_bytes_verified=True)
        save()
        raise SystemExit(code)
    except Exception as exc:
        record.update(status="blocked", error_type=type(exc).__name__, error=str(exc), updated_at=now())
        save()
        raise


if __name__ == "__main__":
    main()
