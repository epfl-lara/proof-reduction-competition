"""Run CPU-only real native-guard integration checks; never call a model/Lean.

Usage: PYTHONPATH=src python3 tests/check_host_compat.py DIRECTORY LEMEX_BINARY
Run inside a container/runtime permitted to create user and mount namespaces.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from proof_eval.providers import (
    execution,
    native_resources,
    readonly_mounts,
    signal_scope,
)
from proof_eval.providers.execution import Launch


def main(root: Path, native: Path) -> dict:
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    profile = root / "profile"
    profile.mkdir()
    protected = root / "source.txt"
    protected.write_text("owned integration canary\n")
    scope = signal_scope.configured_identity()
    identity = {
        "signal_scope": scope,
        "native_resources": native_resources.identity(),
        "filesystem_guard": readonly_mounts.identity(),
    }
    peer = subprocess.Popen([sys.executable, "-I", "-c", "import time;time.sleep(30)"])
    try:
        with tempfile.TemporaryDirectory(prefix="proof-host-check-") as socket_root:
            endpoint = str(Path(socket_root) / "tools.sock")
            service_errors = []

            @contextmanager
            def tools(_session, _workspace):
                listener = socket.socket(socket.AF_UNIX)
                listener.bind(endpoint)
                listener.listen(1)
                listener.settimeout(10)

                def serve():
                    try:
                        connection, _ = listener.accept()
                        with connection:
                            assert connection.recv(1024) == b"host-tool-check"
                            connection.sendall(b"host-tool-ok")
                    except Exception as error:
                        service_errors.append(repr(error))

                thread = threading.Thread(target=serve, daemon=True)
                thread.start()
                try:
                    yield
                finally:
                    listener.close()
                    thread.join(timeout=11)

            payload = root / "payload.py"
            payload.write_text("""import errno,json,os,socket,subprocess,sys
native, endpoint, peer = sys.argv[1],sys.argv[2],int(sys.argv[3])
checks={}
for option in ("--version", "--help"):
    result=subprocess.run([native,option],capture_output=True,text=True,timeout=5)
    assert result.returncode==0,(option,result.returncode,result.stderr)
    checks["native"+option]=bool(result.stdout.strip())
with socket.socket(socket.AF_UNIX) as client:
    client.settimeout(3);client.connect(endpoint);client.sendall(b"host-tool-check")
    checks["host_tool_socket"]=client.recv(1024)==b"host-tool-ok"
try: os.kill(peer,15)
except OSError as error:
    assert error.errno==errno.EPERM
    checks["unrelated_owned_peer_signal_denied"]=True
else: raise AssertionError("client signalled a process outside its native tree")
shell=subprocess.run(["/bin/bash","--noprofile","--norc","-c","printf shell-ok"],capture_output=True,text=True,timeout=3)
checks["shell_child"]=shell.returncode==0 and shell.stdout=="shell-ok"
try: bytearray(5*1024**3)
except MemoryError: checks["oversized_allocation_denied"]=True
else: raise AssertionError("allocation exceeded the inherited hard DATA limit")
assert all(checks.values())
print(json.dumps({"checks":checks}))
""")

            def build(workspace, system, final, folder):
                return Launch(
                    argv=[
                        sys.executable,
                        "-I",
                        str(payload),
                        str(native),
                        endpoint,
                        str(peer.pid),
                    ],
                    environment=dict(os.environ),
                    runtime_paths=(profile,),
                    cwd=workspace,
                    parse=lambda events, final, code: {
                        "status": "received" if code == 0 else "transport_error",
                        "usage": None,
                        "content": "CPU-only guard integration passed",
                        "events": events,
                    },
                )

            folder = root / "generation"
            result = execution.generate(
                folder=folder,
                messages=[
                    {"role": "system", "content": "CPU guard check only"},
                    {"role": "user", "content": "No model or Lean call"},
                ],
                model="no-model-called",
                effort="none",
                mode="score_edges",
                session=SimpleNamespace(best_code="owned canary; not Lean input"),
                context={"source_projects": {"canary": str(protected)}},
                expected_cli=identity,
                instructions="CPU-only integration check",
                tool_service=tools,
                identity=identity,
                provider="lemex-local",
                authentication="none",
                build=build,
                timeout=20,
            )
            assert result["status"] == "received", result
            assert result["signal_scope"]["status"] == "verified"
            assert result["native_resources"]["status"] == "verified"
            assert result["process_ownership"]["cleanup"]["complete"] is True
            assert peer.poll() is None, "The outside peer was changed"
            assert protected.read_text() == "owned integration canary\n"
            assert not service_errors, service_errors
            signal_scope.audit_generation(folder, result)
            command = json.loads((folder / "command.json").read_text())
            request = json.loads((folder / "request.json").read_text())
            tampered = {**command, "filesystem_guard": {"backend": "landlock"}}
            try:
                readonly_mounts.audit(folder, request, tampered, folder)
            except ValueError:
                pass
            else:
                raise AssertionError("Audit accepted a changed filesystem backend")
            report = {
                "status": "passed",
                "checks": result["events"][0]["checks"],
                "filesystem_canaries": command["filesystem_preflight"],
                "guarded_generation_and_offline_audit": True,
                "changed_backend_audit_rejected": True,
                "owned_tree_fully_reaped": True,
                "model_calls": 0,
                "Lean_calls": 0,
                "evidence_directory": str(root),
            }
            (root / "integration-report.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
            return report
    finally:
        peer.terminate()
        peer.wait(timeout=5)


if __name__ == "__main__":
    print(
        json.dumps(
            main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()), indent=2
        )
    )
