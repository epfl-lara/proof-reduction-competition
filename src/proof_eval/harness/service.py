"""Unix-socket tool service. The model cannot write the host's evidence ledger."""

from __future__ import annotations

import base64
import fcntl
import json
import os
import socketserver
import tempfile
import threading
import time
import uuid
from pathlib import Path

from proof_eval.evidence.io import now, write_json
from proof_eval.providers.contracts import ToolSession


class ToolEvidenceError(RuntimeError):
    """A tool RPC could not be durably captured and must not be delivered."""


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite tool JSON constant: {value}")


class _ToolServer(socketserver.ThreadingUnixStreamServer):
    request_queue_size = 128


class ProofToolService:
    def __init__(self, session: ToolSession, workspace: str | Path) -> None:
        self.session, self.workspace = session, Path(workspace)
        # The native process may write workspace, never the host evidence folder.
        evidence = Path(getattr(session, "folder", self.workspace.parent))
        self.ledger_path = evidence / "tool_rpc.jsonl"
        if self.ledger_path.resolve().is_relative_to(self.workspace.resolve()):
            # Standalone callers may supply a workspace containing the session
            # folder. Keep capture outside that writable tree in this case too.
            self.ledger_path = self.workspace.parent / (
                f".{self.workspace.name}-tool-rpc.jsonl"
            )
        if self.ledger_path.resolve().is_relative_to(self.workspace.resolve()):
            raise ValueError("Tool RPC evidence must be outside the native workspace")
        self.service_id = uuid.uuid4().hex
        self._ledger_lock = threading.Lock()
        self._ledger_error: Exception | None = None
        self.temporary = tempfile.TemporaryDirectory(prefix="arena-agent-")
        self.socket_path = str(Path(self.temporary.name) / "tools.sock")
        owner = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                request_id, started = uuid.uuid4().hex, time.monotonic()
                request, error = None, None
                line = b""
                try:
                    line = self.rfile.readline(1024 * 1024 + 1)
                    if len(line) > 1024 * 1024 or not line.endswith(b"\n"):
                        raise ValueError("Oversized or incomplete tool request")
                    request = json.loads(line, parse_constant=_reject_constant)
                except Exception as caught:
                    error = caught
                try:
                    owner._record(
                        {
                            "event": "request_started",
                            "request_id": request_id,
                            "request": request,
                            "request_wire_base64": base64.b64encode(line).decode(),
                        }
                    )
                except ToolEvidenceError:
                    return
                try:
                    if error is not None:
                        raise error
                    response = owner.session.dispatch(request)
                    wire = owner._encode_response(response)
                except Exception as caught:
                    response = {
                        "kind": "tool_error",
                        "error": f"{type(caught).__name__}: {caught}",
                    }
                    wire = owner._encode_response(response)
                try:
                    owner._record(
                        {
                            "event": "response_completed",
                            "request_id": request_id,
                            "response": response,
                            "response_wire_base64": base64.b64encode(wire).decode(),
                            "elapsed_seconds": time.monotonic() - started,
                        }
                    )
                except ToolEvidenceError:
                    return
                try:
                    self.wfile.write(wire)
                except BrokenPipeError:
                    pass

        self.server = _ToolServer(self.socket_path, Handler)
        # A native cost stop can exit while a host Lean check is still running.
        # Drain accepted handlers before the attempt records its final ledger
        # boundary or starts a new session. Wall deadlines remain supervised
        # by the worker's process-level deadline, including these host checks.
        self.server.daemon_threads = False
        self.server.block_on_close = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @staticmethod
    def _encode_response(response: dict) -> bytes:
        return (
            json.dumps(response, ensure_ascii=False, allow_nan=False).encode() + b"\n"
        )

    def _record(self, record: dict) -> None:
        """Append and fsync one step before dispatch or response delivery.

        The lock also covers independent service instances/processes sharing a
        theorem ledger. A killed worker may leave a trailing partial record;
        its already fsynced request-start remains an explicit interrupted RPC.
        """
        try:
            encoded = (
                json.dumps(
                    {
                        "schema_version": 1,
                        "service_id": self.service_id,
                        "workspace": str(self.workspace.resolve()),
                        "at": now(),
                        **record,
                    },
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode()
                + b"\n"
            )
            with self._ledger_lock:
                if self._ledger_error is not None:
                    raise ToolEvidenceError("A previous tool RPC evidence write failed")
                self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
                fd = os.open(
                    self.ledger_path,
                    os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW,
                    0o600,
                )
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                    remaining = memoryview(encoded)
                    while remaining:
                        written = os.write(fd, remaining)
                        if written <= 0:
                            raise OSError("Tool RPC ledger write made no progress")
                        remaining = remaining[written:]
                    os.fsync(fd)
                finally:
                    os.close(fd)
        except Exception as caught:
            with self._ledger_lock:
                if self._ledger_error is None:
                    self._ledger_error = caught
            raise ToolEvidenceError("Durable tool RPC capture failed") from caught

    def __enter__(self) -> ProofToolService:
        self.thread.start()
        write_json(self.workspace / "tool_service.json", {"socket": self.socket_path})
        return self

    def __exit__(self, exception_type=None, exception=None, traceback=None) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temporary.cleanup()
        if self._ledger_error is not None and exception is None:
            raise ToolEvidenceError(
                "Durable tool RPC capture failed"
            ) from self._ledger_error
