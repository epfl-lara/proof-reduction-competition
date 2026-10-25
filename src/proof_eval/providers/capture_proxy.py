"""Attributed, durable capture of local inference request and response bodies.

The proxy never retries or edits inference bodies. Its private registration
credential is host-only; native agents receive only an opaque attempt URL.
"""

from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import os
import re
import secrets
import select
import socket
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from proof_eval.evidence.io import now, write_json

_PREFIX = "PROOF_LEMEX_CAPTURE_"
_REQUEST_HEADERS = frozenset(
    {"content-type", "content-encoding", "accept", "user-agent"}
)
_RESPONSE_HEADERS = frozenset(
    {"content-type", "content-length", "content-encoding", "date", "x-request-id"}
)
_ROUTE = re.compile(
    r"^/a/([0-9a-f]{48})/v1(/(?:responses|chat/completions|completions|models)(?:/[A-Za-z0-9_-]+)?)$"
)
_TERMINAL_TYPES = frozenset(
    {
        "response.completed",
        "response.failed",
        "response.incomplete",
        "response.cancelled",
    }
)


def _local_url(value: str, *, origin_only: bool = False):
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.port is None
        or (origin_only and parsed.path not in ("", "/"))
        or (not origin_only and parsed.path.rstrip("/") != "/v1")
    ):
        raise ValueError("Capture endpoints must be explicit HTTP IPv4 loopback URLs")
    return parsed


def _private_directory(path: Path) -> None:
    """Create private directories without post-create chmod on root-squashed NFS."""
    try:
        path.mkdir(mode=0o700)
    except FileNotFoundError:
        _private_directory(path.parent)
        _private_directory(path)
    except FileExistsError:
        if not path.is_dir():
            raise


