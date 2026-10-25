"""Native process-group termination retains custody and a bounded recovery path."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from proof_eval.providers import lemex_local
from proof_eval.providers.events import parse_events
from proof_eval.providers.processes import owned_command


def test_native_final_ignores_empty_trailing_message_but_rejects_changed_answer():
    final = "theorem example : True := by trivial"

    def message(text):
        return {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": text},
        }

    done = {"type": "turn.completed", "usage": {"output_tokens": 23}}
    events = [message(final), message("\n"), done]
    result = parse_events(events, final, 0)
    assert result["status"] == "received"
    assert result["token_usage"] == done["usage"]
    assert parse_events([message("\n"), done], final, 0)["status"] == "transport_error"
    assert parse_events(events, "changed answer", 0)["status"] == "transport_error"
    assert parse_events(events, final, -15)["status"] == "transport_error"
    assert parse_events(events[:-1], final, 0)["status"] == "transport_error"


def test_local_completed_empty_turn_is_explicit_and_preserves_native_usage():
    usage = {"input_tokens": 1000, "output_tokens": 200, "reasoning_output_tokens": 180}
    events = [
        {"type": "turn.started"},
        {"type": "item.completed", "item": {"type": "reasoning", "text": ""}},
        {"type": "turn.completed", "usage": usage},
    ]
    parsed = lemex_local.parse_events(events, "", 0)
    assert parsed["status"] == "received"
    assert parsed["content"] == ""
    assert parsed["empty_completion"] is True
    assert parsed["terminal_schema_version"] == 2
    assert parsed["token_usage"] == usage
    for missing_usage in (None, {}, {"output_tokens": 0}):
        assert (
            lemex_local.parse_events(
                [*events[:-1], {"type": "turn.completed", "usage": missing_usage}],
                "",
                0,
            )["status"]
            == "transport_error"
        )
    assert parse_events(events, "", 0)["status"] == "transport_error"
    assert lemex_local.parse_events(events, "", -15)["status"] == "transport_error"
    assert lemex_local.parse_events(events[:-1], "", 0)["status"] == "transport_error"
    assert (
        lemex_local.parse_events(events + [events[-1]], "", 0)["status"]
        == "transport_error"
    )
    assert (
        lemex_local.parse_events(
            events
            + [{"type": "error", "message": "unexpected status 401 Unauthorized"}],
            "",
            0,
        )["status"]
        == "transport_error"
    )
    assert (
        lemex_local.parse_events([{"type": "turn.completed", "usage": usage}], "", 0)[
            "status"
        ]
        == "transport_error"
    )


@pytest.mark.skipif(sys.platform != "linux", reason="Linux process ownership")
@pytest.mark.parametrize("target", ["supervisor", "group"])
def test_sigterm_owner_records_sender_and_reaps_only_owned_processes(tmp_path, target):
    receipt = tmp_path / "process_ownership.json"
    ready = tmp_path / "ready.json"
    script = """
import json, os, subprocess, sys, time
from pathlib import Path
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                         start_new_session=True)
Path(sys.argv[1]).write_text(json.dumps({'native': os.getpid(), 'detached': child.pid}))
time.sleep(60)
"""
    outsider = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    owner = subprocess.Popen(
        owned_command([sys.executable, "-c", script, str(ready)], receipt),
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            assert owner.poll() is None
            time.sleep(0.01)
        children = json.loads(ready.read_text())
        if target == "group":
            os.killpg(owner.pid, signal.SIGTERM)
        else:
            owner.terminate()
        assert owner.wait(timeout=5) == 0
        saved = json.loads(receipt.read_text())
        assert saved["native_returncode"] == -signal.SIGTERM
        assert saved["native_exited"] is True
        assert saved["cleanup"]["complete"] is True
        assert saved["cleanup"]["remaining_pids"] == []
        assert children["detached"] in saved["cleanup"]["terminated_pids"]
        assert not Path(f"/proc/{children['detached']}").exists()
        notices = json.loads((tmp_path / "process_signals.json").read_text())
        assert saved["supervisor_signals"] == notices
        assert notices[0]["signal"] == signal.SIGTERM
        assert notices[0]["sender"]["pid"] == os.getpid()
        assert notices[0]["sender_uid"] == os.getuid()
        assert outsider.poll() is None
    finally:
        if owner.poll() is None:
            owner.kill()
            owner.wait(timeout=5)
        outsider.terminate()
        outsider.wait(timeout=5)
