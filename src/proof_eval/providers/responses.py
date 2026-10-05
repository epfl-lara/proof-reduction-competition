"""Shared command builder for native Responses-based agent CLIs."""

from __future__ import annotations

import json
from pathlib import Path

from .events import DISABLED


def command(
    *,
    binary: str,
    workspace: Path,
    system_file: Path,
    last_message: Path,
    model: str,
    effort: str,
    instructions: str,
    settings: dict | None = None,
) -> list[str]:
    """Retain native shell/edit tools with one explicit task policy.

    Neither CLI exposes a sampling-temperature override here. In particular,
    this does not reproduce the old direct client's temperature of 0.3.
    """
    config = {
        "model_reasoning_effort": effort,
        "model_reasoning_summary": "none",
        "model_instructions_file": str(system_file),
        "developer_instructions": instructions,
        "include_environment_context": False,
        "include_permissions_instructions": False,
        "include_collaboration_mode_instructions": False,
        "include_apps_instructions": False,
        "skills.include_instructions": False,
        "skills.bundled.enabled": False,
        "project_doc_max_bytes": 0,
        "web_search": "disabled",
        "agents.enabled": False,
        "tools.update_plan.enabled": False,
        "approval_policy": "never",
        "tools.experimental_request_user_input.enabled": False,
        "check_for_update_on_startup": False,
        **(settings or {}),
    }
    argv = [
        str(binary),
        "exec",
        "--ignore-user-config",
        "--ignore-rules",
        "--strict-config",
        "--ephemeral",
        "--skip-git-repo-check",
        "--sandbox",
        "danger-full-access",
        "--color",
        "never",
        "--json",
        "-C",
        str(workspace),
        "-m",
        model,
        "-o",
        str(last_message),
    ]
    for key, value in config.items():
        argv += ["-c", key + "=" + json.dumps(value)]
    for feature in DISABLED:
        argv += ["--disable", feature]
    return argv + ["-"]
