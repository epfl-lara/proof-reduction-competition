"""Recorded CPU host calls without importing a policy, CUDA, or Lean."""

import json
import os
import socket
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from proof_eval.evidence.immutable import immutable, read, sha
from proof_eval.training import tool_broker as broker
from proof_eval.training.remote_episode import RemoteEpisode
from proof_eval.training.reward import UnscorableEpisode


@pytest.fixture
def running(tmp_path, monkeypatch):
    monkeypatch.setattr(broker, "ticks", lambda _pid: "fixed-test-ticks")
    monkeypatch.setattr(
        broker, "_peer", lambda _connection: (os.getpid(), os.getuid(), os.getgid())
    )
    monkeypatch.setattr(broker, "_owned", lambda _pid, _owner: True)
    with tempfile.TemporaryDirectory(prefix="rltools-", dir="/tmp") as node:
        spec = {
            "socket": str(Path(node) / "host.sock"),
            "requests": str(tmp_path / "requests"),
            "ready": str(tmp_path / "ready.json"),
            "request_seconds": 2,
        }
        config = {"launch_id": "test-launch", "cpu_tool_broker": spec}
        ready = {
            "pid": os.getpid(),
            "start_ticks": "fixed-test-ticks",
            "owner": {"pid": os.getpid(), "start_ticks": "fixed-test-ticks"},
        }
        immutable(spec["ready"], ready)
        calls = []

        class Host:
            def __init__(self, task, identity, rank, supplied):
                self.folder = tmp_path / "episodes" / identity
                self.folder.mkdir(parents=True, exist_ok=False)
                self.task, self.turns = task, 0
                calls.append(("create", task, identity, rank, supplied))

            def initial_messages(self):
                return [{"role": "user", "content": self.task + " αβ input" * 2000}]

            def advance(self, text, finish, tokens):
                self.turns += 1
                calls.append(("advance", self.task, text, finish, tokens))
                return {
                    "done": finish == "stop",
                    "rollout_infos": {"arena_reward": 0.25, "num_turns": self.turns},
                }

            def next_observation(self):
                return json.dumps(
                    {"kind": "host_result", "task": self.task}, ensure_ascii=False
                )

        server = broker.HostServer(config, ready, Host)

        def serve():
            while not server.stop_requested.is_set():
                server.handle_request()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            yield config, server, calls, tmp_path
        finally:
            server.stop_requested.set()
            thread.join(timeout=3)
            server.server_close()
            assert not thread.is_alive()


def test_complete_context_tokens_results_and_receipt_hashes(running):
    config, server, calls, root = running
    episode = RemoteEpisode("task", "owned-one", 0, config)
    assert episode.initial_messages()[0]["content"] == "task" + " αβ input" * 2000
    tokens = {
        "actual_input_messages": episode.initial_messages(),
        "sampled_token_ids": [1, 2, 5],
        "behavior_logprobs": [-0.3, -0.4, -0.7],
    }
    result = episode.advance("full reasoning Ω", "continue", tokens)
    assert result["rollout_infos"]["arena_reward"] == 0.25
    assert calls[-1][2:] == ("full reasoning Ω", "continue", tokens)
    assert json.loads(episode.next_observation())["task"] == "task"
    assert episode.turns == 1
    requests = sorted((root / "requests").glob("0/owned-one/*/request.json"))
    assert len(requests) == 2
    for path in requests:
        receipt = read(path.with_name("finished.json"))
        assert receipt["request_sha256"] == sha(path)
        assert receipt["result_sha256"] == sha(path.with_name("result.json"))
        assert receipt["broker_pid"] == os.getpid()
    assert episode.close()["closed"] is True
    assert not server.episodes


def test_eight_parallel_sessions_keep_separate_state(running):
    config, server, _, _ = running
    with ThreadPoolExecutor(max_workers=8) as pool:
        episodes = list(
            pool.map(
                lambda rank: RemoteEpisode(
                    "task-" + str(rank), "owned-" + str(rank), rank, config
                ),
                range(8),
            )
        )
    assert len(server.episodes) == 8
    assert len({episode.folder for episode in episodes}) == 8
    assert all(
        episode.initial_messages()[0]["content"].startswith("task-" + str(i))
        for i, episode in enumerate(episodes)
    )
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda episode: episode.close(), episodes))
    assert not server.episodes


def test_host_failure_is_unscorable_and_never_retried(running):
    config, server, _, root = running

    def broken(*_):
        raise RuntimeError("exact original unavailable")

    server.factory = broken
    with pytest.raises(UnscorableEpisode, match="exact original unavailable"):
        RemoteEpisode("task", "failed-create", 0, config)
    paths = list((root / "requests").glob("0/failed-create/*/failed.json"))
    assert len(paths) == 1
    assert read(paths[0])["automatic_retry"] is False
    assert not list(root.rglob("reward.json"))


def test_duplicate_episode_refuses_replay(running):
    config, _, calls, _ = running
    episode = RemoteEpisode("task", "duplicate", 0, config)
    with pytest.raises(UnscorableEpisode, match="cannot be replayed"):
        RemoteEpisode("task", "duplicate", 0, config)
    assert len(calls) == 1
    episode.close()


def test_changed_result_hash_refuses_training(running, monkeypatch):
    config, _, _, _ = running
    digest = broker.sha
    monkeypatch.setattr(
        broker,
        "sha",
        lambda path: "changed" if Path(path).name == "result.json" else digest(path),
    )
    with pytest.raises(UnscorableEpisode, match="result changed"):
        RemoteEpisode("task", "changed-result", 0, config)


def test_unknown_transport_preserves_single_intent(running, monkeypatch):
    config, _, calls, root = running
    send = broker._send

    def timeout(connection, value):
        if "folder" in value:
            raise TimeoutError("unknown original request")
        return send(connection, value)

    monkeypatch.setattr(broker, "_send", timeout)
    with pytest.raises(UnscorableEpisode, match="operation is unknown"):
        RemoteEpisode("task", "unknown-call", 0, config)
    assert (
        len(list((root / "requests").glob("0/unknown-call/*/client-unknown.json"))) == 1
    )
    assert not calls


def test_foreign_caller_is_refused_before_host_work(running, monkeypatch):
    config, _, calls, _ = running
    monkeypatch.setattr(broker, "_owned", lambda _pid, _owner: False)
    with pytest.raises(UnscorableEpisode, match="ownership changed"):
        RemoteEpisode("task", "foreign-call", 0, config)
    assert not calls


def test_owner_status_and_shutdown_are_model_free(running):
    config, server, calls, _ = running
    status = broker.rpc(config, "owner", "owner", "status", {})
    assert status == {"active_requests": 0, "episodes": 0}
    broker.rpc(config, "owner", "owner", "shutdown", {})
    assert server.stop_requested.wait(1)
    assert not calls


def test_wire_bound_rejects_incomplete_and_oversized_receipts():
    import struct

    first, second = socket.socketpair()
    try:
        first.sendall(struct.pack("!Q", broker.MAX_WIRE + 1))
        with pytest.raises(ValueError, match="wire bound"):
            broker._receive(second)
        first.close()
        with pytest.raises(ConnectionError, match="ended before"):
            broker._receive(second)
    finally:
        first.close()
        second.close()


def test_episode_identifiers_cannot_escape_ledger(running):
    config, _, calls, _ = running
    with pytest.raises(ValueError, match="identifier"):
        RemoteEpisode("task", "../foreign", 0, config)
    assert not calls
