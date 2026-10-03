"""Offline HTTP admission checks; no actual client, model, or Lean calls."""
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import time

import pytest

from run_with_rcp_limit import (AdmissionEvidenceError, AdmissionGate, legacy_initial_alive,
                                wrap_client)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def no_process(_):
    return False


@pytest.fixture
def legacy(tmp_path):
    initial, repair = tmp_path / "initial", tmp_path / "repair"
    config = {"names": ["p", "q"], "arms": ["plain"], "models": ["m1", "m2", "m3"]}
    write(initial / "config.json", config)
    write(initial / "run.json", {"status": "finished"})
    cells = [{"key": hashlib.sha256((name + model).encode()).hexdigest(), "logical": [name, "plain", model]}
             for name in config["names"] for model in config["models"]]
    write(repair / "matrix_config.json", {"base_directory": str(initial),
        "base_config_sha256": hashlib.sha256((initial / "config.json").read_bytes()).hexdigest(),
        "per_model": 1, "models": config["models"], "cells": cells})
    return {"directory": tmp_path / "gate", "legacy_initial": initial, "legacy_repair": repair,
            "log_directory": tmp_path / "logs", "poll_seconds": 0.02, "process_check": no_process}


def finish_model(options, model):
    repair = options["legacy_repair"]
    matrix = json.loads((repair / "matrix_config.json").read_text())
    for cell in matrix["cells"]:
        if cell["logical"][2] == model:
            name, arm, model = cell["logical"]
            write(repair / "cells" / cell["key"] / "result.json",
                  {"name": name, "arm": arm, "model": model,
                   "base_request_sha256": cell["key"], "outcome": "no_candidate"})


def child_requests(options, start, active, maximum):
    gate = AdmissionGate(**options)
    start.wait()
    for _ in range(2):
        with gate.admit("create_chat_completion"):
            with active.get_lock(), maximum.get_lock():
                active.value += 1
                maximum.value = max(maximum.value, active.value)
            time.sleep(0.06)
            with active.get_lock():
                active.value -= 1


def concurrent_wave(options, expected):
    context = multiprocessing.get_context("fork")
    start, active, maximum = context.Event(), context.Value("i", 0), context.Value("i", 0)
    processes = [context.Process(target=child_requests, args=(options, start, active, maximum)) for _ in range(7)]
    for process in processes:
        process.start()
    start.set()
    for process in processes:
        process.join(10)
        assert not process.is_alive()
        assert process.exitcode == 0
    assert active.value == 0
    assert maximum.value == expected


def test_cross_process_slots_respect_legacy_reservations_and_release_monotonically(legacy):
    gate = AdmissionGate(**legacy)
    assert gate.reservations() == ["m1", "m2", "m3"]
    concurrent_wave(legacy, 2)
    finish_model(legacy, "m1")
    assert gate.reservations() == ["m2", "m3"]
    concurrent_wave(legacy, 3)
    finish_model(legacy, "m2")
    finish_model(legacy, "m3")
    assert gate.reservations() == []
    concurrent_wave(legacy, 5)
    events = [json.loads(line) for path in legacy["log_directory"].glob("*.jsonl") for line in path.read_text().splitlines()]
    assert sum(e["event"] == "admitted" for e in events) == 42
    assert sum(e["event"] == "released" for e in events) == 42
    assert all(e["slot"] >= len(e["reserved_legacy_models"]) for e in events if e["event"] == "admitted")


def die_holding_slot(options, ready):
    gate = AdmissionGate(**options)
    with gate.admit("list_models"):
        ready.set()
        os._exit(0)  # Exercise kernel cleanup, bypassing Python finally blocks.


def test_process_crash_releases_flock(legacy):
    context = multiprocessing.get_context("fork")
    ready = context.Event()
    process = context.Process(target=die_holding_slot, args=(legacy, ready))
    process.start()
    assert ready.wait(5)
    process.join(5)
    assert process.exitcode == 0
    concurrent_wave(legacy, 2)


