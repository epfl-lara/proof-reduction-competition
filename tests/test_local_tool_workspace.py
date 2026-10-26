"""Native shell calls need the actual workspace and successful tool evidence."""

import json

import pytest

from proof_eval.providers import lemex_local
from proof_eval.providers.capture_smoke import _successful_nonce_command


def test_local_native_shell_receives_its_real_environment(tmp_path):
    argv = lemex_local.command(
        binary="lemex",
        workspace=tmp_path,
        system_file=tmp_path / "system.txt",
        last_message=tmp_path / "final.txt",
        model=lemex_local.MODEL,
        effort="xhigh",
        mode="score_edges",
        catalog=tmp_path / "models.json",
        base_url="http://127.0.0.1:8128/v1",
        instructions="Use the host tools.",
    )
    assert argv[argv.index("-C") + 1] == str(tmp_path)
    assert "include_environment_context=true" in argv
    assert "include_apps_instructions=false" in argv
    assert "project_doc_max_bytes=0" in argv


def test_returned_nonce_never_substitutes_for_successful_shell_execution(tmp_path):
    event = {
        "type": "item.completed",
        "item": {
            "type": "command_execution",
            "command": "printf nonce",
            "aggregated_output": "nonce",
            "exit_code": -1,
            "status": "failed",
        },
    }
    (tmp_path / "events.jsonl").write_text(json.dumps(event) + "\n")
    with pytest.raises(RuntimeError, match="completed successful nonce"):
        _successful_nonce_command(tmp_path, "nonce")
