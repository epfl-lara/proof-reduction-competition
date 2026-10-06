"""Native retry behavior against a localhost gateway; no paid model requests."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from proof_eval.evidence.io import fingerprint, read, write_json
from proof_eval.harness.config import RunConfig
from proof_eval.harness.configuration import load_inputs
from proof_eval.harness.incumbents import freeze_incumbents, saved_incumbent
from proof_eval.paths import ROOT
from proof_eval.providers import lemex
from proof_eval.providers.costs import CostConfig, generations_cost
from proof_eval.providers.events import parse_events
from proof_eval.providers.retries import retryable_transport_failure

PROOF = "theorem local_retry : True := by trivial"
MODEL = "Qwen/Qwen3.8-Flash-Next"
USAGE = dict(
    input_tokens=400,
    cached_input_tokens=0,
    output_tokens=200,
    reasoning_output_tokens=20,
)


def final_events():
    return [
        {"type": "item.completed", "item": {"type": "agent_message", "text": PROOF}},
        {"type": "turn.completed", "usage": USAGE},
    ]


def test_recovered_native_error_keeps_evidence_and_unknown_billing():
    notice = {
        "type": "error",
        "message": "Reconnecting... 1/5 (stream disconnected before completion)",
    }
    parsed = parse_events([notice, *final_events()], PROOF, 0)
    assert parsed["status"] == "received"
    assert parsed["events_errors"] == parsed["recovered_transport_errors"] == [notice]
    assert parsed["token_usage"] == USAGE
    assert (
        generations_cost(CostConfig("gpt-6.1-sol", "max"), [parsed])["total_usd"]
        is None
    )


@pytest.mark.parametrize(
    "event,returncode",
    [
        ({"type": "error", "message": "unexpected status 401 Unauthorized"}, 0),
        ({"type": "turn.failed", "error": {"message": "Reconnecting... 1/5"}}, 0),
        ({"type": "error", "message": "Reconnecting... 1/5"}, 1),
    ],
)
def test_fatal_errors_are_not_hidden_by_a_final(event, returncode):
    assert (
        parse_events([event, *final_events()], PROOF, returncode)["status"]
        == "transport_error"
    )


@pytest.mark.parametrize(
    "status", ["indeterminate", "model_mismatch", "budget_exhausted"]
)
def test_recovery_never_resamples_an_unresolved_or_controlled_request(status):
    failure = {
        "status": status,
        "events_errors": [
            {"type": "error", "message": "unexpected status 502 Bad Gateway"},
            {
                "type": "turn.failed",
                "error": {"message": "unexpected status 502 Bad Gateway"},
            },
        ],
    }
    assert not retryable_transport_failure(failure)


@pytest.mark.parametrize("limit", [-1, True, 1.5, 21])
def test_recovery_limit_is_validated(limit):
    with pytest.raises(ValueError, match="max_transport_restarts"):
        RunConfig(max_transport_restarts=limit)


@pytest.mark.parametrize("change", ["condition", "version", "reference", "pin"])
def test_saved_incumbent_rejects_other_conditions_missing_versions_and_changed_references(
    tmp_path, change
):
    name, model, effort = "Core.InitsUpdatesComm", "gpt-6.1-sol", "max"
    pack = load_inputs()[name]
    source = ROOT / "results/harness/06_refactor_regression"
    config = deepcopy(read(source / "config.json"))
    config.update(provider="codex", conditions=[[model, effort]])
    key = fingerprint((name, model, effort, config["mode"]))
    result = deepcopy(read(source / "cells" / key / "result.json"))
    if change == "condition":
        result["effort"] = "low"
    version = next(iter(result["selected_evaluation"]["per_version"]))
    if change == "version":
        result["selected_evaluation"]["per_version"][version]["passed"] = False
    if change == "reference":
        result["selected_evaluation"]["per_version"][version]["reference"][
            "heartbeats_raw"
        ] += 1
    write_json(tmp_path / "config.json", config)
    write_json(tmp_path / "cells" / key / "result.json", result)
    if change == "pin":
        pins = freeze_incumbents(tmp_path, config, {name: pack})
        result["stop"] = {"kind": "changed"}
        write_json(tmp_path / "cells" / key / "result.json", result)
        with pytest.raises(ValueError, match="Frozen incumbent"):
            saved_incumbent({**config, "incumbent_sources": pins}, pack, model, effort)
    else:
        with pytest.raises(ValueError):
            freeze_incumbents(tmp_path, config, {name: pack})


@pytest.mark.skipif(
    shutil.which("lemex") is None, reason="Native Lemex is not installed"
)
def test_installed_lemex_recovers_503_and_truncated_stream_with_tool_history(tmp_path):
    requests = []
    errors = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(data)
                index = len(requests)
                if index == 1:
                    body = b'{"error":{"message":"temporary local gateway failure"}}'
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if index == 2:
                    item = {
                        "id": "tool_local",
                        "type": "function_call",
                        "call_id": "tool_local",
                        "name": "exec_command",
                        "arguments": json.dumps(
                            {"cmd": "echo local-retry-history", "max_output_tokens": 20}
                        ),
                    }
                else:
                    item = {
                        "id": "msg_local",
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {"type": "output_text", "text": PROOF, "annotations": []}
                        ],
                    }
                response = {
                    "id": f"resp_{index}",
                    "object": "response",
                    "status": "completed",
                    "output": [item],
                    "usage": {
                        "input_tokens": 200,
                        "input_tokens_details": {"cached_tokens": 0},
                        "output_tokens": 100,
                        "output_tokens_details": {"reasoning_tokens": 10},
                        "total_tokens": 300,
                    },
                }
                events = [
                    (
                        "response.created",
                        {
                            "type": "response.created",
                            "response": {
                                "id": f"resp_{index}",
                                "object": "response",
                                "status": "in_progress",
                            },
                        },
                    ),
                    (
                        "response.output_item.added",
                        {
                            "type": "response.output_item.added",
                            "output_index": 0,
                            "item": item,
                        },
                    ),
                    (
                        "response.output_item.done",
                        {
                            "type": "response.output_item.done",
                            "output_index": 0,
                            "item": item,
                        },
                    ),
                    (
                        "response.completed",
                        {"type": "response.completed", "response": response},
                    ),
                ]
                if index == 3:
                    events = events[:1]
                payload = "".join(
                    "event: " + kind + "\ndata: " + json.dumps(value) + "\n\n"
                    for kind, value in events
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header(
                    "Content-Length", str(len(payload) + (100 if index == 3 else 0))
                )
                self.end_headers()
                self.wfile.write(payload)
                self.wfile.flush()
                if index == 3:
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
            except Exception as exc:
                errors.append(str(exc))

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        system = tmp_path / "system.txt"
        system.write_text("Use the supplied shell tools and return the final proof.")
        final = tmp_path / "final.txt"
        argv = lemex.command(
            binary=shutil.which("lemex"),
            workspace=tmp_path,
            system_file=system,
            last_message=final,
            model=MODEL,
            effort="xhigh",
            mode="score_edges",
            catalog=Path.home() / ".lemex/models.json",
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            instructions="Use the supplied tools.",
        )
        argv[-1:-1] = ["-c", "features.enable_request_compression=false"]
        result = subprocess.run(
            argv,
            input="Check the proof using the shell, then return it.",
            cwd=tmp_path,
            env={**os.environ, "LEMEX_API_KEY": "local-test-only"},
            text=True,
            capture_output=True,
            timeout=30,
        )
        assert not errors
        assert result.returncode == 0, result.stderr[-2000:]
        assert len(requests) == 4
        assert all(
            r["model"] == MODEL and r["reasoning"]["effort"] == "xhigh"
            for r in requests
        )
        assert all(
            "temperature" not in r and "max_output_tokens" not in r for r in requests
        )
        assert any(
            item.get("type") == "function_call_output"
            and "local-retry-history" in item.get("output", "")
            for item in requests[-1]["input"]
        )
        events = [
            json.loads(line) for line in result.stdout.splitlines() if line.strip()
        ]
        parsed = parse_events(events, final.read_text(), result.returncode)
        assert parsed["status"] == "received"
        assert len(parsed["recovered_transport_errors"]) == 1
        assert parsed["usage_complete"] is False
        assert parsed["token_usage"]["output_tokens"] == 200
        assert (
            sum(
                e.get("item", {}).get("type") == "command_execution"
                and e["type"] == "item.completed"
                for e in events
            )
            == 1
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
