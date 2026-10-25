"""Existing providers keep the native admission lock through their supervisor."""

import os
import sys
from contextlib import contextmanager, nullcontext
from types import SimpleNamespace

from proof_eval.providers import execution


def test_gateway_executor_passes_the_live_capacity_fd_to_its_boundary(
    tmp_path, monkeypatch
):
    marker = tmp_path / "native-lock-observed"

    @contextmanager
    def capacity():
        with (tmp_path / "slot").open("a") as lock:
            yield lock.fileno()

    def boundary(argv, folder, protected, *, lifetime_fd=None, **kwargs):
        if argv[0] != "fixture-native":
            return argv  # The independent no-op isolation preflight.
        return [
            sys.executable,
            "-c",
            "import os,sys; from pathlib import Path; "
            "os.fstat(int(sys.argv[1])); Path(sys.argv[2]).write_text('held')",
            str(lifetime_fd),
            str(marker),
        ]

    monkeypatch.setattr(execution, "launch_command", boundary)

    def build(workspace, *args):
        return execution.Launch(
            argv=["fixture-native"],
            environment=dict(os.environ),
            runtime_paths=(),
            cwd=workspace,
            parse=lambda *_: {
                "status": "received",
                "content": "fixture",
                "usage": None,
            },
            capacity=capacity,
        )

    result = execution.generate(
        folder=tmp_path / "attempt",
        messages=[
            dict(role="system", content="fixture"),
            dict(role="user", content="fixture"),
        ],
        model="Qwen/Qwen3.8-Flash-Next",
        effort="xhigh",
        mode="score_edges",
        session=SimpleNamespace(best_code="theorem fixture : True := by trivial"),
        context={"source_projects": {}},
        expected_cli={},
        identity={},
        instructions="fixture",
        tool_service=lambda *_: nullcontext(),
        provider="lemex",
        authentication="offline fixture",
        build=build,
        timeout=5,
    )
    assert result["status"] == "received" and result["returncode"] == 0
    assert marker.read_text() == "held"
