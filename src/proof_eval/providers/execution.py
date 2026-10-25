"""Host-owned, resumable execution of native tool agents.

Adapters supply commands, environment, and terminal parsing. This module owns
locks, start markers, logs and filesystem isolation, without selecting proofs.
"""

from __future__ import annotations

import fcntl
import json
import subprocess
import sys
import time
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from proof_eval.evidence.io import fingerprint, now, write_json
from proof_eval.paths import PACKAGE

from . import deadline_cleanup, signal_scope
from .contracts import ToolSession
from .isolation import launch_command
from .monitoring import UsageReader, communicate_with_budget, read_events
from .processes import owned_command, owned_identity, process_identity, stop_tree
from .retries import owned_client_eof
from .spending import native_cost_stop
from .termination import record_exit


@dataclass(frozen=True)
class Launch:
    """An explicit native agent launch; credentials are never serialized."""

    argv: list[str]
    environment: dict[str, str]
    runtime_paths: tuple[Path, ...]
    cwd: Path
    parse: Callable[[list[dict], str, int], dict]
    capacity: Callable[[], AbstractContextManager] = nullcontext
    stream_usage: UsageReader | None = None


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
    timeout: float | None = 57 * 60,
    cost_budget: dict | None = None,
) -> dict:
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if [m["role"] for m in messages] != ["system", "user"]:
        raise ValueError("Expected system and user messages")
    if identity != expected_cli:
        raise ValueError(f"{provider} executable or configuration changed")
    scoped = provider == "lemex-local"
    scope_identity = identity.get("signal_scope")
    if scoped:
        signal_scope.validate_identity(scope_identity)
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
    if cost_budget is not None:
        request["cost_budget"] = cost_budget
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
        (workspace / "candidate.lean").write_text(session.best_code)
        system_file, prompt_file = folder / "system.txt", folder / "prompt.txt"
        system_file.write_text(messages[0]["content"])
        prompt_file.write_text(messages[1]["content"])
        last_message = workspace / "final.txt"
        launch = build(workspace, system_file, last_message, folder)
        protected = list(context["source_projects"].values())
        isolation = dict(runtime_paths=launch.runtime_paths)
        if provider == "lemex-local":
            isolation["process_boundary"] = "signal_scope"
        probe_argv = launch_command(
            [sys.executable, "-c", "pass"], workspace, protected, **isolation
        )
        writable = (workspace, *launch.runtime_paths)
        scope_preflight = None
        if scoped:
            scope_preflight = signal_scope.preflight(
                probe_argv,
                folder / "signal_scope_preflight",
                scope_identity,
                writable,
                launch.environment,
            )
        else:
            subprocess.run(probe_argv, check=True, capture_output=True)
        isolated_argv = launch_command(launch.argv, workspace, protected, **isolation)
        argv = (
            signal_scope.wrap(isolated_argv, folder, scope_identity, writable)
            if scoped
            else isolated_argv
        )
        ownership_path = folder / "process_ownership.json"
        started = time.monotonic()
        # Holding one slot until the native session exits conservatively bounds
        # the sequential requests made by that session across all host batches.
        with (
            launch.capacity() as capacity_fd,
            tool_service(session, workspace),
            (folder / "events.jsonl").open("w") as out,
            (folder / "stderr.log").open("w") as err,
        ):
            if not scoped:
                argv = launch_command(
                    launch.argv,
                    workspace,
                    protected,
                    lifetime_fd=capacity_fd,
                    **isolation,
                )
            write_json(
                folder / "command.json",
                {
                    "argv": argv,
                    "cwd": str(launch.cwd),
                    "policy": (
                        "host_ledger_readonly_sources_signal_scope_v1"
                        if scoped
                        else "private_pid_namespace_landlock_host_ledger"
                    ),
                    **(
                        {
                            "signal_scope": scope_identity,
                            "signal_scope_preflight": scope_preflight,
                            "isolated_argv": isolated_argv,
                        }
                        if scoped
                        else {}
                    ),
                },
            )
            write_json(folder / "request_started.json", {"started_at": now()})
            pass_fds = () if capacity_fd is None else (capacity_fd,)
            child = subprocess.Popen(
                (
                    owned_command(argv, ownership_path, pass_fds)
                    if provider == "lemex-local"
                    else argv
                ),
                stdin=subprocess.PIPE,
                stdout=out,
                stderr=err,
                cwd=launch.cwd,
                env=launch.environment,
                text=True,
                start_new_session=True,
                pass_fds=pass_fds,
            )
            process = {
                "pid": child.pid,
                "started_at": now(),
                "identity": process_identity(child.pid),
            }
            if provider == "lemex-local":
                process.update(
                    owned_identity(child.pid),
                    native_supervisor=True,
                    ownership_schema_version=2,
                    signal_scope=scope_identity,
                )
            write_json(folder / "process.json", process)
            cost_stop = None
            monitor_error = None
            stopped = None
            try:
                if cost_budget is not None and cost_budget["kind"] == "host_stream_usd":
                    if launch.stream_usage is None:
                        raise ValueError("Host stream guard requires a usage decoder")
                    cost_stop = communicate_with_budget(
                        child,
                        prompt_file.read_text(),
                        timeout,
                        folder,
                        cost_budget,
                        launch.stream_usage,
                    )
                else:
                    child.communicate(prompt_file.read_text(), timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                stopped = stop_tree(child.pid)
                child.wait(timeout=5)
                if provider == "lemex-local":
                    deadline_cleanup.save_native_stop(
                        folder, process, stopped, returncode=child.returncode
                    )
                timed_out = True
            except (OSError, ValueError, KeyError) as error:
                stop_tree(child.pid)
                child.wait(timeout=5)
                monitor_error = str(error)
                timed_out = False
            # Commit this before draining outstanding host tools or decoding a
            # possibly truncated event stream, so abnormal exits cannot hide.
            native_limit = False
            if cost_budget is not None and child.returncode:
                try:
                    native_limit = native_cost_stop(
                        provider,
                        read_events(folder / "events.jsonl", allow_partial=True),
                        cost_budget,
                    )
                except (OSError, ValueError, KeyError):
                    pass  # Still preserve the raw exit when events are unreadable.
            observed_exit = child.returncode
            if provider == "lemex-local" and ownership_path.exists():
                observed_exit = json.loads(ownership_path.read_text())[
                    "native_returncode"
                ]
            exit_record = record_exit(
                folder,
                observed_exit,
                timed_out=timed_out,
                cost_stopped=cost_stop is not None or native_limit,
                monitor_error=monitor_error,
            )
        try:
            events = read_events(
                folder / "events.jsonl",
                allow_partial=timed_out or cost_stop is not None,
            )
            final = last_message.read_text() if last_message.exists() else ""
            ownership = None
            if provider == "lemex-local" and ownership_path.exists():
                ownership = json.loads(ownership_path.read_text())
                expected_owner = {k: process[k] for k in ("pid", "start_ticks")}
                if ownership.get("supervisor") != expected_owner:
                    raise ValueError(
                        "Native ownership receipt changed process identity"
                    )
            result = launch.parse(
                events,
                final,
                (
                    ownership["native_returncode"]
                    if ownership is not None
                    else child.returncode
                ),
            )
            scope_error = None
            if scoped:
                try:
                    result["signal_scope"] = {
                        "status": "verified",
                        **signal_scope.evidence(
                            folder,
                            scope_identity,
                            isolated_argv,
                            process,
                            ownership,
                            allow_partial=timed_out,
                        ),
                    }
                except (OSError, ValueError, KeyError) as error:
                    scope_error = str(error)
                    result["signal_scope"] = {
                        "status": "unverified",
                        "error": scope_error,
                    }
                write_json(folder / "signal_scope.json", result["signal_scope"])
            if ownership is not None:
                result.update(
                    process_ownership=ownership,
                    supervisor_returncode=child.returncode,
                )
                if not ownership.get("cleanup", {}).get("complete"):
                    result.update(
                        status="transport_error",
                        error="Native descendants could not be fully reaped; not resampled",
                    )
                elif (
                    child.returncode == 0
                    and result["status"] == "transport_error"
                    and not timed_out
                    and cost_stop is None
                    and monitor_error is None
                    and scope_error is None
                    and owned_client_eof(events)
                ):
                    # The service context has also exited: accepted host Lean
                    # checks are drained before the next attempt can start.
                    result.update(
                        error="Owned native client exited during an active turn",
                        owned_client_eof={
                            "schema_version": 1,
                            "reason": "active_native_event_stream_eof",
                            "tool_service_drained": True,
                            "ownership_sha256": fingerprint(ownership),
                        },
                    )
                if ownership.get("supervisor_signals") and not timed_out:
                    result.pop("owned_client_eof", None)
                    result.update(
                        status="transport_error",
                        external_supervisor_signal=True,
                        error="Native supervisor received an external signal; not resampled",
                    )
            elif provider == "lemex-local" and not timed_out:
                result.update(
                    status="transport_error",
                    error="Native client has no complete ownership receipt; not resampled",
                )
            if (
                (
                    native_cost_stop(provider, events, cost_budget)
                    or cost_stop is not None
                )
                and not timed_out
                and (provider != "claude" or result.get("actual_model") == model)
                and (
                    provider != "agy"
                    or result.get("actual_model") in (None, model + "-" + effort)
                )
            ):
                result.update(
                    status="budget_exhausted",
                    termination="cost_limit",
                    cost_budget=cost_budget,
                    error="Cost guard stopped the attempt; not resampled",
                )
                if cost_stop is not None:
                    result["host_cost_stop_sha256"] = fingerprint(cost_stop)
            if timed_out:
                result.update(
                    status="budget_exhausted",
                    error="Native agent reached the problem time limit; not resampled",
                )
                if provider == "lemex-local":
                    result["host_deadline_cleanup"] = deadline_cleanup.record(
                        folder, process, stopped, source="native_timeout"
                    )
            if monitor_error is not None:
                result.update(status="transport_error", error=monitor_error)
            if scope_error is not None:
                result.pop("owned_client_eof", None)
                result.update(status="transport_error", error=scope_error)
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
            returncode=result.get("returncode", observed_exit),
            process_exit=exit_record,
            elapsed_seconds=time.monotonic() - started,
            finished_at=now(),
        )
        write_json(folder / "generation.json", result)
        return result
