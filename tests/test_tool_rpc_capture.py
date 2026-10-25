"""Observable socket and durability contracts for complete host tool capture."""

import base64
import json
import os
import socket
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import proof_eval.harness.service as service_module
from proof_eval.harness.service import ProofToolService, ToolEvidenceError


class Session:
    def __init__(self, folder, dispatch=None):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.requests = []
        self.handler = dispatch

    def dispatch(self, request):
        self.requests.append(request)
        if self.handler is not None:
            return self.handler(request)
        return {"kind": request["op"], "value": "∀ α, α → α", "request": request}


def exchange(service, payload):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(5)
        client.connect(service.socket_path)
        client.sendall(payload)
        client.shutdown(socket.SHUT_WR)
        with client.makefile("rb") as response:
            return response.readline()


def records(service):
    return [json.loads(line) for line in service.ledger_path.read_text().splitlines()]


@pytest.fixture
def session_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return Session(tmp_path / "evidence"), workspace


def test_all_tool_operations_capture_exact_bytes_before_dispatch_and_delivery(
    session_workspace,
):
    session, workspace = session_workspace
    ops = [
        "check",
        "status",
        "goals",
        "profile",
        "search",
        "semantic_search",
        "web_search",
        "web_open",
        "read",
        "outline",
        "finish",
        "remember",
    ]
    with ProofToolService(session, workspace) as service:

        def dispatch(request):
            saved = records(service)[-1]
            assert saved["event"] == "request_started"
            assert saved["request"] == request
            return {"kind": request["op"], "unicode": "∀ x : ℝ, x = x"}

        session.handler = dispatch
        for op in ops:
            payload = (
                "  " + json.dumps({"op": op, "code": "theorem α := by simp"}) + "\n"
            ).encode()
            wire = exchange(service, payload)
            expected = (
                json.dumps(
                    {"kind": op, "unicode": "∀ x : ℝ, x = x"}, ensure_ascii=False
                ).encode()
                + b"\n"
            )
            assert wire == expected
            start, end = records(service)[-2:]
            assert start["event"] == "request_started"
            assert end["event"] == "response_completed"
            assert start["request_id"] == end["request_id"]
            assert base64.b64decode(start["request_wire_base64"]) == payload
            assert base64.b64decode(end["response_wire_base64"]) == wire
            assert end["response"] == json.loads(wire)
            assert end["elapsed_seconds"] >= 0
    assert service.ledger_path == session.folder / "tool_rpc.jsonl"
    assert not service.ledger_path.is_relative_to(workspace)
    assert len(records(service)) == 2 * len(ops)
    assert service.ledger_path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "payload, fragment",
    [
        (b'{"op": "status"', "incomplete"),
        (b"not-json\n", "JSONDecodeError"),
        (b"\xff\n", "UnicodeDecodeError"),
        (b'{"op": "status", "value": NaN}\n', "Non-finite"),
        (b" " * (1024 * 1024) + b"\n", "Oversized"),
    ],
)
def test_invalid_requests_are_recorded_without_dispatch(
    session_workspace, payload, fragment
):
    session, workspace = session_workspace
    with ProofToolService(session, workspace) as service:
        wire = exchange(service, payload)
    start, end = records(service)
    assert not session.requests
    assert start["request"] is None
    assert base64.b64decode(start["request_wire_base64"]) == payload
    assert end["response"]["kind"] == "tool_error"
    assert fragment in end["response"]["error"]
    assert base64.b64decode(end["response_wire_base64"]) == wire


@pytest.mark.parametrize(
    "exception", [ValueError("Unknown operation"), TimeoutError("deadline")]
)
def test_unknown_operation_and_dispatch_failure_have_complete_response_evidence(
    session_workspace, exception
):
    session, workspace = session_workspace

    def fail(_):
        raise exception

    session.handler = fail
    with ProofToolService(session, workspace) as service:
        wire = exchange(service, b'{"op":"unknown"}\n')
    start, end = records(service)
    assert start["request"] == {"op": "unknown"}
    assert end["response"] == {
        "kind": "tool_error",
        "error": f"{type(exception).__name__}: {exception}",
    }
    assert json.loads(wire) == end["response"]


def test_unserializable_success_is_an_explicit_recorded_tool_error(session_workspace):
    session, workspace = session_workspace
    session.handler = lambda _: {"kind": "status", "value": float("nan")}
    with ProofToolService(session, workspace) as service:
        wire = exchange(service, b'{"op":"status"}\n')
    assert json.loads(wire)["kind"] == "tool_error"
    assert records(service)[-1]["response"] == json.loads(wire)


