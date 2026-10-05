"""Durable Codex agent transport, with explicit model and tool-service inputs.

Started requests without terminal evidence are never automatically resampled.
Score search has no imposed total token, attempt or wall-time cap.
"""

from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Callable

from proof_eval.evidence.io import now, write_json
from proof_eval.paths import PACKAGE

from .contracts import ToolSession
from .events import DISABLED, cli_identity, parse_events
from .isolation import launch_command

MODELS = {
    "gpt-6-astra": {"max", "high", "low"},
    "gpt-6-luna": {"max"},
    "gpt-6.1-sol": {"max"},
}


def command(
    *, binary, workspace, system_file, last_message, model, effort, mode, instructions
):
    if (
        model not in MODELS
        or effort not in MODELS[model]
        or mode not in ("correctness", "score", "score_edges")
    ):
        raise ValueError("Unsupported model, effort or experiment mode")
    settings = {
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
    }
    result = [
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
    for key, value in settings.items():
        result += ["-c", key + "=" + json.dumps(value)]
    for feature in DISABLED:
        result += ["--disable", feature]
    return result + ["-"]


def generate(
    *,
    folder: Path,
    messages: list[dict[str, str]],
    model: str,
    effort: str,
    mode: str,
    session: ToolSession,
    context: dict,
    expected_cli: dict,
    instructions: str,
    tool_service: Callable[[ToolSession, Path], AbstractContextManager],
) -> dict:
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if [m["role"] for m in messages] != ["system", "user"]:
        raise ValueError("Expected system and user messages")
    identity = cli_identity()
    if identity != expected_cli:
        raise ValueError("Codex executable changed")
    # Retain the historical one-proposal timeout only in the correctness control.
    timeout = 1800 if mode == "correctness" else None
    request = {
        "messages": messages,
        "model": model,
        "reasoning_effort": effort,
        "mode": mode,
        "tool_instructions": instructions,
        "cli": identity,
        "timeout": timeout,
        "max_attempts": None,
        "max_output_tokens": None,
        "temperature": None,
        "tool_context": context,
        "auth": "existing_codex_login",
    }
    with (folder / ".generation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = folder / "request.json"
        if path.exists() and json.loads(path.read_text()) != request:
            raise ValueError("Saved agent request changed")
        write_json(path, request)
        if (folder / "generation.json").exists():
            return json.loads((folder / "generation.json").read_text())
        if (folder / "request_started.json").exists():
            result = {
                "status": "indeterminate",
                "error": "Started request without terminal output; not resampled",
                "usage": None,
            }
            write_json(folder / "generation.json", result)
            return result
        workspace = folder / "workspace"
        workspace.mkdir(exist_ok=True)
        write_json(workspace / "context.json", context)
        (workspace / "tools.py").write_text((PACKAGE / "harness/client.py").read_text())
        (workspace / "candidate.lean").write_text(session.seed_code)
        (folder / "system.txt").write_text(messages[0]["content"])
        (folder / "prompt.txt").write_text(messages[1]["content"])
        base = command(
            binary=identity["path"],
            workspace=workspace,
            system_file=folder / "system.txt",
            last_message=workspace / "final.txt",
            model=model,
            effort=effort,
            mode=mode,
            instructions=instructions,
        )
        protected = list(context["source_projects"].values())
        # The model may write only its workspace/runtime. The host-owned ledger,
        # requests, system prompt and input evidence are outside this writable root.
        subprocess.run(
            launch_command([sys.executable, "-c", "pass"], workspace, protected),
            check=True,
            capture_output=True,
        )
        args = launch_command(base, workspace, protected)
        write_json(
            folder / "command.json",
            {"argv": args, "policy": "host_ledger_readonly_sources"},
        )
        env = {k: v for k, v in os.environ.items() if not k.startswith("RCP_")}
        started = time.monotonic()
        with (
            tool_service(session, workspace),
            (folder / "events.jsonl").open("w") as out,
            (folder / "stderr.log").open("w") as err,
        ):
            write_json(folder / "request_started.json", {"started_at": now()})
            child = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=out,
                stderr=err,
                cwd=workspace,
                env=env,
                text=True,
                start_new_session=True,
            )
            write_json(folder / "process.json", {"pid": child.pid, "started_at": now()})
            try:
                child.communicate(messages[1]["content"], timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                timed_out = True
        if timed_out:
            result = {
                "status": "indeterminate",
                "error": "Correctness control timed out; not resampled",
                "usage": None,
            }
        else:
            try:
                events = [
                    json.loads(line)
                    for line in (folder / "events.jsonl").read_text().splitlines()
                    if line.strip()
                ]
                final = (
                    (workspace / "final.txt").read_text()
                    if (workspace / "final.txt").exists()
                    else ""
                )
                result = parse_events(events, final, child.returncode)
            except (OSError, ValueError) as error:
                result = {
                    "status": "transport_error",
                    "error": str(error),
                    "usage": None,
                }
        result.update(elapsed_seconds=time.monotonic() - started, finished_at=now())
        write_json(folder / "generation.json", result)
        return result
