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
    cost_budget: dict | None = None,
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
    if cost_budget is not None:
        if cost_budget["kind"] != "native_usd":
            raise ValueError("Expected a native Claude dollar guard")
        argv += ["--max-budget-usd", str(cost_budget["remaining_usd"])]
    return argv


def token_usage(
    raw: dict, *, model_usage: dict | None = None, schema_version: int = 2
) -> dict | None:
    """Anthropic input excludes cached tokens; normalize to the common total."""
    if type(schema_version) is not int or schema_version not in (1, 2):
        raise ValueError("Unsupported Claude usage schema version")
    keys = (
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    )
    if not isinstance(raw, dict) or any(
        type(raw.get(k)) is not int or raw[k] < 0 for k in keys
    ):
        return None
    values = {
        "input_tokens": raw["input_tokens"]
        + raw["cache_read_input_tokens"]
        + raw["cache_creation_input_tokens"],
        "cached_input_tokens": raw["cache_read_input_tokens"],
        "cache_write_input_tokens": raw["cache_creation_input_tokens"],
        "output_tokens": raw["output_tokens"],
        # Zero denotes an unreported subset unless modelUsage certifies it.
        "reasoning_output_tokens": 0,
    }
    if schema_version == 1:
        return values
    cache = raw.get("cache_creation")
    if isinstance(cache, dict):
        hour, short = (
            cache.get("ephemeral_1h_input_tokens"),
            cache.get("ephemeral_5m_input_tokens"),
        )
        if (
            type(hour) is int
            and type(short) is int
            and min(hour, short) >= 0
            and hour + short == values["cache_write_input_tokens"]
        ):
            values["cache_write_1h_input_tokens"] = hour
    reasoning = _reasoning_tokens(model_usage, values["output_tokens"])
    if reasoning is not None:
        values["reasoning_output_tokens"] = reasoning
    return values


def _reasoning_tokens(model_usage: dict | None, output_tokens: int) -> int | None:
    """Use thinking counters only when they cover all reported output."""
    if not isinstance(model_usage, dict) or not model_usage:
        return None
    outputs, reasoning = 0, 0
    for item in model_usage.values():
        if not isinstance(item, dict):
            return None
        total, subset = item.get("outputTokens"), item.get("thinkingTokens")
        if (
            type(total) is not int
            or type(subset) is not int
            or not 0 <= subset <= total
        ):
            return None
        outputs += total
        reasoning += subset
    return reasoning if outputs == output_tokens else None


def _result_usage(result: dict, schema_version: int) -> dict:
    raw = result.get("usage") or {}
    usage = token_usage(
        raw, model_usage=result.get("modelUsage"), schema_version=schema_version
    )
    cost = result.get("total_cost_usd")
    if type(cost) not in (float, int) or not math.isfinite(cost) or cost < 0:
        cost = None
    counters = {
        "prompt_tokens": usage["input_tokens"] if usage else None,
        "completion_tokens": usage["output_tokens"] if usage else None,
        "cached_input_tokens": usage["cached_input_tokens"] if usage else None,
    }
    return {
        "token_usage": usage,
        "claude_usage": raw,
        "cli_cost_usd": cost,
        **(
            {
                "usage_schema_version": 2,
                "cache_write_ttl_reported": usage is not None
                and "cache_write_1h_input_tokens" in usage,
            }
            if schema_version == 2
            else {}
        ),
        "reasoning_usage_reported": schema_version == 2
        and usage is not None
        and _reasoning_tokens(result.get("modelUsage"), usage["output_tokens"])
        is not None,
        "usage": counters if usage or schema_version == 1 else None,
    }


def parse_events(
    events: list[dict],
    final: str,
    returncode: int,
    *,
    model: str = MODEL,
    usage_schema_version: int = 2,
) -> dict:
    if type(usage_schema_version) is not int or usage_schema_version not in (1, 2):
        raise ValueError("Unsupported Claude usage schema version")
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
    if usage_schema_version == 2:
        # Failed or limited sessions can still have charged, reported usage.
        # Preserve it without reclassifying the request as a success.
        base.update(_result_usage(result, usage_schema_version))
    if (
        returncode
        or len(init) != 1
        or len(terminal) != 1
        or result.get("is_error") is not False
        or result.get("subtype") != "success"
        or not isinstance(result.get("result"), str)
        or not result["result"].strip()
        or (
            usage_schema_version == 2
            and (
                not isinstance(base["session_id"], str)
                or not base["session_id"].strip()
                or init[0].get("session_id", base["session_id"]) != base["session_id"]
            )
        )
    ):
        return {
            **base,
            "status": "transport_error",
            "usage": base.get("usage"),
            "error": "Claude Code did not produce one successful terminal result",
        }
    if base["actual_model"] != model:
        return {
            **base,
            "status": "model_mismatch",
            "usage": base.get("usage"),
            "error": f"Requested {model}, received {base['actual_model']}",
        }
    # A tool denial may be recovered using another authorized tool, just like
    # a failed Lean check. Preserve it, but do not invent a transport failure
    # when the CLI reports successful completion. The host verifies the proof.
    if final.strip() and final.strip() != result["result"].strip():
        raise ValueError("Saved final differs from the Claude terminal result")
    return {
        **base,
        **(_result_usage(result, 1) if usage_schema_version == 1 else {}),
        "status": "received",
        "content": result["result"],
        "finish_reason": "stop",
        "tool_outcome": (
            "completed_with_denials" if base["permission_denials"] else "completed"
        ),
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
                cost_budget=kwargs.get("cost_budget"),
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
