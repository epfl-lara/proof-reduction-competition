"""A stopped local native client may recover without overlapping owned tools."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from proof_eval.harness.audit import _audit_native_ownership
from proof_eval.harness.limits import start_budget
from proof_eval.harness.tracking import stop_decision
from proof_eval.providers import execution
from proof_eval.providers.events import parse_events
from proof_eval.providers.isolation import abi_version
from proof_eval.providers.retries import (
    OWNED_CLIENT_EOF,
    retryable_transport_failure,
)


@pytest.mark.parametrize(
    "failure", ["silent", "reported", "sigterm", "auth", "not_started"]
)
def test_owned_native_eof_reaps_detached_tools_and_drains_host_checks_before_retry(
    tmp_path, failure, signal_identity
):
    try:
        if abi_version() < 3:
            pytest.skip("Landlock ABI >= 3 required")
    except (OSError, RuntimeError) as error:
        pytest.skip(str(error))
    source = tmp_path / "pinned-source"
    source.mkdir()
    budget = start_budget(tmp_path, 14400)
    identity = {
        "path": sys.executable,
        "version": "test",
        "sha256": "test",
        "signal_scope": signal_identity,
    }
    phases = []

    @contextmanager
    def capacity():
        phases.append("capacity_enter")
        try:
            yield None
        finally:
            phases.append("capacity_exit")

    @contextmanager
    def service(session, workspace):
        host_check = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"]
        )
        phases.append("service_enter")
        try:
            yield
        finally:
            # This accepted host-side check belongs to the theorem worker,
            # not the native process, and must be drained by its own service.
            assert host_check.poll() is None
            host_check.terminate()
            host_check.wait(timeout=5)
            phases.append("service_drained")

    def run(folder, script):
        def build(workspace, system_file, last_message, output):
            return execution.Launch(
                argv=[sys.executable, "-c", script, str(workspace), str(last_message)],
                environment=dict(os.environ),
                runtime_paths=(),
                cwd=workspace,
                parse=parse_events,
                capacity=capacity,
            )

        return execution.generate(
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
            timeout=30,
        )

    sibling = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        script = """
