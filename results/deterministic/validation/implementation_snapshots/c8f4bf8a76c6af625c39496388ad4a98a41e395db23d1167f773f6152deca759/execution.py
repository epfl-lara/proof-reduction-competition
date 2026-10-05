"""Host-owned, resumable execution of native tool agents.

Adapters supply commands, environment, and terminal parsing. This module owns
locks, start markers, logs and filesystem isolation, without selecting proofs.
"""

from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from proof_eval.evidence.io import now, write_json
from proof_eval.paths import PACKAGE

from .contracts import ToolSession
from .isolation import launch_command


@dataclass(frozen=True)
class Launch:
    """An explicit native agent launch; credentials are never serialized."""

    argv: list[str]
    environment: dict[str, str]
    runtime_paths: tuple[Path, ...]
    cwd: Path
    parse: Callable[[list[dict], str, int], dict]
    capacity: Callable[[], AbstractContextManager] = nullcontext


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
    identity: dict,
    provider: str,
    authentication: str,
    build: Callable[[Path, Path, Path, Path], Launch],
) -> dict:
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if [m["role"] for m in messages] != ["system", "user"]:
        raise ValueError("Expected system and user messages")
    if identity != expected_cli:
        raise ValueError(f"{provider} executable or configuration changed")
    timeout = 1800 if mode == "correctness" else None  # Historical control only.
    request = {
        "provider": provider,
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
        "sampling_policy": "native_cli_default_no_override",
        "tool_context": context,
        "auth": authentication,
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
                "usage": None,
                "error": "Started request without terminal output; not resampled",
            }
            write_json(folder / "generation.json", result)
            return result
        workspace = folder / "workspace"
        workspace.mkdir(exist_ok=True)
        write_json(workspace / "context.json", context)
        (workspace / "tools.py").write_text((PACKAGE / "harness/client.py").read_text())
        (workspace / "candidate.lean").write_text(session.seed_code)
        system_file, prompt_file = folder / "system.txt", folder / "prompt.txt"
        system_file.write_text(messages[0]["content"])
        prompt_file.write_text(messages[1]["content"])
        last_message = workspace / "final.txt"
        launch = build(workspace, system_file, last_message, folder)
        protected = list(context["source_projects"].values())
        isolation = dict(runtime_paths=launch.runtime_paths)
        subprocess.run(
            launch_command(
                [sys.executable, "-c", "pass"], workspace, protected, **isolation
            ),
            check=True,
            capture_output=True,
        )
        argv = launch_command(launch.argv, workspace, protected, **isolation)
        write_json(
            folder / "command.json",
            {
                "argv": argv,
                "cwd": str(launch.cwd),
                "policy": "host_ledger_readonly_sources",
            },
        )
        started = time.monotonic()
        # Holding one slot until the native session exits conservatively bounds
        # the sequential requests made by that session across all host batches.
        with (
            launch.capacity() as capacity_fd,
            tool_service(session, workspace),
            (folder / "events.jsonl").open("w") as out,
            (folder / "stderr.log").open("w") as err,
        ):
            write_json(folder / "request_started.json", {"started_at": now()})
            child = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=out,
                stderr=err,
                cwd=launch.cwd,
                env=launch.environment,
                text=True,
                start_new_session=True,
                pass_fds=() if capacity_fd is None else (capacity_fd,),
            )
            write_json(folder / "process.json", {"pid": child.pid, "started_at": now()})
            try:
                child.communicate(prompt_file.read_text(), timeout=timeout)
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
                "usage": None,
                "error": "Correctness control timed out; not resampled",
            }
        else:
            try:
                events = [
                    json.loads(line)
                    for line in (folder / "events.jsonl").read_text().splitlines()
                    if line.strip()
                ]
                final = last_message.read_text() if last_message.exists() else ""
                result = launch.parse(events, final, child.returncode)
                if result["status"] == "received" and not last_message.exists():
                    last_message.write_text(result["content"])
            except (OSError, ValueError, KeyError) as error:
                result = {
                    "status": "transport_error",
                    "error": str(error),
                    "usage": None,
                }
        result.update(
            provider=provider,
            elapsed_seconds=time.monotonic() - started,
            finished_at=now(),
        )
        write_json(folder / "generation.json", result)
        return result
