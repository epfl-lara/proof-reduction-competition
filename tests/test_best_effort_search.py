"""A complete theorem search through native Codex and a localhost-only server."""

from __future__ import annotations

import json
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from test_budget_tracking import NAME, run_worker, tracking_run  # noqa: F401

from proof_eval.evidence.io import read
from proof_eval.harness.agent import generate
from proof_eval.harness.audit import audit
from proof_eval.harness.config import RunConfig
from proof_eval.harness.reporting import report
from proof_eval.providers import codex

_native_identity = codex.cli_identity


def test_native_best_effort_search_restarts_preserves_proof_and_audits(
    tracking_run, monkeypatch  # noqa: F811 - imported pytest fixture
):
    """A recovered 500 must not end a cost search or replenish its allowance."""
    if not shutil.which("codex"):
        pytest.skip("Native Codex CLI unavailable")
    identity = _native_identity()
    if identity.get("response_usage_schema_version") != 2:
        pytest.skip("Native Codex request tracing unavailable")
    monkeypatch.setattr(codex, "cli_identity", lambda: identity)
    run = tracking_run(usd=0.025, timeout=None)
    requests = []
    errors = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                assert self.path == "/v1/responses"
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(body)
                index = len(requests)
                if index == 1:
                    payload = b'{"error":{"message":"temporary server error"}}'
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                else:
                    item = {
                        "id": f"msg_{index}",
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": run.saved["selected_proof"],
                                "annotations": [],
                            }
                        ],
                    }
                    events = [
                        {
                            "type": "response.created",
                            "response": {"id": f"resp_{index}"},
                        },
                        {
                            "type": "response.output_item.added",
                            "output_index": 0,
                            "item": item,
                        },
                        {
                            "type": "response.output_item.done",
                            "output_index": 0,
                            "item": item,
                        },
                        {
                            "type": "response.completed",
                            "response": {
                                "id": f"resp_{index}",
                                "status": "completed",
                                "output": [item],
                                "usage": {
                                    "input_tokens": 1000,
                                    "input_tokens_details": {"cached_tokens": 900},
                                    "output_tokens": 1000,
                                    "output_tokens_details": {"reasoning_tokens": 100},
                                    "total_tokens": 2000,
                                },
                            },
                        },
                    ]
                    payload = "".join(
                        "event: "
                        + event["type"]
                        + "\ndata: "
                        + json.dumps(event)
                        + "\n\n"
                        for event in events
                    ).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except Exception as error:
                errors.append(str(error))

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original_command = codex.command

    def local_command(**kwargs):
        kwargs["settings"] = {
            **kwargs["settings"],
            "model_provider": "local_search_test",
            "model_providers.local_search_test.name": "Local search test only",
            "model_providers.local_search_test.base_url": (
                f"http://127.0.0.1:{server.server_port}/v1"
            ),
            "model_providers.local_search_test.wire_api": "responses",
            "model_providers.local_search_test.requires_openai_auth": False,
            "model_providers.local_search_test.request_max_retries": 0,
            "model_providers.local_search_test.stream_max_retries": 1,
            "features.enable_request_compression": False,
        }
        return original_command(**kwargs)

    monkeypatch.setattr(codex, "command", local_command)
    try:
        result = run_worker(run, generate)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert not errors
    assert (
        RunConfig(
            output=run.output,
            budget_tracking=run.config["budget_tracking"],
            usage_policy=run.config["usage_policy"],
            budget_usd_per_problem=run.config["budget_usd_per_problem"],
        ).workers
        == 5
    )
    assert run.config["usage_policy"] == "best_effort"
    assert result["status"] == "complete"
    assert result["stop"]["kind"] == "cost_limit"
    assert len(result["attempts"]) >= 2
    assert len(requests) == len(result["attempts"]) + 1  # One native retry.
    assert all(request["model"] == run.model for request in requests)
    assert result["selected_proof"].strip() == run.saved["selected_proof"].strip()
    assert result["selected_evaluation"] == run.saved["selected_evaluation"]
    assert result["attempts"][1]["incumbent_proof"] == result["selected_proof"]
    first = result["generations"][0]
    last = result["generations"][-1]
    assert first["status"] == "received" and first["usage_complete"] is False
    assert first["structurally_valid"] and first["estimated_usage_complete"]
    assert last["status"] == "budget_exhausted"
    assert last["termination"] == "cost_limit"
    assert result["cost"]["status"] == "estimated_incomplete_usage"
    assert result["cost"]["complete_usage"] is False
    assert result["cost"]["total_usd"] == pytest.approx(
        0.01029 * len(result["attempts"])
    )
    assert result["cost"]["total_usd"] >= run.config["budget_usd_per_problem"]
    assert result["cost"]["unknown_attempt_indices"] == [0]
    for attempt in result["attempts"]:
        request = read(run.folder / f"attempt_{attempt['number']:02d}/request.json")
        assert request["timeout"] is None
        assert request["cost_budget"]["remaining_usd"] == pytest.approx(
            run.config["budget_usd_per_problem"]
            - (attempt["cost_before"]["total_usd"] or 0)
        )
    assert not (run.folder / "budget_started.json").exists()
    assert audit(run.output)["status"] == "passed"
    summary = report(run.output, run.config)["conditions"][0]
    assert summary["unknown_usage_calls"] == 1
    assert summary["cost"]["incomplete_usage_problems"] == [NAME]
    assert summary["cost"]["known_cost_problems"] == 1
    assert summary["cost"]["unknown_cost_problems"] == 0

    def forbidden(**kwargs):
        raise AssertionError("Completed cost searches cannot resample")

    request_count = len(requests)
    assert run_worker(run, forbidden) == result
    assert len(requests) == request_count
