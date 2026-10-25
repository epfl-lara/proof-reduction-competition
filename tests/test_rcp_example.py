"""The submission recipe previews safely and never retries an unknown intent."""

import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "examples/rcp/submit-local.sh"


@pytest.fixture
def submit_environment(tmp_path):
    binary = tmp_path / "bin"
    binary.mkdir()
    call = tmp_path / "dispatches"
    (binary / "runai").write_text(
        '#!/bin/sh\nprintf "called\\n" >> "$MOCK_DISPATCHES"\nprintf "fixture ack\\n"\n'
    )
    (binary / "runai").chmod(0o755)
    env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"])
    for key in (
        "PROJECT",
        "IMAGE",
        "UID",
        "GID",
        "USER",
        "HOME",
        "HARNESS",
        "PROFILE",
        "OUTPUT",
        "PLUGIN",
        "BASE",
        "DATASET",
        "REFERENCES",
        "ENVIRONMENTS",
        "CACHE",
    ):
        env["RCP_" + key] = "fixture-" + key.lower()
    env.update(
        RCP_JOB="fixture.local-job",
        RCP_LOCAL_RECEIPTS=str(tmp_path / "receipts"),
        PROOF_SIGNAL_SCOPE_BINARY="/fixture/validated-guard",
        MOCK_DISPATCHES=str(call),
    )
    return env, call


def test_default_is_a_preview_without_dispatch_or_intent(submit_environment):
    env, call = submit_environment
    result = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "--gpu 4" in result.stdout and "--backoff-limit 0" in result.stdout
    assert not call.exists()
    assert not Path(env["RCP_LOCAL_RECEIPTS"]).exists()


def test_submit_is_once_and_acknowledgment_does_not_claim_running(submit_environment):
    env, call = submit_environment
    command = ["bash", str(SCRIPT), "--submit"]
    first = subprocess.run(command, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    prefix = Path(env["RCP_LOCAL_RECEIPTS"]) / env["RCP_JOB"]
    intent = Path(str(prefix) + ".intent.json").read_bytes()
    receipt = json.loads(Path(str(prefix) + ".submission.json").read_text())
    assert receipt["status"] == "acknowledged_unbound"
    assert receipt["workload_pod_identity_verified"] is False
    assert Path(str(prefix) + ".response.log").read_text() == "fixture ack\n"
    second = subprocess.run(command, env=env, capture_output=True, text=True)
    assert second.returncode != 0
    assert call.read_text() == "called\n"
    assert Path(str(prefix) + ".intent.json").read_bytes() == intent
