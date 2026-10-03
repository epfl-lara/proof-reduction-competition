"""Admission-only wrapper for new RCP runners sharing a five-request key.

The original initial-generation process must have drained. Each unresolved
original repair model reserves one slot, because that frozen runner admits at
most one request per model. New processes share the remaining flock slots.
Neither requests nor responses are rewritten, and no frozen runtime is edited.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import functools
import hashlib
import json
import os
from pathlib import Path
import random
import runpy
import sys
import threading
import time
import uuid


ROOT = Path(__file__).resolve().parent.parent
CAPACITY = 5


class AdmissionEvidenceError(RuntimeError):
    """Missing or contradictory evidence: do not admit an HTTP request."""


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise AdmissionEvidenceError("Unreadable admission evidence: " + str(path)) from exc


def write(path, value):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def legacy_initial_alive(initial, *, proc_root=Path("/proc")):
    """Inspect actual CLI processes; no process signals or subprocess launches."""
    initial = Path(initial).resolve()
    if not proc_root.is_dir():
        raise AdmissionEvidenceError("Process inspection unavailable")
    try:
        processes = list(proc_root.iterdir())
    except OSError as exc:
        raise AdmissionEvidenceError("Process inspection unavailable") from exc
    for process in processes:
        if not process.name.isdigit():
            continue
        try:
            args = [part.decode(errors="replace") for part in (process / "cmdline").read_bytes().split(b"\0") if part]
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError as exc:
            raise AdmissionEvidenceError("Cannot inspect a live process command line") from exc
        positions = [i for i, arg in enumerate(args) if Path(arg).name == "run_one_shot.py"]
        for position in positions:
            tail = args[position + 1:]
            outputs = [value.split("=", 1)[1] for value in tail if value.startswith("--output=")]
            outputs.extend(tail[i + 1] for i, value in enumerate(tail[:-1]) if value == "--output")
            if not outputs:
                raise AdmissionEvidenceError("Cannot identify output of a one-shot process")
            try:
                cwd = Path(os.readlink(process / "cwd"))
            except (FileNotFoundError, ProcessLookupError):
                continue
            except OSError as exc:
                raise AdmissionEvidenceError("Cannot inspect a one-shot process working directory") from exc
            if any((cwd / value).resolve() == initial for value in outputs):
                return True
    return False


class AdmissionGate:
    def __init__(self, *, directory, legacy_initial, legacy_repair, log_directory,
                 poll_seconds=0.5, process_check=legacy_initial_alive):
        if isinstance(poll_seconds, bool) or not 0 < poll_seconds <= 1:
            raise ValueError("poll_seconds must be in (0,1]")
        self.directory = Path(directory).resolve()
        self.initial, self.repair = Path(legacy_initial).resolve(), Path(legacy_repair).resolve()
        self.log_directory = Path(log_directory).resolve()
        self.poll_seconds, self.process_check = poll_seconds, process_check
        self.directory.mkdir(parents=True, exist_ok=True)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        self.invocation = uuid.uuid4().hex
        self.log_path = self.log_directory / (self.invocation + ".jsonl")
        self._log_lock = threading.Lock()
        self.matrix = read(self.repair / "matrix_config.json")
        initial_config = read(self.initial / "config.json")
        if self.matrix.get("per_model") != 1:
            raise AdmissionEvidenceError("Legacy repair must have a frozen one-request-per-model limit")
        if Path(self.matrix["base_directory"]).resolve() != self.initial:
            raise AdmissionEvidenceError("Legacy repair points to a different initial run")
        if self.matrix["base_config_sha256"] != digest(self.initial / "config.json"):
            raise AdmissionEvidenceError("Legacy initial configuration changed")
        models = self.matrix["models"]
        if not models or len(set(models)) != len(models) or len(models) >= CAPACITY:
            raise AdmissionEvidenceError("Invalid legacy model reservation cohort")
        expected = {(name, arm, model) for name in initial_config["names"]
                    for arm in initial_config["arms"] for model in initial_config["models"]}
        cells = self.matrix["cells"]
        if (models != initial_config["models"] or len(cells) != len(expected)
                or {tuple(cell["logical"]) for cell in cells} != expected
                or len({cell["key"] for cell in cells}) != len(cells)):
            raise AdmissionEvidenceError("Legacy repair is not the declared complete cohort")
        self.by_model = {model: [cell for cell in cells if cell["logical"][2] == model] for model in models}
        legacy_code = {**initial_config.get("code_sha256", {}), **self.matrix.get("code_sha256", {})}
        self.config = {"schema_version": 1, "capacity": CAPACITY,
            "legacy_initial_directory": str(self.initial), "legacy_repair_directory": str(self.repair),
            "legacy_initial_config_sha256": digest(self.initial / "config.json"),
            "legacy_repair_matrix_sha256": digest(self.repair / "matrix_config.json"),
            "legacy_models": models, "legacy_per_model_reservation": 1,
            "legacy_code_sha256": legacy_code,
            "wrapper_sha256": digest(__file__), "poll_seconds": poll_seconds,
            "semantics": "New list_models and create_chat_completion HTTP calls share five slots minus unresolved legacy repair models; requests and responses unchanged."}
        with self._state_lock():
            path = self.directory / "config.json"
            if path.exists() and read(path) != self.config:
                raise AdmissionEvidenceError("Shared gate configuration changed")
            existing = path.exists()
            if not existing:
                write(path, self.config)
            if not (self.directory / "reservations.json").exists():
                if existing:
                    raise AdmissionEvidenceError("Shared reservation state is missing")
                write(self.directory / "reservations.json", {"completed_models": {}})
        write(self.log_directory / (self.invocation + ".config.json"),
              {**self.config, "invocation": self.invocation, "pid": os.getpid(), "started_at": now()})

    @contextmanager
    def _state_lock(self):
        with (self.directory / ".state.lock").open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def event(self, event_kind, **fields):
        value = {"event": event_kind, "at": now(), "invocation": self.invocation,
                 "pid": os.getpid(), "thread": threading.get_ident(), **fields}
        with self._log_lock, self.log_path.open("a") as stream:
            stream.write(json.dumps(value, sort_keys=True) + "\n")
            stream.flush()

    def require_initial_drained(self):
        if read(self.initial / "run.json").get("status") != "finished":
            raise AdmissionEvidenceError("Original initial-generation run is not finished")
        if self.process_check(self.initial):
            raise AdmissionEvidenceError("Original initial-generation process is still alive")

    def reservations(self):
        """Release legacy reservations monotonically; changed evidence blocks."""
        self.require_initial_drained()
        if (digest(self.initial / "config.json") != self.config["legacy_initial_config_sha256"]
                or digest(self.repair / "matrix_config.json") != self.config["legacy_repair_matrix_sha256"]
                or digest(__file__) != self.config["wrapper_sha256"]):
            raise AdmissionEvidenceError("Pinned admission evidence or source changed")
        if any(digest(ROOT / path) != expected for path, expected in self.config["legacy_code_sha256"].items()):
            raise AdmissionEvidenceError("Frozen legacy runtime changed")
        with self._state_lock():
            if read(self.directory / "config.json") != self.config:
                raise AdmissionEvidenceError("Shared gate configuration changed")
            state = read(self.directory / "reservations.json")
            completed = state["completed_models"]
            if set(completed) - set(self.by_model):
                raise AdmissionEvidenceError("Unknown released legacy model")
            changed = False
            for model, cells in self.by_model.items():
                if model in completed:
                    saved = completed[model]
                    if set(saved) != {cell["key"] for cell in cells}:
                        raise AdmissionEvidenceError("Released model evidence coverage changed")
                    for cell in cells:
                        path = self.repair / "cells" / cell["key"] / "result.json"
                        try:
                            if digest(path) != saved[cell["key"]]:
                                raise AdmissionEvidenceError("Released model result changed")
                        except OSError as exc:
                            raise AdmissionEvidenceError("Released model evidence is missing or unreadable") from exc
                    continue
                paths = [self.repair / "cells" / cell["key"] / "result.json" for cell in cells]
                if not all(path.is_file() for path in paths):
                    continue  # Missing terminal cells retain this model's reservation.
                hashes = {}
                for cell, path in zip(cells, paths):
                    record = read(path)
                    if ([record.get("name"), record.get("arm"), record.get("model")] != cell["logical"]
                            or record.get("base_request_sha256") != cell["key"]
                            or not isinstance(record.get("outcome"), str) or not record["outcome"]):
                        raise AdmissionEvidenceError("Legacy terminal cell identity is unverified")
                    hashes[cell["key"]] = digest(path)
                completed[model] = hashes
                changed = True
            if changed:
                write(self.directory / "reservations.json", state)
            return [model for model in self.by_model if model not in completed]

    @contextmanager
    def admit(self, kind):
        if kind not in {"create_chat_completion", "list_models"}:
            raise ValueError("Unsupported RCP admission kind")
        ticket, started = uuid.uuid4().hex, time.monotonic()
        self.event("queued", ticket=ticket, kind=kind)
        stream = None
        try:
            while stream is None:
                reserved = self.reservations()
                slots = list(range(len(reserved), CAPACITY))
                random.shuffle(slots)  # Avoid permanent preference for a hot slot.
                for slot in slots:
                    candidate = (self.directory / f"slot_{slot}.lock").open("a")
                    try:
                        fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        candidate.close()
                        continue
                    # Recheck the drain barrier/evidence immediately before HTTP.
                    try:
                        reserved = self.reservations()
                    except BaseException:
                        candidate.close()
                        raise
                    stream = candidate
                    break
                if stream is None:
                    time.sleep(random.uniform(self.poll_seconds / 2, self.poll_seconds))
            admitted = time.monotonic()
            self.event("admitted", ticket=ticket, kind=kind, slot=slot,
                       reserved_legacy_models=reserved, queue_seconds=round(admitted - started, 6))
            outcome = "returned"
            try:
                yield
            except BaseException:
                outcome = "exception"
                raise
            finally:
                self.event("released", ticket=ticket, kind=kind, slot=slot, outcome=outcome,
                           admitted_seconds=round(time.monotonic() - admitted, 6))
        except BaseException as exc:
            if stream is None:
                self.event("blocked", ticket=ticket, kind=kind, exception_type=type(exc).__name__)
            raise
        finally:
            if stream is not None:
                stream.close()  # Kernel also releases flock if this process dies.


@contextmanager
def wrap_client(client_class, gate):
    """Admission only: forward identical positional/keyword objects and result."""
    originals = {name: getattr(client_class, name) for name in ("create_chat_completion", "list_models")}
    def wrapper(name, method):
        @functools.wraps(method)
        def wrapped(self, *args, **kwargs):
            with gate.admit(name):
                return method(self, *args, **kwargs)
        return wrapped
    for name, method in originals.items():
        setattr(client_class, name, wrapper(name, method))
    try:
        yield
    finally:
        for name, method in originals.items():
            setattr(client_class, name, method)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-initial", type=Path, required=True)
    parser.add_argument("--legacy-repair", type=Path, required=True)
    parser.add_argument("--gate", type=Path, default=ROOT / ".proof-eval/rcp-admission")
    parser.add_argument("--log-directory", type=Path, required=True)
    parser.add_argument("--poll-seconds", type=float, default=0.5)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("Provide -- src/run_one_shot.py ... or -- src/run_repair_matrix.py ...")
    script = Path(command[0]).resolve()
    if script not in {ROOT / "src/run_one_shot.py", ROOT / "src/run_repair_matrix.py"}:
        parser.error("Only the existing one-shot and repair-matrix CLIs are supported")
    gate = AdmissionGate(directory=args.gate, legacy_initial=args.legacy_initial,
                         legacy_repair=args.legacy_repair, log_directory=args.log_directory,
                         poll_seconds=args.poll_seconds)
    gate.require_initial_drained()  # Fail before the core runner writes start markers.
    write(args.log_directory / (gate.invocation + ".command.json"),
          {"wrapped_script": str(script), "wrapped_script_sha256": digest(script),
           "arguments": command[1:], "wrapper_sha256": digest(__file__), "invocation": gate.invocation,
           "note": "Core elapsed request times include admission queue waits; they are not model latency rankings."})
    from proof_eval.rcp import RCPClient
    previous = sys.argv
    try:
        sys.argv = [str(script), *command[1:]]
        with wrap_client(RCPClient, gate):
            runpy.run_path(str(script), run_name="__main__")
    finally:
        sys.argv = previous


if __name__ == "__main__":
    main()
