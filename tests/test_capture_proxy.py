"""Training capture is attributed, streaming and durable without changing bodies."""

from __future__ import annotations

import gzip
import hashlib
import json
import socket
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from proof_eval.evidence.io import read, write_json
from proof_eval.providers import capture_proxy, lemex_local
from proof_eval.providers.capture_proxy import CaptureProxy, register_attempt


@contextmanager
def upstream(respond):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            calls.append(
                {"body": body, "headers": dict(self.headers), "path": self.path}
            )
            respond(self, body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def post(endpoint, body=b'{"input":"context"}', headers=None):
    return urlopen(
        Request(
            endpoint + "/responses",
            body,
            headers or {"Content-Type": "application/json"},
        ),
        timeout=5,
    )


def registration(proxy, task="theorem"):
    return register_attempt(
        proxy.endpoint,
        proxy.token,
        {"task": task, "attempt": "attempt_00", "model": lemex_local.MODEL},
    )


def records(root):
    return list(root.glob("attempts/*/requests/*"))


def test_stream_is_live_exact_attributed_and_terminal_durable(tmp_path):
    release = threading.Event()
    first = b'event: response.output_text.delta\ndata: {"type":"response.output_text.delta","delta":"hello"}\n\n'
    final = b'event: response.completed\ndata: {"type":"response.completed"}\n\n'

    def respond(handler, body):
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Set-Cookie", "private-cookie")
        handler.end_headers()
        handler.wfile.write(first)
        handler.wfile.flush()
        assert release.wait(5)
        # Exercise markers split across network writes.
        handler.wfile.write(final[:19])
        handler.wfile.flush()
        handler.wfile.write(final[19:])

    with upstream(respond) as (endpoint, calls):
        with CaptureProxy(tmp_path, endpoint) as proxy:
            route = registration(proxy)
            with post(
                route,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "secret-auth",
                    "X-Api-Key": "secret-key",
                    "Cookie": "secret-cookie",
                },
            ) as response:
                assert response.read(len(first)) == first
                assert len(calls) == 1
                request_folder = records(tmp_path)[0]
                assert (request_folder / "request.body").read_bytes() == calls[0][
                    "body"
                ]
                assert (request_folder / "response.body").read_bytes() == first
                release.set()
                assert response.read() == final
                assert read(request_folder / "terminal_step.json")[
                    "response_bytes"
                ] == len(first + final)
            # Handler closes after writing its final receipt.
            with urlopen(proxy.endpoint + "/_capture/health") as response:
                assert json.load(response)["healthy"] is True
    request_folder = records(tmp_path)[0]
    assert (request_folder / "response.body").read_bytes() == first + final
    receipt = read(request_folder / "receipt.json")
    assert receipt["status"] == "complete" and receipt["terminal_event"] is True
    assert receipt["response_sha256"] == hashlib.sha256(first + final).hexdigest()
    assert not any(
        k.lower() in {"authorization", "x-api-key", "cookie"}
        for k in calls[0]["headers"]
    )
    captured = b"".join(p.read_bytes() for p in tmp_path.rglob("*") if p.is_file())
    assert not any(
        s in captured
        for s in [b"secret-auth", b"secret-key", b"secret-cookie", b"private-cookie"]
    )


def test_concurrent_attempts_and_native_retries_keep_distinct_requests(tmp_path):
    def respond(handler, body):
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    with upstream(respond) as (endpoint, calls):
        with CaptureProxy(tmp_path, endpoint) as proxy:
            routes = [registration(proxy, task) for task in ("A", "B")]

            def call(index):
                body = json.dumps({"input": index}).encode()
                with post(routes[index % 2], body) as response:
                    assert response.read() == body

            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(call, range(4)))
    attempts = list(tmp_path.glob("attempts/*"))
    assert len(attempts) == 2 and len(calls) == 4
    assert {read(p / "registration.json")["task"] for p in attempts} == {"A", "B"}
    for attempt in attempts:
        requests = list((attempt / "requests").iterdir())
        assert len(requests) == 2
        assert all(read(p / "receipt.json")["status"] == "complete" for p in requests)


