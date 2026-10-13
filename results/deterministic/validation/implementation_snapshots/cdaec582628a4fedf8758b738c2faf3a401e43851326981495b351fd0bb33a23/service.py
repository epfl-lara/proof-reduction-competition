"""Unix-socket tool service. The model cannot write the host's evidence ledger."""

import json
import socketserver
import tempfile
import threading
from pathlib import Path

from proof_eval.evidence.io import write_json


class ProofToolService:
    def __init__(self, session, workspace):
        self.session, self.workspace = session, Path(workspace)
        self.temporary = tempfile.TemporaryDirectory(prefix="arena-agent-")
        self.socket_path = str(Path(self.temporary.name) / "tools.sock")
        owner = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                try:
                    line = self.rfile.readline(1024 * 1024 + 1)
                    if len(line) > 1024 * 1024 or not line.endswith(b"\n"):
                        raise ValueError("Oversized or incomplete tool request")
                    response = owner.session.dispatch(json.loads(line))
                except Exception as error:
                    response = {
                        "kind": "tool_error",
                        "error": f"{type(error).__name__}: {error}",
                    }
                try:
                    self.wfile.write(
                        json.dumps(
                            response, ensure_ascii=False, allow_nan=False
                        ).encode()
                        + b"\n"
                    )
                except BrokenPipeError:
                    pass

        self.server = socketserver.ThreadingUnixStreamServer(self.socket_path, Handler)
        # A native cost stop can exit while a host Lean check is still running.
        # Drain accepted handlers before the attempt records its final ledger
        # boundary or starts a new session. Wall deadlines remain supervised
        # by the worker's process-level deadline, including these host checks.
        self.server.daemon_threads = False
        self.server.block_on_close = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        write_json(self.workspace / "tool_service.json", {"socket": self.socket_path})
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temporary.cleanup()
