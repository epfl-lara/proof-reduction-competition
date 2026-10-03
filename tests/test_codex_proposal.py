import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import shutil
import threading

import pytest

from codex_proposal import TOOL_INSTRUCTIONS, cli_identity, command, parse_events


def test_success_requires_final_and_allows_tools():
    events = [{"type": "item.completed", "item": {"type": "agent_message", "text": "theorem x : True := by trivial"}},
              {"type": "turn.completed", "usage": {"input_tokens": 20, "output_tokens": 10, "cached_input_tokens": 0}}]
    assert parse_events(events, events[0]["item"]["text"], 0)["status"] == "received"
    for extra in ([{"type": "turn.failed"}], [events[-1]]):
        assert parse_events(events + extra, events[0]["item"]["text"], 0)["status"] == "transport_error"
    assert parse_events(events + [{"type": "item.completed", "item": {"type": "command_execution"}}], events[0]["item"]["text"], 0)["tool_items"] == 1
    assert parse_events(events, "different final", 0)["status"] == "transport_error"


def test_command_rejects_substitution(tmp_path):
    with pytest.raises(ValueError):
        command(binary="codex", workspace=tmp_path, system_file=tmp_path / "s", last_message=tmp_path / "f", model="gpt-6-astra", effort="high")


@pytest.mark.skipif(shutil.which('codex') is None, reason='Codex CLI is not installed')
@pytest.mark.parametrize('isolated', [False, True])
def test_installed_cli_sends_exact_prompt_with_tools(tmp_path, isolated):
    """No remote model call: inspect the CLI's real HTTP body at localhost."""
    received = []
    final = "theorem x : True := by trivial"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            if self.headers.get("Content-Encoding") == "zstd":
                import zstandard
                raw = zstandard.ZstdDecompressor().decompress(raw)
            received.append(json.loads(raw))
            msg = {"id": "msg_1", "type": "message", "role": "assistant", "status": "completed",
                   "content": [{"type": "output_text", "text": final, "annotations": []}]}
            response = {"id": "resp_1", "object": "response", "status": "completed", "output": [msg],
                        "usage": {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30}}
            payload = "".join("event: " + kind + "\ndata: " + json.dumps(value) + "\n\n" for kind, value in [
                ("response.output_item.added", {"type": "response.output_item.added", "output_index": 0, "item": {**msg, "status": "in_progress", "content": []}}),
                ("response.output_text.delta", {"type": "response.output_text.delta", "item_id": "msg_1", "output_index": 0, "content_index": 0, "delta": final}),
                ("response.output_item.done", {"type": "response.output_item.done", "output_index": 0, "item": msg}),
                ("response.completed", {"type": "response.completed", "response": response})])
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(payload.encode())))
            self.end_headers()
            self.wfile.write(payload.encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    system = "EXACT BENCHMARK SYSTEM"
    user = "EXACT BENCHMARK USER"
    (tmp_path / "system.txt").write_text(system)
    empty = tmp_path / "empty"
    empty.mkdir()
    args = command(binary=cli_identity()["path"], workspace=empty, system_file=tmp_path / "system.txt",
                   last_message=tmp_path / "final.txt", model="gpt-6-astra", effort="max")
    overrides = {"model_provider": "local_test", "model_providers.local_test.name": "Local test only",
                 "model_providers.local_test.base_url": f"http://127.0.0.1:{server.server_port}/v1",
                 "model_providers.local_test.wire_api": "responses",
                 "model_providers.local_test.request_max_retries": 0,
                 "model_providers.local_test.stream_max_retries": 0,
                 "features.enable_request_compression": False}
    args = args[:-1] + [v for k, value in overrides.items() for v in ("-c", k + "=" + json.dumps(value))] + ["-"]
    if isolated:
        from codex_readonly import abi_version
        from run_codex_baselines_isolated import launch_command
        try:
            if abi_version() < 3:
                pytest.skip('Landlock ABI >= 3 required')
        except (OSError, RuntimeError) as exc:
            pytest.skip(str(exc))
        protected = tmp_path / 'readonly_source'
        protected.mkdir()
        # Keep outputs and writable cwd in one sibling, outside the protected tree.
        (empty / 'system.txt').write_text(system)
        args = [str(empty / 'final.txt') if value == str(tmp_path / 'final.txt') else
                value.replace(str(tmp_path / 'system.txt'), str(empty / 'system.txt')) for value in args]
        args = launch_command(args, empty, [protected])
    try:
        proc = subprocess.run(args, input=user, text=True, capture_output=True, timeout=30, cwd=empty)
    finally:
        server.shutdown()
        server.server_close()
    assert proc.returncode == 0, proc.stderr
    assert len(received) == 1
    request = received[0]
    (tmp_path / "captured_request.json").write_text(json.dumps(request, indent=2))
    assert request["model"] == "gpt-6-astra"
    assert request["reasoning"]["effort"] == "max"
    assert request.get("tools") or any(item.get("tools") for item in request["input"])
    messages = [item for item in request["input"] if item.get("type") == "message"]
    assert len(messages) == 3, request["input"]
    assert messages[0]["role"] == "developer"
    assert messages[0]["content"] == [{"type": "input_text", "text": system}]
    assert messages[1]["role"] == "developer"
    assert messages[1]["content"] == [{"type": "input_text", "text": TOOL_INSTRUCTIONS}]
    assert messages[2]["role"] == "user"
    assert messages[2]["content"] == [{"type": "input_text", "text": user}]
    assert ((empty if isolated else tmp_path) / "final.txt").read_text().strip() == final
    events = [json.loads(line) for line in proc.stdout.splitlines()]
    assert parse_events(events, final, 0)["status"] == "received"