def test_compressed_request_bytes_and_encoding_are_unchanged_and_private(
    tmp_path, monkeypatch
):
    original = b'{"input":"exact evolving context"}'
    compressed = gzip.compress(original, mtime=0)

    def respond(handler, body):
        assert handler.headers["Content-Encoding"] == "gzip"
        assert gzip.decompress(body) == original
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(original)))
        handler.end_headers()
        handler.wfile.write(original)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Root-squashed scratch must not use post-create chmod")

    monkeypatch.setattr(capture_proxy.os, "chmod", forbidden)
    root = tmp_path / "new" / "private" / "capture"
    with upstream(respond) as (endpoint, calls):
        with CaptureProxy(root, endpoint) as proxy:
            route = registration(proxy)
            with post(
                route,
                compressed,
                {"Content-Type": "application/json", "Content-Encoding": "gzip"},
            ) as response:
                assert response.read() == original
    folder = records(root)[0]
    assert calls[0]["body"] == compressed
    assert (folder / "request.body").read_bytes() == compressed
    assert read(folder / "request.json")["headers"]["content-encoding"] == "gzip"
    for path in [root, *root.rglob("*")]:
        assert path.stat().st_mode & 0o777 == (0o700 if path.is_dir() else 0o600)


@pytest.mark.parametrize("sse", [False, True])
def test_interrupted_upstream_retains_partial_bytes_as_incomplete(tmp_path, sse):
    partial = b'data: {"delta":"unfinished"}\n\n' if sse else b'{"unfinished":'

    def respond(handler, body):
        handler.send_response(200)
        handler.send_header(
            "Content-Type", "text/event-stream" if sse else "application/json"
        )
        if not sse:
            handler.send_header("Content-Length", str(len(partial) + 50))
        handler.end_headers()
        handler.wfile.write(partial)
        handler.wfile.flush()
        handler.close_connection = True

    with upstream(respond) as (endpoint, calls):
        with CaptureProxy(tmp_path, endpoint) as proxy:
            route = registration(proxy)
            try:
                with post(route) as response:
                    response.read()
            except Exception as error:
                assert type(error).__name__ == "IncompleteRead"
    folder = records(tmp_path)[0]
    assert (folder / "response.body").read_bytes() == partial
    assert read(folder / "receipt.json")["status"] == "incomplete"
    assert len(calls) == 1


def test_upstream_error_is_captured_unchanged_without_retry(tmp_path):
    body = b'{"error":"busy"}'

    def respond(handler, _request):
        handler.send_response(503)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    with upstream(respond) as (endpoint, calls):
        with CaptureProxy(tmp_path, endpoint) as proxy:
            route = registration(proxy)
            with pytest.raises(HTTPError) as caught:
                post(route)
            assert caught.value.code == 503 and caught.value.read() == body
    folder = records(tmp_path)[0]
    assert len(calls) == 1
    assert read(folder / "response.json")["status"] == 503
    assert read(folder / "receipt.json")["status"] == "complete"


def test_native_disconnect_preserves_partial_response_and_does_not_retry(tmp_path):
    first = b'data: {"delta":"' + b"x" * (1024 * 1024) + b'"}\n\n'

    def respond(handler, _body):
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.end_headers()
        try:
            handler.wfile.write(first)
            handler.wfile.flush()
            time.sleep(0.05)
            handler.wfile.write(b"data: still running\n\n")
        except (BrokenPipeError, ConnectionResetError):
            pass

    with upstream(respond) as (endpoint, calls):
        with CaptureProxy(tmp_path, endpoint) as proxy:
            route = registration(proxy)
            address = capture_proxy.urlsplit(proxy.endpoint)
            connection = socket.create_connection(("127.0.0.1", address.port))
            path = capture_proxy.urlsplit(route).path + "/responses"
            connection.sendall(
                f"POST {path} HTTP/1.1\r\nHost: localhost\r\nContent-Length: 2\r\n\r\n{{}}".encode()
            )
            assert connection.recv(4096)
            connection.setsockopt(
                socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)
            )
            connection.close()
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                folders = records(tmp_path)
                if folders and (folders[0] / "receipt.json").exists():
                    break
                time.sleep(0.01)
            folder = records(tmp_path)[0]
            assert read(folder / "receipt.json")["status"] == "incomplete"
            assert (folder / "response.body").stat().st_size > 0
    assert len(calls) == 1


