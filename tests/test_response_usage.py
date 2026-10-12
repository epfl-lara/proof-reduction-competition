"""Real native accounting against localhost failures; no paid requests."""

from __future__ import annotations

import json
import os
import shutil
import socket
import threading
from contextlib import nullcontext
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from proof_eval.evidence.io import read, write_json
from proof_eval.harness.tracking import stop_decision
from proof_eval.providers import codex
from proof_eval.providers.costs import CostConfig, generations_cost
from proof_eval.providers.events import parse_events
from proof_eval.providers.response_usage import (
    SCHEMA_VERSION,
    TRACE_DIRECTORY,
    audit_usage,
    collect_usage,
    reconcile_usage,
)
from proof_eval.providers.retries import retryable_transport_failure

MODEL = "gpt-6-luna"
PROOF = "theorem local_usage : True := by trivial"
USAGE = dict(
    input_tokens=200,
    cached_input_tokens=20,
    cache_write_input_tokens=0,
    output_tokens=100,
    reasoning_output_tokens=10,
)


def response(index: int) -> list[dict]:
    item = {
        "id": f"msg_{index}",
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": PROOF, "annotations": []}],
    }
    return [
        {"type": "response.created", "response": {"id": f"resp_{index}"}},
        {"type": "response.output_item.added", "output_index": 0, "item": item},
        {"type": "response.output_item.done", "output_index": 0, "item": item},
        {
            "type": "response.completed",
            "response": {
                "id": f"resp_{index}",
                "status": "completed",
                "output": [item],
                "usage": {
                    "input_tokens": 200,
                    "output_tokens": 100,
                    "input_tokens_details": {"cached_tokens": 20},
                    "output_tokens_details": {"reasoning_tokens": 10},
                    "total_tokens": 300,
                },
            },
        },
    ]