def _write_bytes(path: Path, value: bytes) -> None:
    _private_directory(path.parent)
    fd, temporary = tempfile.mkstemp(prefix=".capture-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _terminal_event(event: bytes) -> bool:
    for line in event.splitlines():
        if line.startswith(b"event:") and line[6:].strip().decode() in _TERMINAL_TYPES:
            return True
        if not line.startswith(b"data:"):
            continue
        data = line[5:].strip()
        if data == b"[DONE]":
            return True
        try:
            if json.loads(data).get("type") in _TERMINAL_TYPES:
                return True
        except (ValueError, AttributeError, UnicodeDecodeError):
            pass
    return False


class _ResponseBody:
    """Unbuffered stream with bounded durability even during an idle upstream."""

    def __init__(self, path: Path, interval: float, failed) -> None:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        self._stream = os.fdopen(descriptor, "wb", buffering=0)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._dirty = False
        self._error: OSError | None = None

        def tick():
            while not self._stop.wait(interval):
                try:
                    self.sync()
                except OSError as error:
                    self._error = error
                    failed()
                    break

        self._thread = threading.Thread(target=tick, daemon=True)
        self._thread.start()

    def write(self, value: bytes) -> None:
        with self._lock:
            if self._error is not None:
                raise self._error
            remaining = memoryview(value)
            while remaining:
                written = self._stream.write(remaining)
                if not written:
                    raise OSError("Capture body write made no progress")
                remaining = remaining[written:]
            self._dirty = True

    def sync(self) -> None:
        with self._lock:
            if self._error is not None:
                raise self._error
            if self._dirty:
                os.fsync(self._stream.fileno())
                self._dirty = False

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        try:
            self.sync()
        finally:
            self._stream.close()


class _CancelOnDisconnect:
    """Do not leave GPU work running after its native caller is terminated."""

    def __init__(self, downstream: socket.socket, upstream: socket.socket) -> None:
        self._stop = threading.Event()

        def watch():
            while not self._stop.wait(0.1):
                try:
                    ready, _, _ = select.select([downstream], [], [], 0)
                    if not ready or downstream.recv(1, socket.MSG_PEEK):
                        continue
                except OSError:
                    pass
                try:
                    upstream.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                return

        self._thread = threading.Thread(target=watch, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1)


def register_attempt(endpoint: str, token: str, metadata: dict) -> str:
    """Register host-owned attribution and return its opaque native base URL."""
    _local_url(endpoint, origin_only=True)
    request = Request(
        endpoint.rstrip("/") + "/_capture/register",
        json.dumps(metadata, ensure_ascii=False, allow_nan=False).encode(),
        {"Content-Type": "application/json", "X-Capture-Registration-Key": token},
    )
    with urlopen(request, timeout=15) as response:
        record = json.load(response)
    if not re.fullmatch(r"[0-9a-f]{48}", record.get("route", "")):
        raise ValueError("Capture registration returned an invalid route")
    return endpoint.rstrip("/") + "/a/" + record["route"] + "/v1"


class CaptureProxy:
    """A per-engine local recorder, used as a context manager by a launcher.

    ``environment`` belongs only on the host harness process. The adapter strips
    its registration credential before launching the native agent. Request and
    terminal model-step bytes are fsynced before delivery; intermediate SSE bytes
    are flushed progressively and fsynced at most ``sync_interval_seconds`` apart.
    Interrupted responses retain their bodies and an explicit incomplete receipt.
    """

    def __init__(
        self,
        root: Path,
        upstream: str,
        *,
        port: int = 0,
        sync_interval_seconds: float = 1.0,
        upstream_timeout_seconds: float = 7200,
    ) -> None:
        self.root = Path(root).resolve()
        self.upstream = _local_url(upstream)
        if not 0 <= port <= 65535 or sync_interval_seconds <= 0:
            raise ValueError("Invalid capture listener or synchronization interval")
        self.port = port
        self.sync_interval_seconds = sync_interval_seconds
        self.upstream_timeout_seconds = upstream_timeout_seconds
        self.token = secrets.token_hex(32)
        self._lock = threading.Lock()
        self._routes: set[str] = set()
        self._fatal = False
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def endpoint(self) -> str:
        if self._server is None:
            raise RuntimeError("Capture proxy has not started")
        return f"http://127.0.0.1:{self._server.server_port}"

    @property
    def environment(self) -> dict[str, str]:
        return {
            _PREFIX + "ENDPOINT": self.endpoint,
            _PREFIX + "REGISTRATION_TOKEN": self.token,
        }

    def __enter__(self) -> CaptureProxy:
        if self._server is not None:
            raise RuntimeError("Capture proxy is already running")
        _private_directory(self.root)
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_args):
                pass

            def do_POST(self):
                self._handle()

            def do_GET(self):
                self._handle()

            def do_DELETE(self):
                self._handle()

            def _json(self, status, record):
                body = json.dumps(record).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
                self.close_connection = True

            def _body(self, limit=128 * 1024 * 1024):
                if self.headers.get("Transfer-Encoding"):
                    raise ValueError("Chunked inference requests are unsupported")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 <= length <= limit:
                    raise ValueError("Invalid request body size")
                body = self.rfile.read(length)
                if len(body) != length:
                    raise ValueError("Incomplete request body")
                return body

            def _handle(self):
                self.close_connection = True
                if self.path == "/_capture/health":
                    self._json(
                        503 if owner._fatal else 200, {"healthy": not owner._fatal}
                    )
                    return
                if owner._fatal:
                    self._json(503, {"error": "capture storage unavailable"})
                    return
                if self.path == "/_capture/register" and self.command == "POST":
                    supplied = self.headers.get("X-Capture-Registration-Key", "")
                    if not hmac.compare_digest(supplied, owner.token):
                        self._json(403, {"error": "registration denied"})
                        return
                    try:
                        metadata = json.loads(self._body(1024 * 1024))
                        allowed = {
                            "provider",
                            "model",
                            "effort",
                            "task",
                            "cell",
                            "attempt",
                            "attempt_directory",
                            "request_sha256",
                        }
                        if not isinstance(metadata, dict) or set(metadata) - allowed:
                            raise ValueError("Invalid attribution metadata")
                        route = secrets.token_hex(24)
                        _private_directory(owner.root / "attempts" / route)
                        write_json(
                            owner.root / "attempts" / route / "registration.json",
                            metadata,
                        )
                        with owner._lock:
                            owner._routes.add(route)
                        self._json(200, {"route": route})
                    except OSError:
                        owner._fatal = True
                        self._json(503, {"error": "capture storage unavailable"})
                    except (ValueError, TypeError):
                        self._json(400, {"error": "invalid registration"})
                    return
                matched = _ROUTE.fullmatch(self.path)
                if matched is None or matched[1] not in owner._routes:
                    self._json(404, {"error": "unknown capture route"})
                    return
                self._inference(matched[1], matched[2])

            def _inference(self, route, suffix):
                request_id = secrets.token_hex(16)
                folder = owner.root / "attempts" / route / "requests" / request_id
                connection = None
                cancellation = None
                body_file = None
                headers_sent = False
                response_bytes = 0
                response_hash = hashlib.sha256()
                terminal = False
                is_sse = False
                status = "incomplete"
                failure = None
                started = time.time()
                try:
                    _private_directory(folder)
                    body = self._body()
                    _write_bytes(folder / "request.body", body)
                    write_json(
                        folder / "request.json",
                        {
                            "schema_version": 1,
                            "request_id": request_id,
                            "method": self.command,
                            "upstream_path": "/v1" + suffix,
                            "headers": {
                                k.lower(): v
                                for k, v in self.headers.items()
                                if k.lower() in _REQUEST_HEADERS
                            },
                            "body_bytes": len(body),
                            "body_sha256": hashlib.sha256(body).hexdigest(),
                            "started_at": now(),
                            "started_epoch": started,
                        },
                    )
                    # Open the evidence stream before admitting an upstream call.
                    body_file = _ResponseBody(
                        folder / "response.body",
                        owner.sync_interval_seconds,
                        lambda: setattr(owner, "_fatal", True),
                    )
                    connection = http.client.HTTPConnection(
                        "127.0.0.1",
                        owner.upstream.port,
                        timeout=owner.upstream_timeout_seconds,
                    )
                    headers = {
                        k: v
                        for k, v in self.headers.items()
                        if k.lower() in _REQUEST_HEADERS
                    }
                    if owner._fatal:
                        raise OSError("Capture storage unavailable")
                    connection.request(
                        self.command, "/v1" + suffix, body=body, headers=headers
                    )
                    cancellation = _CancelOnDisconnect(self.connection, connection.sock)
                    response = connection.getresponse()
                    safe_headers = {
                        k.lower(): v
                        for k, v in response.getheaders()
                        if k.lower() in _RESPONSE_HEADERS
                    }
                    write_json(
                        folder / "response.json",
                        {
                            "status": response.status,
                            "reason": response.reason,
                            "headers": safe_headers,
                            "received_at": now(),
                        },
                    )
                    is_sse = "text/event-stream" in safe_headers.get("content-type", "")
                    self.send_response(response.status)
                    for name, value in safe_headers.items():
                        self.send_header(name, value)
                    self.send_header("Connection", "close")
                    self.end_headers()
                    headers_sent = True
                    pending = b""
                    while True:
                        chunk = response.read1(65536)
                        if not chunk:
                            break
                        if owner._fatal:
                            raise OSError("Capture storage unavailable")
                        body_file.write(chunk)
                        response_hash.update(chunk)
                        response_bytes += len(chunk)
                        if not is_sse:
                            # Retain the last chunk until its terminal fsync.
                            if pending:
                                self.wfile.write(pending)
                                self.wfile.flush()
                            pending = chunk
                            continue
                        pending += chunk
                        # Preserve exact delimiters while retaining partial SSE events.
                        while True:
                            match = re.search(b"\r?\n\r?\n", pending)
                            if match is None:
                                break
                            event, pending = (
                                pending[: match.end()],
                                pending[match.end() :],
                            )
                            if _terminal_event(event):
                                body_file.sync()
                                write_json(
                                    folder / "terminal_step.json",
                                    {
                                        "persisted_at": now(),
                                        "response_bytes": response_bytes,
                                        "response_sha256": response_hash.hexdigest(),
                                    },
                                )
                                terminal = True
                            self.wfile.write(event)
                            self.wfile.flush()
                    if "content-length" in safe_headers and response_bytes != int(
                        safe_headers["content-length"]
                    ):
                        raise http.client.IncompleteRead(
                            b"", int(safe_headers["content-length"]) - response_bytes
                        )
                    body_file.sync()
                    if is_sse and pending and _terminal_event(pending):
                        terminal = True
                        write_json(
                            folder / "terminal_step.json",
                            {
                                "persisted_at": now(),
                                "response_bytes": response_bytes,
                                "response_sha256": response_hash.hexdigest(),
                            },
                        )
                    status = "complete" if not is_sse or terminal else "incomplete"
                    # Persist completion before forwarding final non-SSE bytes.
                    write_json(
                        folder / "receipt.json",
                        {
                            "status": status,
                            "response_bytes": response_bytes,
                            "response_sha256": response_hash.hexdigest(),
                            "terminal_event": terminal,
                            "finished_at": now(),
                            "elapsed_seconds": time.time() - started,
                        },
                    )
                    if pending:
                        self.wfile.write(pending)
                        self.wfile.flush()
                except (OSError, http.client.HTTPException, ValueError) as error:
                    failure = type(error).__name__
                    # Incomplete body bytes are retained even when the native
                    # caller disconnects or a local upstream stops responding.
                    if isinstance(error, OSError) and not isinstance(
                        error, (ConnectionError, TimeoutError)
                    ):
                        owner._fatal = True
                    if not headers_sent:
                        try:
                            self._json(
                                502, {"error": "capture request did not complete"}
                            )
                        except OSError:
                            pass
                finally:
                    if cancellation is not None:
                        cancellation.close()
                    if body_file is not None:
                        try:
                            body_file.close()
                        except OSError:
                            owner._fatal = True
                    if connection is not None:
                        connection.close()
                    if failure is not None:
                        try:
                            write_json(
                                folder / "receipt.json",
                                {
                                    "status": "incomplete",
                                    "error_type": failure,
                                    "response_bytes": response_bytes,
                                    "response_sha256": response_hash.hexdigest(),
                                    "terminal_event": terminal,
                                    "finished_at": now(),
                                    "elapsed_seconds": time.time() - started,
                                },
                            )
                        except OSError:
                            owner._fatal = True

        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        try:
            write_json(
                self.root / "proxy.json",
                {
                    "schema_version": 1,
                    "endpoint": self.endpoint,
                    "upstream": f"http://127.0.0.1:{self.upstream.port}/v1",
                    "sync_interval_seconds": self.sync_interval_seconds,
                    "request_durable_before_upstream": True,
                    "terminal_step_durable_before_delivery": True,
                    "intermediate_body_flush": "unbuffered with bounded fsync",
                    "started_at": now(),
                },
            )
        except OSError:
            self._server.server_close()
            self._server = None
            raise
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
