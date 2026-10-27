"""Regression contracts for real deadline/ownership races, with no paid models."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from proof_eval.evidence.io import fingerprint, read, write_json
from proof_eval.harness import limits
from proof_eval.harness.audit import _audit_native_ownership
from proof_eval.harness.recovery import _generation
from proof_eval.harness.tracking import stop_decision
from proof_eval.providers import execution, lemex_local, processes
from proof_eval.providers.retries import retryable_transport_failure


def test_deadline_stop_precedes_transport_classification_but_not_unavailable_checks():
    arguments = dict(
        config={"budget_tracking": "time", "cleanup_reserve_seconds": 0},
        generation={"status": "budget_exhausted", "error": "native time limit"},
        cost={"total_usd": None},
        round_number=0,
        time_remaining=0,
    )
    assert stop_decision(**arguments, unavailable=False)["kind"] == "time_limit"
    assert stop_decision(**arguments, unavailable=True)["kind"] == "infrastructure"
    arguments["time_remaining"] = 100
    assert stop_decision(**arguments, unavailable=False)["kind"] == "infrastructure"


def test_terminal_budget_end_overrides_an_earlier_unexhausted_snapshot(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(limits.time, "time", lambda: 100)
    start = limits.start_budget(tmp_path, 7200)
    write_json(
        tmp_path / "budget_end.json", {"exhausted": True, "work_stopped_epoch": 7300}
    )
    summary = limits.time_budget_summary(tmp_path, exhausted=False)
    assert summary["exhausted"] is True and summary["elapsed_seconds"] == 7200
    assert all(summary[k] == v for k, v in start.items())


def recovery_fixture(folder, *, ownership):
    folder.mkdir(parents=True)
    process = {
        "pid": 123,
        "start_ticks": "10",
        "native_supervisor": True,
        "ownership_schema_version": 2,
    }
    native = {"pid": 124, "start_ticks": "11"}
    startup = {
        "schema_version": 2,
        "supervisor": {"pid": 123, "start_ticks": "10"},
        "native": native,
        "native_exec_gated": True,
        "at_epoch": 100,
    }
    write_json(folder / "request.json", {"cli": {"ownership_schema_version": 2}})
    write_json(folder / "request_started.json", {"started_at": "test"})
    write_json(folder / "process.json", process)
    write_json(folder / "process_ownership_started.json", startup)
    workspace = folder / "workspace"
    workspace.mkdir()
    final = "theorem t : True := by trivial"
    (workspace / "final.txt").write_text(final)
    events = [
        {"type": "turn.started"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": final}},
        {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 10}},
    ]
    (folder / "events.jsonl").write_text("\n".join(map(json.dumps, events)) + "\n")
    stopped = {
        "exhausted": True,
        "work_stopped_epoch": 7300,
        "terminated_pids": [123, 124],
        "process_start_ticks": {"123": "10", "124": "11"},
        "cleanup": {"complete": True, "freeze_complete": True, "remaining_pids": []},
    }
    write_json(folder.parent / "budget_end.json", stopped)
    if ownership:
        write_json(
            folder / "process_ownership.json",
            {
                "schema_version": 1,
                "supervisor": startup["supervisor"],
                "native": native,
                "native_returncode": 0,
                "native_exited": True,
                "startup": startup,
                "cleanup": {"complete": True, "remaining_pids": []},
            },
        )
    return events


def test_recovery_binds_a_received_final_to_its_real_ownership_receipt(tmp_path):
    folder = tmp_path / "attempt_00"
    events = recovery_fixture(folder, ownership=True)
    generation = _generation(folder, "lemex-local")
    assert generation["status"] == "received"
    assert generation["process_ownership"] == read(folder / "process_ownership.json")
    _audit_native_ownership(folder, generation, events)


def test_final_event_at_hard_deadline_is_controlled_not_a_fabricated_native_exit(
    tmp_path,
):
    folder = tmp_path / "attempt_00"
    events = recovery_fixture(folder, ownership=False)
    generation = _generation(folder, "lemex-local")
    assert generation["status"] == "budget_exhausted"
    assert generation["termination"] == "problem_deadline"
    assert "process_ownership" not in generation
    assert generation["host_deadline_cleanup"]
    _audit_native_ownership(folder, generation, events)
    receipt = read(folder / "deadline_cleanup.json")
    receipt["stopped"]["cleanup"]["complete"] = False
    write_json(folder / "deadline_cleanup.json", receipt)
    with pytest.raises(ValueError, match="cleanup evidence"):
        _audit_native_ownership(folder, generation, events)


def test_signal_tainted_owned_eof_is_never_retried_even_if_cleanup_finished():
    ownership = {
        "schema_version": 1,
        "supervisor": {"pid": 1, "start_ticks": "10"},
        "native": {"pid": 2, "start_ticks": "11"},
        "native_exited": True,
        "native_returncode": -15,
        "cleanup": {"complete": True, "remaining_pids": []},
    }
    generation = {
        "status": "transport_error",
        "provider": "lemex-local",
        "completed_turns": 0,
        "supervisor_returncode": 0,
        "process_ownership": ownership,
        "owned_client_eof": {
            "schema_version": 1,
            "reason": "active_native_event_stream_eof",
            "tool_service_drained": True,
            "ownership_sha256": fingerprint(ownership),
        },
    }
    assert retryable_transport_failure(generation)
    ownership["supervisor_signals"] = [{"signal": 15}]
    generation["owned_client_eof"]["ownership_sha256"] = fingerprint(ownership)
    assert not retryable_transport_failure(generation)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux process custody")
def test_native_exec_cannot_run_before_durable_startup_identity(tmp_path, monkeypatch):
    marker = tmp_path / "native-ran"

    def fail_receipt(*args):
        raise OSError("simulated durable-storage failure")

    monkeypatch.setattr(processes, "_write_receipt", fail_receipt)
    with pytest.raises(OSError, match="durable-storage"):
        processes._supervise(
            tmp_path / "process_ownership.json",
            (),
            [
                sys.executable,
                "-c",
                "from pathlib import Path; import sys; Path(sys.argv[1]).touch()",
                str(marker),
            ],
        )
    assert not marker.exists()


@pytest.mark.skipif(sys.platform != "linux", reason="Linux process custody")
def test_hard_stop_reaps_detached_children_and_preserves_peer(tmp_path):
    ready = tmp_path / "ready.json"
    script = """
