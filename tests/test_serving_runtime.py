"""Serving identity follows the vLLM executable, not the harness interpreter."""

import io
import json
from pathlib import Path

import pytest

from proof_eval.evidence.io import digest
from proof_eval.providers import vllm_server as server


def cli(tmp_path, shebang):
    file = tmp_path / "vllm"
    file.write_text(shebang + "\n")
    file.chmod(0o755)
    return file


def test_python_shebang_selects_serving_environment(tmp_path, monkeypatch):
    binary = cli(tmp_path, "#!/serving/bin/python")
    monkeypatch.setattr(
        server.shutil, "which", lambda p: str(binary) if p == "vllm" else p
    )
    actual = server.serving_runtime(server.ServerConfig())
    assert actual["python"] == "/serving/bin/python"
    assert actual["binary_sha256"] == digest(binary)


def test_rcp_wrapper_selects_packaged_python_after_harness_activation(monkeypatch):
    original = Path.open

    def opening(path, *a, **kw):
        if str(path) == "/opt/rcp/bin/vllm":
            return io.BytesIO(b"#!/usr/bin/env bash\n")
        return original(path, *a, **kw)

    monkeypatch.setattr(Path, "open", opening)
    monkeypatch.setattr(
        server.shutil, "which", lambda p: "/opt/rcp/bin/vllm" if p == "vllm" else p
    )
    monkeypatch.setattr(server, "digest", lambda p: "pinned-launcher")
    assert (
        server.serving_runtime(server.ServerConfig())["python"]
        == "/opt/rcp/venv/bin/python"
    )


def test_unknown_wrapper_requires_explicit_serving_python(tmp_path, monkeypatch):
    binary = cli(tmp_path, "#!/bin/bash")
    monkeypatch.setattr(
        server.shutil, "which", lambda p: str(binary) if p == "vllm" else p
    )
    with pytest.raises(ValueError, match="--vllm-python"):
        server.serving_runtime(server.ServerConfig())
    assert (
        server.serving_runtime(server.ServerConfig(python="/serving/bin/python"))[
            "python"
        ]
        == "/serving/bin/python"
    )


def test_missing_cli_is_reported_without_starting_a_server(monkeypatch):
    monkeypatch.setattr(server.shutil, "which", lambda p: None)
    with pytest.raises(ValueError, match="executable is unavailable"):
        server.serving_runtime(server.ServerConfig())


def test_metadata_probes_serving_python_with_plugin_environment_and_finite_bound(
    tmp_path, monkeypatch
):
    binary = cli(tmp_path, "#!/serving/bin/python")
    monkeypatch.setattr(
        server.shutil, "which", lambda p: str(binary) if p == "vllm" else p
    )
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    module = plugin / "ampere_ple_patch.py"
    module.write_text("def register(): pass\n")
    calls = []

    def probe(argv, **kwargs):
        calls.append((argv, kwargs))
        return json.dumps(
            {
                "python": "/serving/bin/python",
                "versions": {"vllm": "fixture"},
                "plugins": {
                    "ampere_ple_patch": {
                        "entry_point": "ampere_ple_patch:register",
                        "source": str(module),
                        "sha256": digest(module),
                    }
                },
            }
        )

    monkeypatch.setattr(server.subprocess, "check_output", probe)
    value = server.metadata(server.ServerConfig(), plugin)
    assert calls[0][0][0] == "/serving/bin/python" and calls[0][1]["timeout"] == 30
    assert calls[0][1]["env"]["PYTHONPATH"].split(":")[0] == str(plugin)
    assert value["serving_runtime"]["python"] == "/serving/bin/python"
    assert value["plugins"]["ampere_ple_patch"]["sha256"] == digest(module)


@pytest.mark.parametrize("plugins", [{}, {"ampere_ple_patch": {"sha256": "wrong"}}])
def test_source_only_or_mismatched_plugin_fails_before_server_launch(
    tmp_path, monkeypatch, plugins
):
    binary = cli(tmp_path, "#!/serving/bin/python")
    monkeypatch.setattr(
        server.shutil, "which", lambda p: str(binary) if p == "vllm" else p
    )
    (tmp_path / "ampere_ple_patch.py").write_text("def register(): pass\n")
    monkeypatch.setattr(
        server.subprocess,
        "check_output",
        lambda *a, **k: json.dumps(
            {"versions": {}, "python": "/serving/bin/python", "plugins": plugins}
        ),
    )
    with pytest.raises(ValueError, match="plugin is missing or differs"):
        server.metadata(server.ServerConfig(), tmp_path)
