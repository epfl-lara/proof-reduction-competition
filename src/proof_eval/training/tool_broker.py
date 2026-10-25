"""Job-owned CPU host sessions, separate from CUDA and Megatron interpreters."""

from __future__ import annotations

import json
import os
import re
import signal
import socket
import socketserver
import struct
import subprocess
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path

from proof_eval.evidence.immutable import canonical, immutable, read, sha
from proof_eval.training.reward import UnscorableEpisode

MAX_WIRE = 1024 * 1024


def ticks(pid: int) -> str:
    return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]


def _receive(connection: socket.socket) -> dict:
    def take(size):
        parts = []
        while size:
            value = connection.recv(size)
            if not value:
                raise ConnectionError("CPU tool connection ended before its receipt")
            parts.append(value)
            size -= len(value)
        return b"".join(parts)

    size = struct.unpack("!Q", take(8))[0]
    if not 0 < size <= MAX_WIRE:
        raise ValueError("CPU tool receipt exceeds its wire bound")
    return json.loads(take(size))


def _send(connection: socket.socket, value: dict) -> None:
    raw = canonical(value)
    if len(raw) > MAX_WIRE:
        raise ValueError("CPU tool receipt exceeds its wire bound")
    connection.sendall(struct.pack("!Q", len(raw)) + raw)


def _peer(connection: socket.socket) -> tuple[int, int, int]:
    return struct.unpack(
        "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
    )


def _owned(pid: int, owner: dict) -> bool:
    if ticks(owner["pid"]) != owner["start_ticks"]:
        return False
    for _ in range(16):
        if pid == owner["pid"]:
            return True
        if pid <= 1:
            return False
        parts = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        pid = int(parts[1])
    return False


def rpc(config: dict, rank: str, episode: str, op: str, payload: dict) -> dict:
    spec = config["cpu_tool_broker"]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", episode):
        raise ValueError("Invalid owned episode identifier")
    if rank != "owner" and rank not in {str(i) for i in range(8)}:
        raise ValueError("Invalid training rank")
    folder = Path(spec["requests"]) / rank / episode / uuid.uuid4().hex
    request = {
        "op": op,
        "episode": episode,
        "rank": rank,
        "payload": payload,
        "client_pid": os.getpid(),
        "client_start_ticks": ticks(os.getpid()),
        "launch_id": config["launch_id"],
        "at_epoch": time.time(),
    }
    pin = immutable(folder / "request.json", request)
    descriptor = Path(spec["ready"])
    ready_pin = sha(descriptor)
    ready = read(descriptor)
    immutable(
        folder / "intent.json",
        {
            "request_sha256": pin,
            "broker_ready_sha256": ready_pin,
            "automatic_retry": False,
            "deadline_seconds": spec["request_seconds"],
        },
    )
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(5)
            connection.connect(spec["socket"])
            connection.settimeout(spec["request_seconds"])
            _send(
                connection,
                {
                    "folder": str(folder),
                    "request_sha256": pin,
                    "broker_ready_sha256": ready_pin,
                },
            )
            receipt = _receive(connection)
    except (OSError, ValueError, ConnectionError) as error:
        immutable(
            folder / "client-unknown.json",
            {"error": str(error), "at_epoch": time.time(), "automatic_retry": False},
        )
        raise UnscorableEpisode(
            "CPU tool operation is unknown; inspect exact receipts: " + str(folder)
        ) from error
    if (
        receipt["request_sha256"] != pin
        or receipt["broker_pid"] != ready["pid"]
        or receipt["broker_start_ticks"] != ready["start_ticks"]
        or receipt["broker_ready_sha256"] != ready_pin
    ):
        raise UnscorableEpisode("CPU tool receipt ownership changed")
    if receipt["status"] != "passed":
        if receipt["failed_sha256"] != sha(folder / "failed.json"):
            raise UnscorableEpisode("CPU tool failure evidence changed")
        failure = read(folder / "failed.json")
        raise UnscorableEpisode(
            "CPU host tool failed: " + failure["error"] + "; evidence: " + str(folder)
        )
    if receipt["result_sha256"] != sha(folder / "result.json"):
        raise UnscorableEpisode("CPU tool result changed")
    return read(folder / "result.json")


class HostServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True

    def __init__(self, config: dict, ready: dict, factory=None):
        self.config, self.ready = config, ready
        self.factory = factory
        self.episodes = {}
        self.locks = {}
        self.guard = threading.Lock()
        self.active = 0
        self.stop_requested = threading.Event()
        super().__init__(config["cpu_tool_broker"]["socket"], HostRequest)
        os.chmod(config["cpu_tool_broker"]["socket"], 0o600)
        self.timeout = 0.2

    def dispatch(self, request: dict):
        op, payload = request["op"], request["payload"]
        key = request["rank"] + "/" + request["episode"]
        if op in {"status", "shutdown"}:
            if request["client_pid"] != self.ready["owner"]["pid"]:
                raise ValueError("Only the original driver controls the CPU service")
            with self.guard:
                active = self.active
            result = {"active_requests": active - 1, "episodes": len(self.episodes)}
            if op == "shutdown":
                if active != 1:
                    raise ValueError("CPU tool requests are still active")
                self.episodes.clear()
            return result
        with self.guard:
            lock = self.locks.setdefault(key, threading.Lock())
        if not lock.acquire(blocking=False):
            raise ValueError("An episode already owns an active CPU operation")
        try:
            if op == "create":
                if key in self.episodes:
                    raise ValueError("A CPU episode cannot be replayed")
                factory = self.factory
                if factory is None:
                    from proof_eval.training.episode import Episode

                    factory = Episode
                episode = factory(
                    payload["task_id"],
                    request["episode"],
                    int(request["rank"]),
                    self.config,
                )
                self.episodes[key] = episode
                return {
                    "folder": str(episode.folder),
                    "messages": episode.initial_messages(),
                    "turns": episode.turns,
                }
            if key not in self.episodes:
                raise ValueError("No live CPU episode owns this operation")
            episode = self.episodes[key]
            if op == "advance":
                result = episode.advance(
                    payload["completion"],
                    payload["finish_reason"],
                    payload["token_record"],
                )
                return {
                    "result": result,
                    "turns": episode.turns,
                    "next_observation": (
                        None if result["done"] else episode.next_observation()
                    ),
                }
            if op == "close":
                self.episodes.pop(key)
                return {"closed": True, "turns": episode.turns}
            raise ValueError("Unsupported CPU host operation")
        finally:
            lock.release()


class HostRequest(socketserver.BaseRequestHandler):
    def handle(self):
        folder = None
        request = None
        server = self.server
        try:
            self.request.settimeout(5)
            wire = _receive(self.request)
            folder = Path(wire["folder"]).resolve()
            root = Path(server.config["cpu_tool_broker"]["requests"]).resolve()
            if not folder.is_relative_to(root):
                raise ValueError("CPU request escapes this run's request ledger")
            request = read(folder / "request.json")
            pid, uid, _ = _peer(self.request)
            if (
                uid != os.getuid()
                or pid != request["client_pid"]
                or ticks(pid) != request["client_start_ticks"]
                or not _owned(pid, server.ready["owner"])
                or request["launch_id"] != server.config["launch_id"]
                or sha(folder / "request.json") != wire["request_sha256"]
                or wire["broker_ready_sha256"]
                != sha(server.config["cpu_tool_broker"]["ready"])
            ):
                raise ValueError("CPU request caller/source ownership changed")
            started = {
                "request_sha256": wire["request_sha256"],
                "broker_pid": server.ready["pid"],
                "broker_start_ticks": server.ready["start_ticks"],
                "broker_ready_sha256": wire["broker_ready_sha256"],
                "at_epoch": time.time(),
            }
            immutable(folder / "started.json", started)
            with server.guard:
                server.active += 1
            try:
                result = server.dispatch(request)
            finally:
                with server.guard:
                    server.active -= 1
            pin = immutable(folder / "result.json", result)
            receipt = {
                **started,
                "status": "passed",
                "result_sha256": pin,
                "at_epoch": time.time(),
            }
            immutable(folder / "finished.json", receipt)
            _send(self.request, receipt)
            if request["op"] == "shutdown":
                server.stop_requested.set()
        except Exception as error:
            if folder is not None and request is not None:
                failed = {
                    "status": "failed",
                    "error": str(error),
                    "type": type(error).__name__,
                    "traceback": traceback.format_exc(),
                    "request_sha256": sha(folder / "request.json"),
                    "broker_pid": server.ready["pid"],
                    "broker_start_ticks": server.ready["start_ticks"],
                    "broker_ready_sha256": sha(
                        server.config["cpu_tool_broker"]["ready"]
                    ),
                    "at_epoch": time.time(),
                    "automatic_retry": False,
                }
                failure_pin = immutable(folder / "failed.json", failed)
                try:
                    _send(self.request, {**failed, "failed_sha256": failure_pin})
                except OSError:
                    pass


