"""Real CLI/tool round trip against a deterministic localhost Responses stub.

No model or Lean process exists in this test. The stub requests one harmless
shell command, then returns fixed text; all evidence stays in the given folder.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from contextlib import nullcontext
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

from proof_eval.providers import (
    execution,
    lemex_local,
    native_resources,
    readonly_mounts,
    responses,
    signal_scope,
)
from proof_eval.providers.execution import Launch

TEXT = "HOST_GUARD_PROTOCOL_OK"


def main(root: Path, binary: Path) -> dict:
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    profile = root / "profile"
    profile.mkdir()
    home = root / "home"
    (home / ".cache").mkdir(parents=True)
    os.environ["HOME"] = str(home)
    source = root / "source.txt"
    source.write_text("owned protocol canary\n")
    catalog = json.loads(
        Path(lemex_local.__file__).with_name("local_catalog.json").read_text()
    )
    catalog["models"][0]["slug"] = lemex_local.MODEL
    catalog_path = profile / "models.json"
    catalog_path.write_text(json.dumps(catalog))
    requests = []
    errors = []

    class Stub(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(request)
            try:
                if len(requests) == 1:
                    names = {item.get("name") for item in request.get("tools", [])}
                    assert "exec_command" in names, sorted(str(n) for n in names)
                    item = {
                        "type": "function_call",
                        "id": "fc_guard",
                        "call_id": "call_guard",
                        "name": "exec_command",
                        "arguments": json.dumps(
                            {
                                "cmd": "printf protocol-tool-ok",
                                "yield_time_ms": 1000,
                                "max_output_tokens": 100,
                            }
                        ),
                    }
                elif len(requests) == 2:
                    assert "protocol-tool-ok" in json.dumps(request["input"])
                    item = {
                        "type": "message",
                        "id": "msg_guard",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {"type": "output_text", "text": TEXT, "annotations": []}
                        ],
                    }
                else:
                    raise AssertionError("Unexpected extra local stub request")
                response = {
                    "id": "resp_guard_" + str(len(requests)),
                    "object": "response",
                    "model": lemex_local.MODEL,
                    "status": "completed",
                    "output": [item],
                    "usage": {
                        "input_tokens": 1,
                        "output_tokens": 1,
                        "total_tokens": 2,
                        "input_tokens_details": {"cached_tokens": 0},
                        "output_tokens_details": {"reasoning_tokens": 0},
                    },
                }
                events = [
                    {
                        "type": "response.created",
                        "response": {**response, "status": "in_progress", "output": []},
                    },
                    {
                        "type": "response.output_item.added",
                        "output_index": 0,
                        "item": (
                            {**item, "arguments": ""}
                            if item["type"] == "function_call"
                            else item
                        ),
                    },
                ]
                if item["type"] == "function_call":
                    events += [
                        {
                            "type": "response.function_call_arguments.delta",
                            "item_id": item["id"],
                            "output_index": 0,
                            "delta": item["arguments"],
                        },
                        {
                            "type": "response.function_call_arguments.done",
                            "item_id": item["id"],
                            "output_index": 0,
                            "arguments": item["arguments"],
                        },
                    ]
                else:
                    events += [
                        {
                            "type": "response.output_text.delta",
                            "item_id": item["id"],
                            "output_index": 0,
                            "content_index": 0,
                            "delta": TEXT,
                        }
                    ]
                events += [
                    {
                        "type": "response.output_item.done",
                        "output_index": 0,
                        "item": item,
                    },
                    {"type": "response.completed", "response": response},
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
            except Exception as error:
                errors.append(repr(error))
                self.send_error(500)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        guard = signal_scope.configured_identity()
        identity = {
            "signal_scope": guard,
            "native_resources": native_resources.identity(),
            "filesystem_guard": readonly_mounts.identity(),
        }

        def build(workspace, system_file, final, folder):
            argv = responses.command(
                binary=str(binary),
                workspace=workspace,
                system_file=system_file,
                last_message=final,
                model=lemex_local.MODEL,
                effort="xhigh",
                instructions="CPU protocol test: execute the supplied tool request only.",
                settings={
                    "model_catalog_json": str(catalog_path),
                    "model_provider": "guard_stub",
                    "model_providers.guard_stub.name": "CPU guard protocol stub",
                    "model_providers.guard_stub.base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "model_providers.guard_stub.wire_api": "responses",
                    "model_providers.guard_stub.requires_openai_auth": False,
                    "model_providers.guard_stub.supports_websockets": False,
                    "model_providers.guard_stub.request_max_retries": 0,
                    "model_providers.guard_stub.stream_max_retries": 0,
                },
            )
            argv.insert(1, "--no-daemon")
            env = {
                k: os.environ[k] for k in ("PATH", "HOME", "LANG") if k in os.environ
            }
            env["LEMEX_HOME"] = str(profile)
            return Launch(
                argv=argv,
                environment=env,
                runtime_paths=(profile,),
                cwd=workspace,
                parse=lemex_local.parse_events,
            )

        folder = root / "generation"
        result = execution.generate(
            folder=folder,
            messages=[
                {"role": "system", "content": "Local CPU protocol test only."},
                {
                    "role": "user",
                    "content": "Use the requested shell command and return the fixed marker.",
                },
            ],
            model=lemex_local.MODEL,
            effort="xhigh",
            mode="score_edges",
            session=SimpleNamespace(best_code="owned test marker; not Lean input"),
            context={"source_projects": {"canary": str(source)}},
            expected_cli=identity,
            identity=identity,
            instructions="No model or Lean is called",
            tool_service=lambda *args: nullcontext(),
            provider="lemex-local",
            authentication="localhost_stub_no_key",
            build=build,
            timeout=20,
        )
        assert not errors, errors
        assert result["status"] == "received", result
        assert result["content"].strip() == TEXT
        assert result["tool_items"] == 1 and len(requests) == 2
        assert source.read_text() == "owned protocol canary\n"
        signal_scope.audit_generation(folder, result)
        report = {
            "status": "passed",
            "real_native_CLI_and_shell_tool": True,
            "canned_HTTP_requests": len(requests),
            "model_calls": 0,
            "Lean_calls": 0,
            "offline_audit": True,
            "native_tool_items": result["tool_items"],
        }
        (root / "protocol-report.json").write_text(json.dumps(report, indent=2) + "\n")
        return report
    finally:
        (root / "stub-requests.json").write_text(json.dumps(requests, indent=2) + "\n")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    print(
        json.dumps(
            main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()), indent=2
        )
    )
