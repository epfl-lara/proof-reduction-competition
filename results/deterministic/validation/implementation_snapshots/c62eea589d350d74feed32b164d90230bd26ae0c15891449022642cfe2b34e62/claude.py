"""Claude Code adapter with exact model/effort and inspected terminal evidence."""

from __future__ import annotations

import math
import os
from pathlib import Path

from proof_eval.paths import ROOT

from . import execution
from .events import cli_identity as executable_identity
from .execution import Launch

MODEL = "claude-opus-5-5"


def cli_identity() -> dict:
    return executable_identity("claude")


def command(
    *,
    binary: str,
    workspace: Path,
    system_file: Path,
    tool_file: Path,
    model: str,
    effort: str,
    source_projects: list[str],
) -> list[str]:
    if model != MODEL or effort != "max":
        raise ValueError("The Claude condition is claude-opus-5-5/max")
    # Normal project configuration/authentication discovery is retained. This
    # benchmark deliberately excludes unrelated MCP servers and extra agents.
    tools = "Bash,Read,Write,Edit,Glob,Grep"
    allowed = [
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
        "Bash(python " + str(workspace / "tools.py") + " *)",
        "Bash(python tools.py *)",
        "Bash(python *)",
        "Bash(python3 *)",
        "Bash(rg *)",
        "Bash(grep *)",
        "Bash(cat *)",
        "Bash(sed *)",
        "Bash(ls *)",
        "Bash(head *)",
        "Bash(tail *)",
        "Bash(pwd)",
    ]
    argv = [
        str(binary),
        "-p",
        "--model",
        model,
        "--effort",
        effort,
        "--output-format",
        "stream-json",
        "--verbose",
        "--system-prompt-file",
        str(system_file),
        "--append-system-prompt-file",
        str(tool_file),
        "--tools",
        tools,
        "--allowedTools",
        *allowed,
        "--permission-mode",
        "dontAsk",
        "--permission-prompts",
        "none",
        "--strict-mcp-config",
        "--no-chrome",
        "--no-session-persistence",
    ]
    for directory in sorted({str(workspace), *source_projects}):
        argv += ["--add-dir", directory]
    return argv


def token_usage(raw: dict) -> dict | None:
    """Anthropic input excludes cached tokens; normalize to the common total."""
    keys = (
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    )
    if any(type(raw.get(k)) is not int or raw[k] < 0 for k in keys):
        return None
    return {
        "input_tokens": raw["input_tokens"]
        + raw["cache_read_input_tokens"]
        + raw["cache_creation_input_tokens"],
        "cached_input_tokens": raw["cache_read_input_tokens"],
        "cache_write_input_tokens": raw["cache_creation_input_tokens"],
        "output_tokens": raw["output_tokens"],
        # The CLI doesn't separate reasoning. It is already part of output;
        # zero here denotes an unreported subset, not zero reasoning usage.
        "reasoning_output_tokens": 0,
    }


def parse_events(
    events: list[dict], final: str, returncode: int, *, model: str = MODEL
) -> dict:
    init = [
        e for e in events if e.get("type") == "system" and e.get("subtype") == "init"
    ]
    terminal = [e for e in events if e.get("type") == "result"]
    tools = [
        b
        for e in events
        if e.get("type") == "assistant"
        for b in e.get("message", {}).get("content", [])
        if b.get("type") == "tool_use"
    ]
    result = terminal[-1] if terminal else {}
    base = {
        "returncode": returncode,
        "session_id": result.get("session_id"),
        "actual_model": init[0].get("model") if len(init) == 1 else None,
        "claude_result": result,
        "completed_turns": len(terminal),
        "tool_items": len(tools),
        "tool_item_types": [t.get("name") for t in tools],
        "permission_denials": result.get("permission_denials", []),
    }
    if (
        returncode
        or len(init) != 1
        or len(terminal) != 1
        or result.get("is_error") is not False
        or result.get("subtype") != "success"
        or not isinstance(result.get("result"), str)
        or not result["result"].strip()
    ):
        return {
            **base,
            "status": "transport_error",
            "usage": None,
            "error": "Claude Code did not produce one successful terminal result",
        }
    if base["actual_model"] != model:
        return {
            **base,
            "status": "model_mismatch",
            "usage": None,
            "error": f"Requested {model}, received {base['actual_model']}",
        }
    # A tool denial may be recovered using another authorized tool, just like
    # a failed Lean check. Preserve it, but do not invent a transport failure
    # when the CLI reports successful completion. The host verifies the proof.
    if final.strip() and final.strip() != result["result"].strip():
        raise ValueError("Saved final differs from the Claude terminal result")
    raw = result.get("usage") or {}
    usage = token_usage(raw)
    cost = result.get("total_cost_usd")
    if (
        not isinstance(cost, (int, float))
        or isinstance(cost, bool)
        or not math.isfinite(cost)
        or cost < 0
    ):
        cost = None
    return {
        **base,
        "status": "received",
        "content": result["result"],
        "finish_reason": "stop",
        "token_usage": usage,
        "claude_usage": raw,
        "cli_cost_usd": cost,
        "tool_outcome": (
            "completed_with_denials" if base["permission_denials"] else "completed"
        ),
        "reasoning_usage_reported": False,
        "usage": {
            "prompt_tokens": usage["input_tokens"] if usage else None,
            "completion_tokens": usage["output_tokens"] if usage else None,
            "cached_input_tokens": usage["cached_input_tokens"] if usage else None,
        },
    }


def generate(**kwargs) -> dict:
    identity = cli_identity()

    def build(workspace, system_file, last_message, folder):
        tool_file = folder / "tool_instructions.txt"
        tool_file.write_text(
            kwargs["instructions"]
            + "\nYour isolated writable workspace is "
            + str(workspace)
            + ".\n"
            + "The process starts in the repository. Use absolute workspace paths for Read/Write/Edit, and run `python "
            + str(workspace / "tools.py")
            + " check "
            + str(workspace / "candidate.lean")
            + "` (and similarly for other tool operations). Do not edit repository files.\n"
        )
        return Launch(
            argv=command(
                binary=identity["path"],
                workspace=workspace,
                system_file=system_file,
                tool_file=tool_file,
                model=kwargs["model"],
                effort=kwargs["effort"],
                source_projects=list(kwargs["context"]["source_projects"].values()),
            ),
            environment={
                k: v
                for k, v in os.environ.items()
                if not k.startswith(("RCP_", "LEMEX_"))
            },
            runtime_paths=(Path.home() / ".claude", Path.home() / ".claude.json"),
            cwd=ROOT,
            parse=parse_events,
        )

    return execution.generate(
        **kwargs,
        identity=identity,
        provider="claude",
        authentication="existing_claude_code_login",
        build=build,
    )
