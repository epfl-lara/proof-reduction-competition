"""Backend selection, protected-path overlap and immutable canary evidence."""

import json
import sys

import pytest

from proof_eval.providers import filesystem_probe, isolation, readonly_mounts


def test_unknown_backend_never_falls_back(monkeypatch):
    monkeypatch.setenv(readonly_mounts.ENVIRONMENT, "unrestricted")
    with pytest.raises(ValueError, match="Unknown filesystem"):
        readonly_mounts.identity()


def test_namespace_option_retains_the_existing_process_boundary(tmp_path):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    argv = isolation.launch_command(
        [sys.executable, "-c", "pass"],
        workspace,
        [source],
        runtime_paths=(),
        process_boundary="signal_scope",
        filesystem_backend="readonly-mounts",
    )
    assert "--signal-scope" in argv
    assert argv[argv.index("--filesystem-backend") + 1] == "readonly-mounts"
    with pytest.raises(ValueError, match="existing signal broker"):
        isolation.launch_command(
            ["true"], workspace, [source], filesystem_backend="readonly-mounts"
        )
    default = isolation.launch_command(
        ["true"], workspace, [source], runtime_paths=(), process_boundary="signal_scope"
    )
    assert "--filesystem-backend" not in default


@pytest.mark.parametrize("relative", ["", "source", "source/child"])
def test_overlapping_writable_roots_are_rejected(tmp_path, relative):
    source = tmp_path / "source"
    (source / "child").mkdir(parents=True)
    with pytest.raises(ValueError, match="overlaps protected"):
        readonly_mounts.checked_paths([tmp_path / relative], [source])


def test_canary_evidence_rejects_edited_host_bytes(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _, root = filesystem_probe.prepare(tmp_path, workspace)
    probe = tmp_path / "signal_scope_preflight"
    probe.mkdir()
    (probe / "stdout.log").write_text(
        json.dumps({"checks": {name: True for name in filesystem_probe.CHECKS}})
    )
    assert filesystem_probe.verify(tmp_path)["status"] == "verified"
    (root / "source.txt").write_text("changed")
    with pytest.raises(ValueError, match="changed a protected host canary"):
        filesystem_probe.verify(tmp_path)


def test_filesystem_backend_cannot_change_in_saved_command(tmp_path):
    request = {"cli": {"filesystem_guard": {"backend": "readonly-mounts"}}}
    with pytest.raises(ValueError, match="command identity changed"):
        readonly_mounts.audit(
            tmp_path, request, {"filesystem_guard": {"backend": "landlock"}}, tmp_path
        )