def test_client_cancellation_aborts_upstream_during_prefill(tmp_path):
    admitted = threading.Event()
    release = threading.Event()

    def respond(handler, _body):
        admitted.set()
        assert release.wait(5)
        try:
            handler.send_response(200)
            handler.end_headers()
            handler.wfile.write(b"late response")
        except (BrokenPipeError, ConnectionResetError):
            pass

    try:
        with upstream(respond) as (endpoint, calls):
            with CaptureProxy(tmp_path, endpoint) as proxy:
                route = registration(proxy)
                address = capture_proxy.urlsplit(proxy.endpoint)
                connection = socket.create_connection(("127.0.0.1", address.port))
                path = capture_proxy.urlsplit(route).path + "/responses"
                connection.sendall(
                    f"POST {path} HTTP/1.1\r\nHost: localhost\r\nContent-Length: 2\r\n\r\n{{}}".encode()
                )
                assert admitted.wait(2)
                connection.close()
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    folders = records(tmp_path)
                    if folders and (folders[0] / "receipt.json").exists():
                        break
                    time.sleep(0.01)
                folder = records(tmp_path)[0]
                assert read(folder / "receipt.json")["status"] == "incomplete"
                assert (folder / "response.body").read_bytes() == b""
                assert len(calls) == 1
                release.set()
    finally:
        release.set()


def test_progressive_body_fsync_does_not_wait_for_another_upstream_chunk(
    tmp_path, monkeypatch
):
    synced = threading.Event()
    original = capture_proxy.os.fsync

    def sync(fd):
        original(fd)
        synced.set()

    monkeypatch.setattr(capture_proxy.os, "fsync", sync)
    body = capture_proxy._ResponseBody(
        tmp_path / "body", 0.02, lambda: pytest.fail("sync failed")
    )
    try:
        body.write(b"partial SSE bytes while upstream is idle")
        assert synced.wait(2)
    finally:
        body.close()
    assert (
        tmp_path / "body"
    ).read_bytes() == b"partial SSE bytes while upstream is idle"


def test_capture_storage_failure_never_admits_uncaptured_upstream(
    tmp_path, monkeypatch
):
    def respond(handler, _body):
        pytest.fail("An uncaptured request reached upstream")

    with upstream(respond) as (endpoint, calls):
        with CaptureProxy(tmp_path, endpoint) as proxy:
            route = registration(proxy)

            def fail(*_args):
                raise OSError("storage unavailable")

            monkeypatch.setattr(capture_proxy, "_write_bytes", fail)
            with pytest.raises(HTTPError):
                post(route)
            with pytest.raises(HTTPError) as caught:
                urlopen(proxy.endpoint + "/_capture/health")
            assert caught.value.code == 503
            assert calls == []


def test_terminal_stream_fsync_failure_never_delivers_completion(tmp_path, monkeypatch):
    terminal = b'event: response.completed\ndata: {"type":"response.completed"}\n\n'

    def respond(handler, _body):
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.end_headers()
        handler.wfile.write(terminal)

    def fail(_body):
        raise OSError("response fsync failed")

    with upstream(respond) as (endpoint, _calls):
        with CaptureProxy(tmp_path, endpoint) as proxy:
            route = registration(proxy)
            monkeypatch.setattr(capture_proxy._ResponseBody, "sync", fail)
            with post(route) as response:
                assert response.read() == b""
            with pytest.raises(HTTPError) as caught:
                urlopen(proxy.endpoint + "/_capture/health")
            assert caught.value.code == 503
    folder = records(tmp_path)[0]
    assert (folder / "response.body").read_bytes() == terminal
    assert not (folder / "terminal_step.json").exists()
    assert read(folder / "receipt.json")["status"] == "incomplete"


