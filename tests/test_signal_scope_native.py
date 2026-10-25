"""Actual pinned native client through the integrated provider; localhost only."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
import threading
import uuid
from contextlib import nullcontext
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

from proof_eval.harness.audit import _audit_native_ownership
from proof_eval.providers import lemex_local
from proof_eval.providers.capture_proxy import CaptureProxy


def test_actual_native_provider_signal_scope_capture_and_finalization(
    tmp_path, monkeypatch, signal_identity
):
    # Only the pinned production-image gate supplies these explicit fixtures.
    catalog = Path(os.environ["PROOF_SCOPE_NATIVE_CATALOG"])
    binary = Path(os.environ["PROOF_SCOPE_NATIVE_BINARY"])
    assert (
        hashlib.sha256(binary.read_bytes()).hexdigest()
        == "06f461985fbe54ee03515a6d6e4df913790b55e7a43425c4f81786c7763e6aac"
    )
    monkeypatch.setenv("PATH", str(binary.parent) + os.pathsep + os.environ["PATH"])
    profile = tmp_path / "profile"
    profile.mkdir()
    source = tmp_path / "pinned-source"
    source.mkdir()
    (profile / "models.json").write_bytes(catalog.read_bytes())
    folder = tmp_path / "attempt"
    workspace = folder / "workspace"
    nonce = uuid.uuid4().hex
    peer = subprocess.Popen(["sleep", "40"], start_new_session=True)
    tool = tmp_path / "fixture_tool.py"
    tool.write_text(
        "import errno,json,os,signal,subprocess\nfrom pathlib import Path\n"
        f"try:os.kill({peer.pid},0)\n"
        "except OSError as error:assert error.errno==errno.EPERM\n"
        "else:raise AssertionError('peer signal crossed boundary')\n"
        "child=subprocess.Popen(['sleep','35'],start_new_session=True)\n"
        "os.killpg(child.pid,signal.SIGTERM)\nassert child.wait(timeout=3)==-signal.SIGTERM\n"
        f"try:Path({str(folder / 'signals.jsonl')!r}).write_text('tamper')\n"
        "except PermissionError:pass\nelse:raise AssertionError('writable host audit')\n"
        "orphan=subprocess.Popen(['sleep','35'],start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
        "Path('orphan.pid').write_text(str(orphan.pid))\n"
        "native_child=subprocess.Popen(['sleep','35'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
        "Path('native-group.pid').write_text(str(native_child.pid))\n"
        f"print({nonce!r})\n"
    )
    calls = []
    failures = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            body = json.dumps({"data": [{"id": lemex_local.MODEL}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            calls.append(json.loads(raw))
            if len(calls) == 1:
                item = {
                    "type": "function_call",
                    "call_id": "call_scope_fixture",
                    "name": "exec_command",
                    "arguments": json.dumps(
                        {
                            "cmd": shlex.join([sys.executable, str(tool)]),
                            "yield_time_ms": 10000,
                        }
                    ),
                }
            else:
                outputs = [
                    i.get("output", "")
                    for i in calls[-1].get("input", [])
                    if i.get("type") == "function_call_output"
                ]
                if not any(nonce in str(v) for v in outputs):
                    failures.append("Missing successful native tool stdout")
                item = {
                    "type": "message",
                    "role": "assistant",
                    "id": "fixture_done",
                    "content": [{"type": "output_text", "text": "INTEGRATED_SCOPE_OK"}],
                }
            if len(calls) > 2:
                failures.append("Unexpected repeated fixture turn")
            events = [
                {"type": "response.created", "response": {"id": f"scope-{len(calls)}"}},
                {"type": "response.output_item.done", "item": item},
                {
                    "type": "response.completed",
                    "response": {"id": f"scope-{len(calls)}"},
                },
            ]
            body = "".join(
                "event: " + e["type"] + "\ndata: " + json.dumps(e) + "\n\n"
                for e in events
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}/v1"
    (profile / "config.toml").write_text(
        'model_context_window=266400\nmodel_auto_compact_token_limit=222400\nmodel_provider="local_qwen"\n'
        '[model_providers.local_qwen]\nname="Local fixture"\nwire_api="responses"\n'
        f"base_url={json.dumps(endpoint)}\nrequires_openai_auth=false\n"
    )
    monkeypatch.setenv("PROOF_LEMEX_LOCAL_HOME", str(profile))
    monkeypatch.setenv("PROOF_LEMEX_LOCAL_CAPACITY_NAMESPACE", "fixture-" + nonce)
    try:
        with CaptureProxy(tmp_path / "capture", endpoint) as proxy:
            for key, value in proxy.environment.items():
                monkeypatch.setenv(key, value)
            identity = lemex_local.cli_identity()
            assert identity["signal_scope"] == signal_identity
            result = lemex_local.generate(
                folder=folder,
                messages=[
                    {
                        "role": "system",
                        "content": "Run the deterministic fixture tool.",
                    },
                    {"role": "user", "content": "Run the fixture."},
                ],
                model=lemex_local.MODEL,
                effort="xhigh",
                mode="score_edges",
                session=SimpleNamespace(
                    best_code="theorem fixture : True := by trivial",
                    row={"name": "model-free-fixture"},
                ),
                context={"source_projects": {"fixture": str(source)}},
                expected_cli=identity,
                instructions="Local deterministic signal-ownership fixture.",
                tool_service=lambda *args: nullcontext(),
                timeout=25,
                capacity_slots=1,
            )
        assert result["status"] == "received", result
        assert result["content"].strip() == "INTEGRATED_SCOPE_OK"
        assert len(calls) == 2 and not failures, failures
        assert result["signal_scope"]["status"] == "verified"
        assert peer.poll() is None
        orphan = int((workspace / "orphan.pid").read_text())
        assert orphan in result["process_ownership"]["cleanup"]["terminated_pids"]
        assert not Path(f"/proc/{orphan}").exists()
        native_child = int((workspace / "native-group.pid").read_text())
        assert not Path(f"/proc/{native_child}").exists()
        ready = json.loads((folder / "signal_scope_ready.json").read_text())
        root_pid = ready["root"]["pid"]
        raw_signals = (folder / "signals.jsonl").read_text().splitlines()
        signals = [json.loads(line) for line in raw_signals]
        assert any(
            row["caller_tgid"] == root_pid
            and row["caller"] != root_pid
            and row["target_arg"] < 0
            and row["error"] == 0
            and row["signal_number"] == 9
            and native_child in row["delivered_targets"]
            for row in signals
        ), "Native runtime thread must cancel its live owned group through the guard"

        events = [
            json.loads(s) for s in (folder / "events.jsonl").read_text().splitlines()
        ]
        _audit_native_ownership(folder, result, events)
        captures = list((tmp_path / "capture").glob("attempts/*/requests/*"))
        assert len(captures) == 2
        assert all(
            (p / "request.body").stat().st_size > 0
            and (p / "response.body").stat().st_size > 0
            for p in captures
        )
        assert list((workspace / "rollout-traces").rglob("*.json*"))
        assert identity["context_settings"]["model_context_window"] == 266400
        assert identity["context_settings"]["model_auto_compact_token_limit"] == 222400
    finally:
        if peer.poll() is None:
            peer.terminate()
        peer.wait(timeout=5)
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