def test_concurrent_requests_remain_correlated_complete_jsonl(session_workspace):
    session, workspace = session_workspace
    with ProofToolService(session, workspace) as service:
        with ThreadPoolExecutor(max_workers=12) as pool:
            payloads = [
                json.dumps({"op": "read", "number": n}).encode() + b"\n"
                for n in range(48)
            ]
            replies = list(
                pool.map(lambda payload: exchange(service, payload), payloads)
            )
    assert {json.loads(w)["request"]["number"] for w in replies} == set(range(48))
    saved = records(service)
    assert len(saved) == 96
    per_request = {}
    for record in saved:
        per_request.setdefault(record["request_id"], []).append(record)
    assert len(per_request) == 48
    assert all(
        [r["event"] for r in pair] == ["request_started", "response_completed"]
        for pair in per_request.values()
    )


@pytest.mark.parametrize("failing_sync", [1, 2])
def test_durability_failure_never_delivers_unrecorded_success(
    session_workspace, monkeypatch, failing_sync
):
    session, workspace = session_workspace
    service = ProofToolService(session, workspace)
    service.__enter__()
    fsync, calls = service_module.os.fsync, []

    def fail_sync(fd):
        calls.append(fd)
        if len(calls) >= failing_sync:
            raise OSError("evidence storage unavailable")
        return fsync(fd)

    with monkeypatch.context() as patch:
        patch.setattr(service_module.os, "fsync", fail_sync)
        assert exchange(service, b'{"op":"status"}\n') == b""
        assert exchange(service, b'{"op":"status"}\n') == b""
    assert len(session.requests) == failing_sync - 1
    with pytest.raises(ToolEvidenceError, match="Durable tool RPC capture failed"):
        service.__exit__()


def test_disconnected_client_completion_is_durable_and_drained(session_workspace):
    session, workspace = session_workspace
    entered, release, closed = threading.Event(), threading.Event(), threading.Event()

    def delayed(request):
        entered.set()
        assert release.wait(5)
        return {"kind": "read", "source": "α β γ"}

    session.handler = delayed
    service = ProofToolService(session, workspace)
    service.__enter__()
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(service.socket_path)
    client.sendall(b'{"op":"read"}\n')
    assert entered.wait(3)
    client.close()

    def close():
        service.__exit__()
        closed.set()

    closer = threading.Thread(target=close)
    closer.start()
    assert not closed.wait(0.1)
    release.set()
    closer.join(5)
    assert closed.is_set()
    assert [r["event"] for r in records(service)] == [
        "request_started",
        "response_completed",
    ]


def test_process_death_leaves_a_durable_started_rpc(tmp_path):
    source = """
import os, signal, socket, sys
from pathlib import Path
from proof_eval.harness.service import ProofToolService
class Session:
    folder=Path(sys.argv[1])/'evidence'
    def dispatch(self, request):
        os.kill(os.getpid(), signal.SIGKILL)
workspace=Path(sys.argv[1])/'workspace'
workspace.mkdir()
with ProofToolService(Session(), workspace) as service:
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
        client.connect(service.socket_path)
        client.sendall(b'{"op":"goals"}\\n')
        client.recv(1)
"""
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[1] / "src"))
    result = subprocess.run(
        [sys.executable, "-c", source, str(tmp_path)],
        env=environment,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == -9, result.stderr.decode()
    saved = [
        json.loads(s)
        for s in (tmp_path / "evidence/tool_rpc.jsonl").read_text().splitlines()
    ]
    assert len(saved) == 1
    assert saved[0]["event"] == "request_started"
    assert saved[0]["request"] == {"op": "goals"}


def test_independent_processes_can_append_to_the_same_theorem_ledger(tmp_path):
    source = """
import json, socket, sys
from pathlib import Path
from proof_eval.harness.service import ProofToolService
class Session:
    folder=Path(sys.argv[1])/'evidence'
    def dispatch(self, request):
        return {'kind':'read','number':request['number']}
workspace=Path(sys.argv[1])/sys.argv[2]
workspace.mkdir()
with ProofToolService(Session(), workspace) as service:
    for number in range(12):
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
            client.connect(service.socket_path)
            client.sendall(json.dumps({'op':'read','number':number}).encode()+b'\\n')
            with client.makefile('rb') as incoming:
                assert json.loads(incoming.readline())=={'kind':'read','number':number}
"""
    environment = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[1] / "src"))

    def run(prefix):
        return subprocess.run(
            [sys.executable, "-c", source, str(tmp_path), prefix],
            env=environment,
            capture_output=True,
            timeout=10,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ["workspace-a", "workspace-b"]))
    assert all(result.returncode == 0 for result in results), [
        result.stderr.decode() for result in results
    ]
    saved = [
        json.loads(line)
        for line in (tmp_path / "evidence/tool_rpc.jsonl").read_text().splitlines()
    ]
    assert len(saved) == 48
    assert len({record["service_id"] for record in saved}) == 2
    assert len({record["request_id"] for record in saved}) == 24


def test_broad_workspace_keeps_capture_outside_its_writable_tree(tmp_path):
    session = Session(tmp_path)
    with ProofToolService(session, tmp_path) as service:
        assert not service.ledger_path.resolve().is_relative_to(tmp_path.resolve())
        assert json.loads(exchange(service, b'{"op":"status"}\n'))["kind"] == "status"
    assert len(records(service)) == 2