def test_registration_private_and_upstream_restricted(tmp_path):
    for endpoint in [
        "https://127.0.0.1:80/v1",
        "http://example.org:80/v1",
        "http://user:secret@127.0.0.1:80/v1",
        "http://127.0.0.1:80/v1?key=secret",
    ]:
        with pytest.raises(ValueError):
            CaptureProxy(tmp_path, endpoint)
    with CaptureProxy(tmp_path, "http://127.0.0.1:8128/v1") as proxy:
        with pytest.raises(HTTPError) as caught:
            register_attempt(proxy.endpoint, "incorrect", {"task": "A"})
        assert caught.value.code == 403
        with pytest.raises(HTTPError) as caught:
            register_attempt(proxy.endpoint, proxy.token, {"Authorization": "secret"})
        assert caught.value.code == 400
        with pytest.raises(HTTPError) as caught:
            post(proxy.endpoint + "/a/" + "0" * 48 + "/v1")
        assert caught.value.code == 404


def test_native_capture_route_trace_and_control_credentials(tmp_path, monkeypatch):
    identity = {
        "home": str(tmp_path),
        "path": "/native",
        "catalog_path": str(tmp_path / "models.json"),
        "base_url": "http://127.0.0.1:8128/v1",
        "served_models": [lemex_local.MODEL],
    }
    monkeypatch.setattr(lemex_local, "cli_identity", lambda: identity)
    seen = {}
    monkeypatch.setenv("PROOF_LEMEX_CAPTURE_ENDPOINT", "http://127.0.0.1:18128")
    monkeypatch.setenv("PROOF_LEMEX_CAPTURE_REGISTRATION_TOKEN", "private-control")
    monkeypatch.setattr(
        capture_proxy,
        "register_attempt",
        lambda endpoint, token, metadata: seen.update(
            endpoint=endpoint, token=token, metadata=metadata
        )
        or endpoint + "/a/" + "a" * 48 + "/v1",
    )
    monkeypatch.setattr(
        lemex_local, "command", lambda **kw: seen.update(command=kw) or ["native"]
    )
    folder = tmp_path / "cell" / "attempt_00"
    workspace = folder / "workspace"
    workspace.mkdir(parents=True)
    write_json(folder / "request.json", {"messages": ["initial context"]})

    def execute(**kwargs):
        launch = kwargs["build"](
            workspace, folder / "system.txt", workspace / "final.txt", folder
        )
        assert launch.environment["CODEX_ROLLOUT_TRACE_ROOT"] == str(
            workspace / "rollout-traces"
        )
        assert not any(k.startswith("PROOF_LEMEX_CAPTURE_") for k in launch.environment)
        assert seen["command"]["base_url"].endswith("/a/" + "a" * 48 + "/v1")
        return {"status": "received"}

    monkeypatch.setattr(lemex_local.execution, "generate", execute)
    result = lemex_local.generate(
        model=lemex_local.MODEL,
        effort="xhigh",
        mode="score_edges",
        instructions="tools",
        session=SimpleNamespace(row={"name": "Theorem.A"}),
    )
    assert result["status"] == "received"
    assert seen["metadata"]["task"] == "Theorem.A"
    assert seen["metadata"]["attempt"] == "attempt_00"
    assert read(folder / "capture.json")["attribution"] == seen["metadata"]
    assert "private-control" not in (folder / "capture.json").read_text()


def test_explicit_local_capacity_namespaces_do_not_share_replica_slots(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(lemex_local.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(lemex_local.socket, "gethostname", lambda: "pod")
    monkeypatch.setenv("PROOF_LEMEX_LOCAL_CAPACITY_NAMESPACE", "engine0")
    with lemex_local._capacity(20):
        monkeypatch.setenv("PROOF_LEMEX_LOCAL_CAPACITY_NAMESPACE", "engine1")
        with lemex_local._capacity(20):
            assert (
                tmp_path / ".proof-arena/lemex-local-slots/pod/engine0/0.lock"
            ).exists()
            assert (
                tmp_path / ".proof-arena/lemex-local-slots/pod/engine1/0.lock"
            ).exists()
    monkeypatch.setenv("PROOF_LEMEX_LOCAL_CAPACITY_NAMESPACE", "../bad")
    with pytest.raises(ValueError):
        lemex_local._capacity(20)
