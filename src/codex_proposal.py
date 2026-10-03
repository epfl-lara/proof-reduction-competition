"""One Codex agent proposal, with durable no-resampling records.

The benchmark prompt replaces built-in instructions; tools remain available at
the user's request. An isolated workspace supplies source paths and a validity
checker, without scores or outputs from other experiment conditions.
CLI output-token and temperature controls are not available: record this rather
than claiming parity with an RCP request's 32768/.3 settings.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from run_deterministic import write_json
from run_validity_repair import now


MODELS = {"gpt-6-astra": {"max"}, "gpt-6-luna": {"max", "high", "medium"}}
DISABLED = ("apps", "plugins", "memories", "multi_agent", "multi_agent_v2",
            "goals", "hooks", "skill_search", "skill_mcp_dependency_install",
            "recommended_plugins", "unbounded_connection_retries")
TOOL_INSTRUCTIONS = """Tools are enabled for this proof-refactoring attempt.
The supplied workspace has context.json with pinned Lean project/source paths
and check_candidate.py. Write a complete proposed declaration to candidate.lean,
then run `python check_candidate.py candidate.lean` to check every required Lean
version. It returns correctness feedback only. You may inspect the listed source
projects and their dependencies and use other available tools as needed.
Keep imported source files unchanged. Do not inspect experiment results, other
model outputs, benchmark caches, credentials, or files outside the supplied
source projects and your workspace. Do not run deterministic optimization scripts
or request candidate performance scores. Make one optimization proposal; use
compiler feedback only to debug its validity, not to search for a better score.
Return the complete declaration as your final message under the original output
contract. Tool access and any in-turn debugging are recorded separately from the
outer harness's at-most-three correctness repair calls.
"""


def cli_identity():
    binary = Path(shutil.which("codex") or "codex").resolve(strict=True)
    return {"path": str(binary), "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "version": subprocess.check_output([str(binary), "--version"], text=True).strip()}


def command(*, binary, workspace, system_file, last_message, model, effort):
    if model not in MODELS or effort not in MODELS[model]:
        raise ValueError("Unsupported benchmark model/effort")
    settings = {
        "model_reasoning_effort": effort, "model_reasoning_summary": "none",
        "model_instructions_file": str(system_file), "developer_instructions": TOOL_INSTRUCTIONS,
        "include_environment_context": False, "include_permissions_instructions": False,
        "include_collaboration_mode_instructions": False, "include_apps_instructions": False,
        "skills.include_instructions": False, "skills.bundled.enabled": False,
        "project_doc_max_bytes": 0, "web_search": "cached", "agents.enabled": False,
        "tools.update_plan.enabled": False, "approval_policy": "never",
        "tools.experimental_request_user_input.enabled": False,
        "check_for_update_on_startup": False,
    }
    cmd = [str(binary), "exec", "--ignore-user-config", "--ignore-rules", "--strict-config",
           "--ephemeral", "--skip-git-repo-check", "--sandbox", "danger-full-access",
           "--color", "never", "--json", "-C", str(workspace), "-m", model,
           "-o", str(last_message)]
    for key, value in settings.items():
        cmd += ["-c", key + "=" + json.dumps(value)]
    for feature in DISABLED:
        cmd += ["--disable", feature]
    root = Path(__file__).resolve().parent.parent
    for writable in (root / '.proof-eval', root / '.proof-eval-projects'):
        cmd += ["--add-dir", str(writable)]
    return cmd + ["-"]


def parse_events(events, final, returncode):
    turns = [e for e in events if e.get("type") == "turn.completed"]
    bad = [e for e in events if e.get("type") in {"error", "turn.failed"}]
    items = [e["item"] for e in events if e.get("type") == "item.completed"]
    tools = [e for e in items if e.get("type") not in {"agent_message", "reasoning"}]
    messages = [e.get("text", "") for e in items if e.get("type") == "agent_message"]
    if returncode or bad or len(turns) != 1 or not final.strip() or not messages or messages[-1].strip() != final.strip():
        return {"status": "transport_error", "error": "Codex did not produce one complete final",
                "returncode": returncode, "completed_turns": len(turns), "tool_items": len(tools),
                "events_errors": bad, "usage": turns[-1].get("usage") if turns else None}
    usage = turns[0].get("usage", {})
    return {"status": "received", "content": final, "finish_reason": "stop",
            "usage": {"prompt_tokens": usage.get("input_tokens"),
                      "completion_tokens": usage.get("output_tokens"),
                      "cached_input_tokens": usage.get("cached_input_tokens")},
            "codex_usage": usage, "completed_turns": 1, "tool_items": len(tools),
            "tool_item_types": [t.get('type') for t in tools]}


def generate_once(*, folder, messages, model="gpt-6-astra", effort="max", timeout=1800,
                  expected_cli=None, tool_context=None):
    folder = Path(folder).resolve()
    if [m.get("role") for m in messages] != ["system", "user"] or any(not isinstance(m.get("content"), str) for m in messages):
        raise ValueError("Expected exactly system and user text messages")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Timeout must be finite and positive")
    if model not in MODELS or effort not in MODELS[model]:
        raise ValueError("Unsupported benchmark model/effort")
    identity = cli_identity()
    if expected_cli is not None and identity != expected_cli:
        raise ValueError("Codex CLI identity changed")
    request = {"messages": messages, "model": model, "reasoning_effort": effort,
               "transport": "codex_exec", "cli": identity, "timeout": timeout,
               "temperature": None, "max_output_tokens": None,
               "control_limitations": "Codex CLI exposes neither a hard output-token cap nor temperature; do not claim RCP budget parity.",
               "disabled_features": list(DISABLED), "tool_instructions": TOOL_INSTRUCTIONS,
               "tool_context": tool_context}
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".generation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        request_path = folder / "request.json"
        if request_path.exists() and json.loads(request_path.read_text()) != request:
            raise ValueError("Saved Codex request changed")
        write_json(request_path, request)
        saved = folder / "generation.json"
        if saved.exists():
            return json.loads(saved.read_text())
        marker = folder / "request_started.json"
        if marker.exists():
            result = {"status": "indeterminate", "error": "Started Codex request without saved result; not resampled", "usage": None}
        else:
            write_json(marker, {"started_at": now()})
            (folder / "system.txt").write_text(messages[0]["content"])
            (folder / "prompt.txt").write_text(messages[1]["content"])
            started = time.monotonic()
            workspace = folder / 'workspace'
            workspace.mkdir(exist_ok=True)
            write_json(workspace / 'context.json', tool_context or {})
            root = Path(__file__).resolve().parent.parent
            helper = (root / 'src/codex_validity_tool.py').read_text()
            (workspace / 'check_candidate.py').write_text(helper)
            empty = str(workspace)
            cmd = command(binary=identity["path"], workspace=empty, system_file=folder / "system.txt",
                          last_message=folder / "final.txt", model=model, effort=effort)
            write_json(folder / "command.json", {"argv": cmd, "cwd_kind": "isolated_proof_workspace", "auth": "existing_codex_login"})
            # Never pass RCP credentials into the proposal process. Do not
            # modify the user's saved Codex configuration or authentication.
            env = {k: v for k, v in os.environ.items() if not k.startswith("RCP_")}
            with (folder / "events.jsonl").open("w") as out, (folder / "stderr.log").open("w") as err:
                child = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                         cwd=empty, env=env, text=True, start_new_session=True)
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
                result = {"status": "indeterminate", "error": "Codex timeout; not resampled", "usage": None}
            else:
                try:
                    events = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines() if line.strip()]
                    final = (folder / "final.txt").read_text() if (folder / "final.txt").exists() else ""
                    result = parse_events(events, final, child.returncode)
                except (ValueError, OSError) as exc:
                    result = {"status": "transport_error", "error": type(exc).__name__, "usage": None}
            result.update(elapsed_seconds=time.monotonic() - started, finished_at=now())
        write_json(saved, result)
        return result