import json, os, subprocess, sys, time
from pathlib import Path
from proof_eval.providers.processes import enable_subreaper
enable_subreaper()
leaf=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True)
Path(sys.argv[1]).write_text(json.dumps({'leaf':leaf.pid}))
time.sleep(60)
"""
    peer = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    child = subprocess.Popen([sys.executable, "-c", script, str(ready)])
    try:
        until = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < until:
            assert child.poll() is None
            time.sleep(0.01)
        leaf = read(ready)["leaf"]
        stopped = processes.stop_tree(child.pid)
        child.wait(timeout=5)
        assert stopped["cleanup"]["complete"] is True
        assert stopped["cleanup"]["remaining_pids"] == []
        assert not Path(f"/proc/{leaf}").exists()  # A zombie is insufficient.
        assert peer.poll() is None
    finally:
        if child.poll() is None:
            processes.stop_tree(child.pid)
            child.wait(timeout=5)
        peer.terminate()
        peer.wait(timeout=5)


@pytest.mark.skipif(sys.platform != "linux", reason="Pinned Linux native scope")
@pytest.mark.parametrize("nondumpable", [False, True])
def test_native_timeout_has_full_host_cleanup_and_no_zombie(
    tmp_path, signal_identity, nondumpable
):
    source = tmp_path / "source"
    source.mkdir()
    folder = tmp_path / "attempt_00"

    @contextmanager
    def service(*args):
        yield

    script = """
import json, subprocess, sys, time
from pathlib import Path
leaf_code='import ctypes, time; ctypes.CDLL(None).prctl(4, 0, 0, 0, 0); time.sleep(60)' if NONDUMPABLE else 'import time; time.sleep(60)'
leaf=subprocess.Popen([sys.executable,'-c',leaf_code,'_ProofEval_deadbeef.lean'],start_new_session=True)
Path('detached.pid').write_text(str(leaf.pid))
print(json.dumps({'type':'turn.started'}),flush=True)
time.sleep(60)
"""
    script = "NONDUMPABLE=" + repr(nondumpable) + "\n" + script
    identity = {
        "path": sys.executable,
        "version": "test",
        "sha256": "test",
        "signal_scope": signal_identity,
        "ownership_schema_version": 2,
    }

    def build(workspace, *args):
        return execution.Launch(
            argv=[sys.executable, "-c", script],
            environment=dict(os.environ),
            runtime_paths=(),
            cwd=workspace,
            parse=lemex_local.parse_events,
        )

    generation = execution.generate(
        folder=folder,
        messages=[
            {"role": "system", "content": "policy"},
            {"role": "user", "content": "proof"},
        ],
        model="Qwen/Qwen3.8-Flash-Next-FP8",
        effort="xhigh",
        mode="score_edges",
        session=SimpleNamespace(best_code="theorem t : True := by trivial"),
        context={"source_projects": {"v1": str(source)}},
        expected_cli=identity,
        instructions="tools",
        tool_service=service,
        identity=identity,
        provider="lemex-local",
        authentication="local_server_no_api_key",
        build=build,
        timeout=0.8,
    )
    assert generation["status"] == "budget_exhausted"
    assert generation["host_deadline_cleanup"]
    leaf = int((folder / "workspace/detached.pid").read_text())
    assert not Path(f"/proc/{leaf}").exists()
    events = [
        json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()
    ]
    _audit_native_ownership(folder, generation, events)
    # Reproduce the outer deadline arriving after native cleanup but before
    # generation publication. Only the enclosing worker remains in its snapshot.
    native_stop = read(folder / "native_timeout_cleanup.json")
    assert native_stop["supervisor_reaped"] is True
    write_json(
        folder.parent / "budget_end.json",
        {
            "exhausted": True,
            "process_start_ticks": {"99": "9"},
            "cleanup": {
                "complete": True,
                "freeze_complete": True,
                "remaining_pids": [],
            },
        },
    )
    (folder / "generation.json").unlink()
    recovered = _generation(folder, "lemex-local")
    assert recovered["status"] == "budget_exhausted"
    assert read(folder / "deadline_cleanup.json")["source"] == "native_timeout"
    _audit_native_ownership(folder, recovered, events)
