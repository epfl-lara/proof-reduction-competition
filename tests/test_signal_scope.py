"""The actual local provider must preserve signal, evidence and deadline bounds."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from proof_eval.harness.audit import _audit_native_ownership
from proof_eval.providers import execution, signal_scope
from proof_eval.providers.events import parse_events
from proof_eval.providers.processes import enable_subreaper
from proof_eval.providers.retries import retryable_transport_failure


def _run(folder, scope, script, *, timeout=15):
    identity = {"path": sys.executable, "version": "fixture", "signal_scope": scope}
    source = folder.parent / "pinned-source"
    source.mkdir(exist_ok=True)

    def build(workspace, system_file, last_message, output):
        return execution.Launch(
            argv=[sys.executable, "-c", script, str(workspace), str(last_message)],
            environment=dict(os.environ),
            runtime_paths=(),
            cwd=workspace,
            parse=parse_events,
        )

    return execution.generate(
        folder=folder,
        messages=[
            {"role": "system", "content": "fixture"},
            {"role": "user", "content": "fixture"},
        ],
        model="Qwen/Qwen3.8-Flash-Next-FP8",
        effort="xhigh",
        mode="score_edges",
        session=SimpleNamespace(best_code="theorem fixture : True := by trivial"),
        context={"source_projects": {"fixture": str(source)}},
        expected_cli=identity,
        identity=identity,
        instructions="fixture",
        tool_service=lambda *args: nullcontext(),
        provider="lemex-local",
        authentication="local_server_no_api_key",
        build=build,
        timeout=timeout,
    )


def _events(folder):
    return [json.loads(s) for s in (folder / "events.jsonl").read_text().splitlines()]


def test_guard_is_required_before_a_native_start(tmp_path, monkeypatch):
    monkeypatch.delenv("PROOF_SIGNAL_SCOPE_BINARY", raising=False)
    with pytest.raises(ValueError, match="set PROOF_SIGNAL_SCOPE_BINARY"):
        signal_scope.configured_identity()
    with pytest.raises(ValueError, match="unvalidated"):
        _run(tmp_path / "missing", None, "raise AssertionError('must not execute')")
    assert not (tmp_path / "missing/request_started.json").exists()
    assert not (tmp_path / "missing/workspace").exists()


@pytest.mark.parametrize("mutation", ["binary_sha256", "source_sha256", "policy"])
def test_changed_guard_identity_never_dispatches(tmp_path, signal_identity, mutation):
    identity = {**signal_identity, mutation: "changed"}
    with pytest.raises(ValueError, match="unvalidated"):
        _run(tmp_path / mutation, identity, "raise AssertionError('must not execute')")
    assert not (tmp_path / mutation / "request_started.json").exists()


@pytest.mark.parametrize("completion", ["normal", "deadline"])
def test_provider_scope_protects_peers_reaps_orphans_and_preserves_terminal_evidence(
    tmp_path, signal_identity, completion
):
    enable_subreaper()
    peer = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(45)"], start_new_session=True
    )
    folder = tmp_path / completion
    script = f"""
import errno,json,os,signal,subprocess,sys,time
from pathlib import Path
workspace=Path(sys.argv[1])
try: os.kill({peer.pid},0)
except OSError as error: assert error.errno==errno.EPERM
else: raise AssertionError('peer was reachable')
audit=workspace.parent/'signals.jsonl'
try: audit.write_text('tamper')
except PermissionError: pass
else: raise AssertionError('host audit was writable')
child=subprocess.Popen(['sleep','40'],start_new_session=True)
os.killpg(child.pid,signal.SIGTERM)
assert child.wait(timeout=3)==-signal.SIGTERM
orphan=subprocess.Popen(['sleep','40'],start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
(workspace/'orphan.pid').write_text(str(orphan.pid))
print(json.dumps({{'type':'turn.started'}}),flush=True)
"""
    if completion == "deadline":
        script += "time.sleep(40)\n"
    else:
        script += """
Path(sys.argv[2]).write_text('SCOPE_OK')
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'SCOPE_OK'}}),flush=True)
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':1,'output_tokens':1}}),flush=True)
"""
    try:
        result = _run(
            folder,
            signal_identity,
            script,
            timeout=2 if completion == "deadline" else 15,
        )
        assert result["status"] == (
            "budget_exhausted" if completion == "deadline" else "received"
        )
        assert result["signal_scope"]["status"] == "verified"
        assert result["signal_scope"]["denials"] >= 2
        assert peer.poll() is None
        orphan = int((folder / "workspace/orphan.pid").read_text())
        assert (
            not Path(f"/proc/{orphan}").exists()
            or Path(f"/proc/{orphan}/stat").read_text().rsplit(")", 1)[1].split()[0]
            == "Z"
        )
        _audit_native_ownership(folder, result, _events(folder))
        assert (
            _run(
                folder,
                signal_identity,
                script,
                timeout=2 if completion == "deadline" else 15,
            )
            == result
        )
        assert json.loads((folder / "request.json").read_text())["temperature"] is None
        assert not retryable_transport_failure(result)
        if completion == "normal":
            assert result["process_ownership"]["cleanup"]["complete"]
            original = (folder / "signals.jsonl").read_bytes()
            (folder / "signals.jsonl").write_bytes(original + b"{}\n")
            with pytest.raises(ValueError, match="kernel decision"):
                _audit_native_ownership(folder, result, _events(folder))
            (folder / "signals.jsonl").write_bytes(original)
            changed = deepcopy(result)
            changed["signal_scope"]["audit_sha256"] = "changed"
            with pytest.raises(ValueError, match="saved signal evidence changed"):
                _audit_native_ownership(folder, changed, _events(folder))
    finally:
        peer.terminate()
        peer.wait(timeout=5)
        if completion == "deadline" and (folder / "workspace/orphan.pid").exists():
            orphan = int((folder / "workspace/orphan.pid").read_text())
            try:
                os.waitpid(orphan, 0)
            except ChildProcessError:
                pass


def test_writable_guard_or_evidence_cannot_be_launched(tmp_path, signal_identity):
    with pytest.raises(ValueError, match="outside model-writable"):
        signal_scope.wrap(["true"], tmp_path, signal_identity, (tmp_path,))
    (tmp_path / "signals.jsonl").write_text("preserve")
    with pytest.raises(ValueError, match="reuse"):
        signal_scope.wrap(["true"], tmp_path, signal_identity, ())
    assert (tmp_path / "signals.jsonl").read_text() == "preserve"


def test_historical_unguarded_evidence_stays_readable(tmp_path):
    (tmp_path / "request.json").write_text(
        json.dumps({"provider": "lemex-local", "cli": {}})
    )
    signal_scope.audit_generation(tmp_path, {"status": "received"})