def broker_spec(plan: dict, root: Path, home: Path) -> dict:
    return {
        "socket": "/tmp/arena-rl-tools-" + plan["launch_id"] + ".sock",
        "requests": str(root / "tool-rpc"),
        "ready": str(root / "tool-broker/ready.json"),
        "home": str(home / "tool-broker"),
        "root": str(root / "tool-broker"),
        "request_seconds": plan["episode_seconds"] + 60,
        "maximum_seconds": plan["maximum_updates_if_all_200_eligible"]
        * (plan["episode_seconds"] + 120)
        + 14400,
    }


def start(config_path: Path):
    from proof_eval.training.semantic_process import semantic_environment

    config = read(config_path)
    spec = config["cpu_tool_broker"]
    folder = Path(spec["root"])
    folder.mkdir(parents=True, exist_ok=False)
    with (folder / "worker.log").open("xb") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "proof_eval.training.tool_broker_worker",
                str(config_path),
            ],
            env=semantic_environment(),
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                "CPU tool service failed before ready; inspect worker.log"
            )
        if Path(spec["ready"]).is_file():
            ready = read(spec["ready"])
            if (
                ready["pid"] != process.pid
                or ready["start_ticks"] != ticks(process.pid)
                or ready["config_sha256"] != sha(config_path)
                or ready["source_sha256"] != sha(Path(__file__))
                or ready["worker_source_sha256"]
                != sha(Path(__file__).with_name("tool_broker_worker.py"))
                or ready["owner"]
                != {"pid": os.getpid(), "start_ticks": ticks(os.getpid())}
            ):
                raise RuntimeError("CPU tool service start identity changed")
            return process
        time.sleep(0.1)
    raise TimeoutError("CPU tool service start is indeterminate; do not duplicate it")


def stop(config: dict, process) -> None:
    deadline = time.monotonic() + config["cpu_tool_broker"]["request_seconds"]
    while time.monotonic() < deadline:
        status = rpc(config, "owner", "owner", "status", {})
        if status["active_requests"] == 0:
            rpc(config, "owner", "owner", "shutdown", {})
            code = process.wait(timeout=30)
            if code:
                raise RuntimeError("CPU tool service did not close cleanly")
            return
        time.sleep(1)
    raise TimeoutError(
        "CPU tool service still has owned active work; preserve receipts"
    )


def serve(config_path: Path, factory=None) -> None:
    config = read(config_path)
    spec = config["cpu_tool_broker"]
    root, home = Path(spec["root"]), Path(spec["home"])
    owner = read(Path(config["home"]) / "started.json")
    ready = {
        "pid": os.getpid(),
        "start_ticks": ticks(os.getpid()),
        "owner": {"pid": owner["pid"], "start_ticks": owner["start_ticks"]},
        "config_sha256": sha(config_path),
        "source_sha256": sha(Path(__file__)),
        "worker_source_sha256": sha(Path(__file__).with_name("tool_broker_worker.py")),
        "at_epoch": time.time(),
        "maximum_seconds": spec["maximum_seconds"],
        "policy_model_calls": 0,
        "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES"),
    }
    for base in (root, home):
        immutable(base / "started.json", ready)

    class Bound(BaseException):
        pass

    def expired(*_):
        raise Bound("Finite job-owned CPU tool service bound")

    signal.signal(signal.SIGALRM, expired)
    signal.alarm(spec["maximum_seconds"])
    try:
        if any(
            n == "mcore_bridge" or n.startswith("mcore_bridge.") for n in sys.modules
        ):
            raise RuntimeError("Training library leaked into the CPU host service")
        with HostServer(config, ready, factory) as server:
            for base in (root, home):
                immutable(base / "ready.json", ready)
            while not server.stop_requested.is_set():
                if ticks(owner["pid"]) != owner["start_ticks"]:
                    raise RuntimeError("Original training driver is no longer live")
                server.handle_request()
        for base in (root, home):
            immutable(
                base / "finished.json",
                {**ready, "status": "closed", "at_epoch": time.time()},
            )
    except BaseException:
        for base in (root, home):
            immutable(
                base / "failed.json",
                {**ready, "error": traceback.format_exc(), "at_epoch": time.time()},
            )
        raise
    finally:
        signal.alarm(0)
        Path(spec["socket"]).unlink(missing_ok=True)