import json, os, subprocess, sys
from pathlib import Path
workspace = Path(sys.argv[1])
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                         start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
(workspace / 'detached.pid').write_text(str(child.pid))
"""
        if failure != "not_started":
            script += "print(json.dumps({'type': 'turn.started'}), flush=True)\n"
        if failure == "sigterm":
            script += (
                "import signal, time\n"
                "os.kill(os.getpid(), signal.SIGTERM)\n"
                "time.sleep(60)\n"
            )
        if failure in {"reported", "auth"}:
            script += (
                "print("
                + repr(
                    json.dumps(
                        {
                            "type": "error",
                            "message": (
                                OWNED_CLIENT_EOF
                                if failure == "reported"
                                else "unexpected status 401 Unauthorized"
                            ),
                        }
                    )
                )
                + ", flush=True)\nraise SystemExit(1)\n"
            )
        first = tmp_path / "first"
        failed = run(first, script)
        assert failed["status"] == "transport_error"
        assert failed["usage"] is None
        assert failed["returncode"] == (
            143 if failure == "sigterm" else int(failure in {"reported", "auth"})
        )
        assert retryable_transport_failure(failed) == (
            failure in {"silent", "reported", "sigterm"}
        )
        assert phases == [
            "capacity_enter",
            "service_enter",
            "service_drained",
            "capacity_exit",
        ]
        receipt = json.loads((first / "process_ownership.json").read_text())
        detached = int((first / "workspace/detached.pid").read_text())
        assert detached in receipt["cleanup"]["terminated_pids"]
        assert detached in [p["pid"] for p in receipt["cleanup"]["reaped"]]
        assert not Path(f"/proc/{detached}").exists()
        assert receipt["cleanup"]["remaining_pids"] == []
        assert sibling.poll() is None
        assert json.loads((first / "generation.json").read_text()) == failed
        assert json.loads((first / "request.json").read_text())["timeout"] == 30
        saved_events = [
            json.loads(line)
            for line in (first / "events.jsonl").read_text().splitlines()
        ]
        _audit_native_ownership(first, failed, saved_events)

        if failure in {"auth", "not_started"}:
            assert "owned_client_eof" not in failed
            return

        config = {
            "provider": "lemex-local",
            "budget_tracking": "time",
            "max_transport_restarts": 2,
            "max_budget_restarts": 10000,
            "cleanup_reserve_seconds": 0,
        }
        decision_args = {
            "config": config,
            "generation": failed,
            "cost": {"status": "unknown_usage", "total_usd": None},
            "unavailable": False,
            "round_number": 0,
            "time_remaining": budget["deadline_epoch"] - time.time(),
        }
        assert stop_decision(**decision_args, transport_restarts_used=0) is None
        assert (
            stop_decision(**decision_args, transport_restarts_used=2)["kind"]
            == "transport_recovery_limit"
        )
        expired = {**decision_args, "time_remaining": 0}
        assert (
            stop_decision(**expired, transport_restarts_used=0)["kind"]
            == "cleanup_reserve"
        )
        assert decision_args["cost"]["total_usd"] is None

        final = "theorem t : True := by trivial"
        message = {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": final},
        }
        success = run(
            tmp_path / "second",
            "import json,sys; from pathlib import Path; "
            f"Path(sys.argv[2]).write_text({final!r}); "
            f"print(json.dumps({message!r})); "
            "print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 1, 'output_tokens': 1}}))",
        )
        assert success["status"] == "received"
        assert "owned_client_eof" not in success
        assert not retryable_transport_failure(success)
        assert sibling.poll() is None
        assert start_budget(tmp_path, 14400) == budget
        second = tmp_path / "second"
        _audit_native_ownership(
            second,
            success,
            [
                json.loads(line)
                for line in (second / "events.jsonl").read_text().splitlines()
            ],
        )

        with pytest.raises(ValueError, match="matching active stream"):
            _audit_native_ownership(first, failed, [])
        original_receipt = (first / "process_ownership.json").read_text()
        (first / "process_ownership.json").write_text("{}")
        with pytest.raises(ValueError, match="receipt differs"):
            _audit_native_ownership(first, failed, saved_events)
        (first / "process_ownership.json").write_text(original_receipt)
        process_path = first / "process.json"
        original_process = process_path.read_text()
        changed_process = json.loads(original_process)
        changed_process["start_ticks"] = "different-process"
        process_path.write_text(json.dumps(changed_process))
        with pytest.raises(ValueError, match="exited and reaped"):
            _audit_native_ownership(first, failed, saved_events)
        process_path.write_text(original_process)
        _audit_native_ownership(first, failed, saved_events)

        for mutation in (
            "provider",
            "active",
            "cleanup",
            "identity",
            "digest",
            "service",
            "error",
        ):
            unsafe = deepcopy(failed)
            if mutation == "provider":
                unsafe["provider"] = "lemex"
            elif mutation == "active":
                unsafe["status"] = "indeterminate"
            elif mutation == "cleanup":
                unsafe["process_ownership"]["cleanup"]["remaining_pids"] = [detached]
            elif mutation == "identity":
                unsafe["process_ownership"]["supervisor"]["start_ticks"] = None
            elif mutation == "digest":
                unsafe["owned_client_eof"]["ownership_sha256"] = "changed"
            elif mutation == "service":
                unsafe["owned_client_eof"]["tool_service_drained"] = False
            else:
                unsafe["events_errors"] = [
                    {"type": "error", "message": "unexpected status 401 Unauthorized"}
                ]
            assert not retryable_transport_failure(unsafe), mutation
    finally:
        sibling.terminate()
        sibling.wait(timeout=5)


@pytest.mark.parametrize("status", ["indeterminate", "transport_error"])
def test_missing_terminal_without_confirmed_owned_exit_is_never_retried(status):
    assert not retryable_transport_failure(
        {
            "status": status,
            "provider": "lemex-local",
            "completed_turns": 0,
            "events_errors": [{"type": "error", "message": OWNED_CLIENT_EOF}],
        }
    )