def test_drain_barrier_and_missing_or_changed_evidence_fail_closed(legacy):
    gate = AdmissionGate(**legacy)
    write(legacy["legacy_initial"] / "run.json", {"status": "running"})
    with pytest.raises(AdmissionEvidenceError, match="not finished"):
        with gate.admit("create_chat_completion"):
            pytest.fail("admitted before old initial completed")
    write(legacy["legacy_initial"] / "run.json", {"status": "finished"})
    gate.process_check = lambda _: True
    with pytest.raises(AdmissionEvidenceError, match="still alive"):
        gate.require_initial_drained()
    gate.process_check = no_process
    finish_model(legacy, "m1")
    assert gate.reservations() == ["m2", "m3"]
    path = next((legacy["legacy_repair"] / "cells").glob("*/result.json"))
    path.unlink()
    with pytest.raises(AdmissionEvidenceError, match="missing or unreadable"):
        gate.reservations()
    (legacy["legacy_repair"] / "matrix_config.json").write_text("not JSON")
    with pytest.raises(AdmissionEvidenceError, match="Unreadable"):
        AdmissionGate(**legacy)


def test_unverified_legacy_terminal_record_does_not_release_slot(legacy):
    finish_model(legacy, "m1")
    path = next((legacy["legacy_repair"] / "cells").glob("*/result.json"))
    record = json.loads(path.read_text());record["model"] = "other"
    write(path, record)
    with pytest.raises(AdmissionEvidenceError, match="identity"):
        AdmissionGate(**legacy).reservations()


def test_process_scan_matches_actual_script_output_and_not_another_run(tmp_path):
    proc, cwd = tmp_path / "proc", tmp_path / "workspace"
    cwd.mkdir();(proc / "123").mkdir(parents=True)
    args = ["python", "src/run_one_shot.py", "--output", "results/old"]
    (proc / "123/cmdline").write_bytes(b"\0".join(s.encode() for s in args) + b"\0")
    (proc / "123/cwd").symlink_to(cwd)
    assert legacy_initial_alive(cwd / "results/old", proc_root=proc)
    assert not legacy_initial_alive(cwd / "results/new", proc_root=proc)
    (proc / "123/cmdline").write_bytes(b"python\0src/run_one_shot.py\0--output=results/old\0")
    assert legacy_initial_alive(cwd / "results/old", proc_root=proc)
    (proc / "123/cmdline").write_bytes(b"python\0src/run_one_shot.py\0")
    with pytest.raises(AdmissionEvidenceError, match="Cannot identify"):
        legacy_initial_alive(cwd / "results/old", proc_root=proc)


def test_wrapping_forwards_exact_objects_results_and_exceptions_without_payload_logging(legacy):
    gate = AdmissionGate(**legacy)
    calls, answer, sentinel = [], object(), {"messages": ["PRIVATE_REQUEST_CONTENT"], "token": "PRIVATE_CREDENTIAL"}
    failure = ValueError("PRIVATE_ERROR_CONTENT")
    class FakeClient:
        def create_chat_completion(self, *args, **kwargs):
            calls.append((args, kwargs))
            if kwargs.get("fail"):
                raise failure
            return answer
        def list_models(self, *args, **kwargs):
            calls.append((args, kwargs))
            return answer
    original = FakeClient.create_chat_completion
    client = FakeClient()
    with wrap_client(FakeClient, gate):
        assert client.create_chat_completion(sentinel, option=sentinel) is answer
        assert calls[-1][0][0] is sentinel and calls[-1][1]["option"] is sentinel
        assert client.list_models(timeout=7) is answer
        assert calls[-1] == ((), {"timeout": 7})
        with pytest.raises(ValueError) as captured:
            client.create_chat_completion(fail=True)
        assert captured.value is failure
    assert FakeClient.create_chat_completion is original
    logs = gate.log_path.read_text()
    assert "PRIVATE_" not in logs
    events = [json.loads(line) for line in logs.splitlines()]
    assert [e["event"] for e in events] == ["queued", "admitted", "released"] * 3
    assert [e["kind"] for e in events if e["event"] == "admitted"] == ["create_chat_completion", "list_models", "create_chat_completion"]
    assert events[-1]["outcome"] == "exception"


def test_legacy_higher_per_model_limit_is_rejected(legacy):
    path = legacy["legacy_repair"] / "matrix_config.json"
    config = json.loads(path.read_text());config["per_model"] = 2;write(path, config)
    with pytest.raises(AdmissionEvidenceError, match="one-request-per-model"):
        AdmissionGate(**legacy)


def test_missing_shared_state_does_not_silently_restore_released_reservations(legacy):
    AdmissionGate(**legacy)
    (legacy["directory"] / "reservations.json").unlink()
    with pytest.raises(AdmissionEvidenceError, match="reservation state is missing"):
        AdmissionGate(**legacy)