@pytest.fixture
def native_run(tmp_path, monkeypatch):
    if not shutil.which("codex"):
        pytest.skip("Native Codex unavailable")
    identity = codex.cli_identity()
    if identity.get("response_usage_schema_version") not in (1, 2):
        pytest.skip("Native Codex request tracing unavailable")
    original_command = codex.command

    def run(scenario):
        requests = []
        errors = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                try:
                    data = json.loads(
                        self.rfile.read(int(self.headers["Content-Length"]))
                    )
                    requests.append(data)
                    index = len(requests)
                    if index == 1 and scenario in ("http500", "http503", "retry_guard"):
                        body = b'{"error":{"message":"temporary server error"}}'
                        self.send_response(503 if scenario == "http503" else 500)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return
                    events = response(index)
                    if index == 1 and scenario in ("late_capacity", "compaction"):
                        item = {
                            "id": "call_local",
                            "call_id": "call_local",
                            "type": "function_call",
                            "name": "exec_command",
                            "arguments": json.dumps({"cmd": "true"}),
                        }
                        events[1]["item"] = events[2]["item"] = item
                        events[3]["response"]["output"] = [item]
                        if scenario == "compaction":
                            events[3]["response"]["usage"].update(
                                input_tokens=20000, total_tokens=20100
                            )
                    if scenario == "compaction" and any(
                        item.get("type") == "compaction_trigger"
                        for item in data["input"]
                    ):
                        item = {
                            "id": "cmp_local",
                            "type": "compaction",
                            "encrypted_content": "local_compaction",
                        }
                        events[1]["item"] = events[2]["item"] = item
                        events[3]["response"]["output"] = [item]
                        events[3]["response"].pop("usage")
                    if (
                        index == 1 and scenario in ("capacity", "partial_capacity")
                    ) or (index == 2 and scenario == "late_capacity"):
                        failed = {
                            "type": "response.failed",
                            "response": {
                                "error": {
                                    "code": "server_is_overloaded",
                                    "message": "overloaded",
                                }
                            },
                        }
                        events = (
                            events[:-1] + [failed]
                            if scenario == "partial_capacity"
                            else [failed]
                        )
                    disconnected = index == 1 and scenario == "disconnect"
                    if disconnected:
                        events = events[:1]
                    body = "".join(
                        "event: " + e["type"] + "\ndata: " + json.dumps(e) + "\n\n"
                        for e in events
                    ).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header(
                        "Content-Length", str(len(body) + (100 if disconnected else 0))
                    )
                    self.end_headers()
                    self.wfile.write(body)
                    self.wfile.flush()
                    if disconnected:
                        self.close_connection = True
                        self.connection.shutdown(socket.SHUT_RDWR)
                except Exception as error:
                    errors.append(str(error))

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def command(**kwargs):
            kwargs["settings"] = {
                **kwargs["settings"],
                "model_provider": "local_usage_test",
                "model_providers.local_usage_test.name": "Local usage test only",
                "model_providers.local_usage_test.base_url": f"http://127.0.0.1:{server.server_port}/v1",
                "model_providers.local_usage_test.wire_api": "responses",
                "model_providers.local_usage_test.requires_openai_auth": False,
                "model_providers.local_usage_test.request_max_retries": 0,
                "model_providers.local_usage_test.stream_max_retries": 1,
                "features.enable_request_compression": False,
            }
            if scenario == "compaction":
                kwargs["settings"].update(
                    {
                        "model_auto_compact_token_limit": 15000,
                        "model_providers.local_usage_test.capabilities.remote_compaction": "v2",
                        "features.token_budget.enabled": False,
                    }
                )
            return original_command(**kwargs)

        monkeypatch.setattr(codex, "command", command)
        source = tmp_path / "source"
        source.mkdir(exist_ok=True)
        folder = tmp_path / scenario
        guard = (
            {
                "kind": "native_weighted_tokens",
                "remaining_usd": 3.0,
                "limit_tokens": 100,
                "prefill_token_weight": 0.2,
                "sampling_token_weight": 1.0,
                "reminder_at_remaining_tokens": [10],
            }
            if scenario in ("guard", "retry_guard")
            else None
        )
        try:
            generation = codex.generate(
                folder=folder,
                messages=[
                    {"role": "system", "content": "Return the requested theorem."},
                    {"role": "user", "content": PROOF},
                ],
                model=MODEL,
                effort="max",
                mode="score_edges",
                session=SimpleNamespace(best_code=PROOF),
                context={"source_projects": {"local": str(source)}},
                expected_cli=identity,
                instructions="Return the requested theorem.",
                tool_service=lambda *_: nullcontext(),
                timeout=25,
                cost_budget=guard,
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        assert not errors
        assert requests
        assert all(
            r["model"] == MODEL and r["reasoning"]["effort"] == "max" for r in requests
        )
        assert all(
            "temperature" not in r and "max_output_tokens" not in r for r in requests
        )
        events = [
            json.loads(line)
            for line in (folder / "events.jsonl").read_text().splitlines()
        ]
        parsed = parse_events(
            events, generation.get("content", ""), generation.get("returncode", 0)
        )
        audited = audit_usage(folder, events, MODEL, parsed)
        for key in ("token_usage", "usage_complete", "response_usage_sha256"):
            assert audited.get(key) == generation.get(key)
        return generation, read(folder / "response_usage.json"), folder, events

    return run


@pytest.mark.parametrize("scenario", ["http500", "http503"])
def test_recovered_server_errors_do_not_invent_zero_spending(native_run, scenario):
    generation, evidence, _, _ = native_run(scenario)
    assert generation["status"] == "received"
    assert generation["usage_complete"] is False
    assert generation["token_usage"] == USAGE
    assert [r["status"] for r in evidence["requests"]] == ["unknown", "completed"]
    assert generation["recovered_transport_errors"]
    cost = generations_cost(CostConfig(MODEL, "max"), [generation])
    assert cost["total_usd"] is None
    assert (
        stop_decision(
            {
                "provider": "codex",
                "budget_tracking": "cost",
                "budget_usd_per_problem": 3.0,
            },
            generation,
            cost,
            unavailable=False,
            round_number=0,
            time_remaining=None,
        )["kind"]
        == "unknown_usage"
    )


def test_capacity_refusal_is_known_zero_and_retryable_without_model_substitution(
    native_run,
):
    generation, evidence, _, _ = native_run("capacity")
    assert generation["status"] == "transport_error"
    assert evidence["complete"] is True
    assert all(value == 0 for value in generation["token_usage"].values())
    assert retryable_transport_failure(generation)
    cost = generations_cost(CostConfig(MODEL, "max"), [generation])
    assert cost["total_usd"] == 0
    assert (
        stop_decision(
            {
                "provider": "codex",
                "budget_tracking": "cost",
                "max_transport_restarts": 2,
            },
            generation,
            cost,
            unavailable=False,
            round_number=0,
            time_remaining=None,
        )
        is None
    )


@pytest.mark.parametrize("scenario", ["disconnect", "partial_capacity"])
def test_interrupted_responses_remain_unknown(native_run, scenario):
    generation, evidence, _, _ = native_run(scenario)
    assert generation["usage_complete"] is False
    assert evidence["unknown_request_ids"]
    cost = generations_cost(CostConfig(MODEL, "max"), [generation])
    assert cost["total_usd"] is None
    assert (
        stop_decision(
            {
                "provider": "codex",
                "budget_tracking": "cost",
                "max_transport_restarts": 2,
            },
            generation,
            cost,
            unavailable=False,
            round_number=0,
            time_remaining=None,
        )["kind"]
        == "unknown_usage"
    )


@pytest.mark.parametrize("scenario", ["guard", "retry_guard"])
def test_native_budget_stop_preserves_usage_missing_from_exec_terminal(
    native_run, scenario
):
    generation, evidence, _, events = native_run(scenario)
    assert generation["status"] == "budget_exhausted"
    assert generation["termination"] == "cost_limit"
    assert not any(e["type"] == "turn.completed" for e in events)
    assert evidence["complete"] is (scenario == "guard")
    assert generation["token_usage"] == USAGE
    cost = generations_cost(CostConfig(MODEL, "max"), [generation])
    assert (cost["total_usd"] is not None) is (scenario == "guard")


def test_late_capacity_failure_keeps_previous_completed_response_cost(native_run):
    generation, evidence, _, _ = native_run("late_capacity")
    assert generation["status"] == "transport_error"
    assert generation["usage_complete"] is True
    assert generation["token_usage"] == USAGE
    assert [r["status"] for r in evidence["requests"]] == ["completed", "rejected"]
    assert generations_cost(CostConfig(MODEL, "max"), [generation])["total_usd"] > 0


@pytest.mark.parametrize("change", ["counters", "terminal"])
def test_usage_audit_detects_changed_counters_and_missing_terminal_trace(
    native_run, change
):
    generation, evidence, folder, events = native_run("success")
    assert (
        audit_usage(Path(os.path.relpath(folder)), events, MODEL, generation)
        == generation
    )
    if change == "counters":
        response = next(
            p
            for p in evidence["files"]
            if "/payloads/" in p and read(folder / p).get("token_usage")
        )
        path = folder / response
        payload = read(path)
        payload["token_usage"]["output_tokens"] += 1
        path.write_text(json.dumps(payload))
    else:
        path = folder / next(p for p in evidence["files"] if p.endswith("trace.jsonl"))
        path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n")
    with pytest.raises(ValueError, match="usage evidence changed"):
        audit_usage(folder, events, MODEL, generation)


def test_legacy_reconnect_accounting_is_unchanged():
    events = [
        {
            "type": "error",
            "message": "Reconnecting... 1/5 (unexpected status 503 Service Unavailable)",
        },
        {"type": "item.completed", "item": {"type": "agent_message", "text": PROOF}},
        {"type": "turn.completed", "usage": USAGE},
    ]
    parsed = parse_events(events, PROOF, 0)
    assert parsed["usage_complete"] is False
    assert generations_cost(CostConfig(MODEL, "max"), [parsed])["total_usd"] is None


def test_native_compaction_retains_responses_before_and_after_it(native_run):
    generation, evidence, _, _ = native_run("compaction")
    assert generation["status"] == "received"
    assert generation["usage_complete"] is False
    assert generation["structurally_valid"] is True
    assert generation["estimated_usage_complete"] is True
    assert [request["kind"] for request in evidence["requests"]] == [
        "inference",
        "compaction",
        "inference",
    ]
    assert generation["token_usage"] == {
        **USAGE,
        "input_tokens": 20200,
        "cached_input_tokens": 40,
        "output_tokens": 200,
        "reasoning_output_tokens": 20,
    }
    assert evidence["usage_estimates"][0]["kind"] == "compaction"
    assert len(evidence["unknown_request_ids"]) == 1


@pytest.fixture
def saved_trace(tmp_path):
    """Representative native request/compaction evidence without a CLI or network."""
    folder = tmp_path / "attempt"
    trace = folder / TRACE_DIRECTORY / "trace-local"
    write_json(
        trace / "manifest.json",
        {
            "schema_version": 1,
            "root_thread_id": "thread-local",
            "rollout_id": "rollout-local",
            "raw_event_log": "trace.jsonl",
        },
    )
    rows = []

    def append(kind, **payload):
        rows.append(
            {
                "schema_version": 1,
                "seq": len(rows) + 1,
                "rollout_id": "rollout-local",
                "thread_id": "thread-local",
                "payload": {"type": kind, **payload},
            }
        )
        (trace / "trace.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows)
        )

    def payload(name, data):
        path = "payloads/" + name + ".json"
        write_json(trace / path, data)
        return {"path": path}

    def request(call_id, *, compact=False):
        prefix = "compaction_request" if compact else "inference"
        id_key = "compaction_request_id" if compact else "inference_call_id"
        request_data = {"model": MODEL, "input": [{"text": "π" * 20}]}
        append(
            prefix + "_started",
            **{id_key: call_id},
            model=MODEL,
            request_payload=payload(call_id + "-request", request_data),
        )
        return request_data

    def completed(call_id, *, compact=False, usage=USAGE):
        prefix = "compaction_request" if compact else "inference"
        id_key = "compaction_request_id" if compact else "inference_call_id"
        body = {"output_items": [{"type": "compaction", "encrypted_content": "abc"}]}
        extra = {}
        if not compact:
            body["response_id"] = call_id + "-response"
            extra["response_id"] = body["response_id"]
        if usage is not None:
            body["token_usage"] = usage
        append(
            prefix + "_completed",
            **{id_key: call_id},
            **extra,
            response_payload=payload(call_id + "-response", body),
        )
        return body

    events = [{"type": "thread.started", "thread_id": "thread-local"}]
    return SimpleNamespace(
        folder=folder,
        trace=trace,
        append=append,
        payload=payload,
        request=request,
        completed=completed,
        events=events,
    )


def test_compaction_retains_all_reported_usage_and_hashes_estimated_evidence(
    saved_trace,
):
    trace = saved_trace
    trace.request("before")
    trace.completed("before")
    trace.request("compact", compact=True)
    trace.completed("compact", compact=True, usage=None)
    trace.append(
        "compaction_installed",
        checkpoint_payload=trace.payload("checkpoint", {"replacement_history": []}),
    )
    trace.request("after")
    trace.completed("after")
    trace.append("rollout_ended")
    total = {key: value * 2 for key, value in USAGE.items()}
    trace.events.append({"type": "turn.completed", "usage": total})
    generation = reconcile_usage(
        trace.folder, trace.events, MODEL, {"status": "received"}
    )
    record = read(trace.folder / "response_usage.json")
    assert generation["response_usage_schema_version"] == SCHEMA_VERSION
    assert generation["usage_complete"] is False
    assert generation["token_usage"] == total
    assert generation["structurally_valid"] is True
    assert generation["estimated_usage_complete"] is True
    assert record["unknown_request_ids"] == ["compact"]
    assert len(record["files"]) == 9
    estimate = generation["usage_estimates"][0]
    assert estimate["basis"] == "neighboring_reported_context_tokens"
    assert estimate["evidence"]["input"]["call_id"] == "before"
    assert estimate["evidence"]["output"]["call_id"] == "after"
    for field, expected in (
        ("input_tokens", USAGE["input_tokens"] + USAGE["output_tokens"]),
        ("output_tokens", USAGE["input_tokens"]),
    ):
        assert estimate["token_usage"][field] == expected
        assert generation["estimated_token_usage"][field] == total[field] + expected
    assert audit_usage(trace.folder, trace.events, MODEL, generation) == generation
    path = trace.trace / "payloads/compact-response.json"
    changed = read(path)
    changed["output_items"][0]["encrypted_content"] = "modified"
    write_json(path, changed)
    with pytest.raises(ValueError, match="usage evidence changed"):
        audit_usage(trace.folder, trace.events, MODEL, generation)


def test_compaction_without_neighbor_counters_uses_explicit_json_size_fallback(
    saved_trace,
):
    trace = saved_trace
    request_body = trace.request("compact", compact=True)
    response_body = trace.completed("compact", compact=True, usage=None)
    trace.append("rollout_ended")
    record = collect_usage(trace.folder, trace.events, MODEL)
    estimate = record["usage_estimates"][0]
    assert estimate["basis"] == "canonical_json_utf8_bytes_divided_by_four_uncached"
    for field, body in (
        ("input_tokens", request_body),
        ("output_tokens", response_body),
    ):
        encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
        assert estimate["token_usage"][field] == (len(encoded) + 3) // 4
    assert record["estimated_usage_complete"] is True
    assert record["complete"] is False


def test_failed_requests_preserve_unknown_ids_and_explicit_zero_assumption(saved_trace):
    trace = saved_trace
    trace.request("failed")
    trace.append(
        "inference_failed",
        inference_call_id="failed",
        error="temporary server error",
        partial_response_payload=None,
    )
    trace.request("completed")
    trace.completed("completed")
    trace.append("rollout_ended")
    trace.events.append({"type": "turn.completed", "usage": USAGE})
    record = collect_usage(trace.folder, trace.events, MODEL)
    assert record["complete"] is False
    assert record["estimated_usage_complete"] is True
    assert record["unknown_request_ids"] == ["failed"]
    assert record["token_usage"] == record["estimated_token_usage"] == USAGE
    assert record["usage_estimates"][0]["basis"] == (
        "failed_inference_without_partial_output_assumed_zero"
    )


def test_partial_response_estimate_preserves_evidence_and_reported_counters(
    saved_trace,
):
    trace = saved_trace
    trace.request("partial")
    trace.append(
        "inference_failed",
        inference_call_id="partial",
        error="stream disconnected before completion",
        partial_response_payload=trace.payload(
            "partial", {"token_usage": None, "output_items": [{"text": "partial"}]}
        ),
    )
    trace.request("completed")
    trace.completed("completed")
    trace.append("rollout_ended")
    record = collect_usage(trace.folder, trace.events, MODEL)
    assert record["complete"] is False
    assert record["estimated_usage_complete"] is True
    assert record["token_usage"] == USAGE
    assert record["estimated_token_usage"]["input_tokens"] > USAGE["input_tokens"]
    assert record["estimated_token_usage"]["output_tokens"] > USAGE["output_tokens"]
    assert any(path.endswith("payloads/partial.json") for path in record["files"])


def test_reported_failed_response_counters_are_preserved_without_estimation(
    saved_trace,
):
    trace = saved_trace
    trace.request("failed")
    trace.append(
        "inference_failed",
        inference_call_id="failed",
        error="stream disconnected before completion",
        partial_response_payload=trace.payload(
            "partial", {"token_usage": USAGE, "output_items": [{"text": "partial"}]}
        ),
    )
    trace.request("completed")
    trace.completed("completed")
    trace.append("rollout_ended")
    trace.events.append({"type": "turn.completed", "usage": USAGE})
    record = collect_usage(trace.folder, trace.events, MODEL)
    assert record["complete"] is True
    assert record["estimated_usage_complete"] is True
    assert record["token_usage"] == {key: value * 2 for key, value in USAGE.items()}
    assert record["estimated_token_usage"] == record["token_usage"]
    assert record["usage_estimates"] == []


@pytest.mark.parametrize("damage", ["truncated", "malformed", "mismatch", "started"])
def test_invalid_or_unfinished_trace_cannot_supply_complete_estimates(
    saved_trace, damage
):
    trace = saved_trace
    trace.request("completed")
    trace.completed("completed")
    if damage == "started":
        trace.request("unfinished")
    if damage != "truncated":
        trace.append("rollout_ended")
    if damage == "malformed":
        with (trace.trace / "trace.jsonl").open("a") as stream:
            stream.write("{bad json\n")
    if damage == "mismatch":
        trace.events.append(
            {"type": "turn.completed", "usage": {**USAGE, "output_tokens": 1000}}
        )
    record = collect_usage(trace.folder, trace.events, MODEL)
    assert record["complete"] is False
    assert record["estimated_usage_complete"] is False
    assert record["token_usage"] == USAGE
    assert record["structurally_valid"] is (damage == "started")


def test_compaction_with_complete_native_counters_does_not_need_an_estimate(
    saved_trace,
):
    trace = saved_trace
    trace.request("normal")
    trace.completed("normal")
    trace.request("compact", compact=True)
    trace.completed("compact", compact=True)
    trace.append("rollout_ended")
    trace.events.append({"type": "turn.completed", "usage": USAGE})
    record = collect_usage(trace.folder, trace.events, MODEL)
    assert record["complete"] is True
    assert record["usage_estimates"] == []
    assert record["token_usage"] == {key: value * 2 for key, value in USAGE.items()}


def test_schema_one_compaction_rebuild_keeps_historical_stop_and_fingerprint(
    saved_trace,
):
    trace = saved_trace
    trace.request("before")
    trace.completed("before")
    trace.request("compact", compact=True)
    trace.completed("compact", compact=True, usage=None)
    trace.request("after")
    trace.completed("after")
    trace.append("rollout_ended")
    generation = reconcile_usage(
        trace.folder, trace.events, MODEL, {"status": "received"}, schema_version=1
    )
    record = read(trace.folder / "response_usage.json")
    assert generation["response_usage_schema_version"] == 1
    assert record["reason"] == "Compaction usage is not covered by inference tracing"
    assert "token_usage" not in record
    assert "estimated_token_usage" not in generation
    assert len(record["files"]) == 3
    assert audit_usage(trace.folder, trace.events, MODEL, generation) == generation
