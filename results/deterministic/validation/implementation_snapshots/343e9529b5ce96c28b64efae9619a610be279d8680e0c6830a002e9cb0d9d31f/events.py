"""Executable identities and Codex-compatible terminal event parsing."""

import hashlib
import shutil
import subprocess
from pathlib import Path

DISABLED = (
    "apps",
    "plugins",
    "memories",
    "multi_agent",
    "multi_agent_v2",
    "goals",
    "hooks",
    "skill_search",
    "skill_mcp_dependency_install",
    "recommended_plugins",
    "unbounded_connection_retries",
)


def cli_identity(name: str = "codex") -> dict:
    binary = Path(shutil.which(name) or name).resolve(strict=True)
    return {
        "path": str(binary),
        "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "version": subprocess.check_output(
            [str(binary), "--version"], text=True
        ).strip(),
    }


def parse_events(events, final, returncode):
    turns = [e for e in events if e.get("type") == "turn.completed"]
    bad = [e for e in events if e.get("type") in {"error", "turn.failed"}]
    items = [e["item"] for e in events if e.get("type") == "item.completed"]
    tools = [e for e in items if e.get("type") not in {"agent_message", "reasoning"}]
    messages = [e.get("text", "") for e in items if e.get("type") == "agent_message"]
    if (
        returncode
        or bad
        or len(turns) != 1
        or not final.strip()
        or not messages
        or messages[-1].strip() != final.strip()
    ):
        return {
            "status": "transport_error",
            "error": "Codex did not produce one complete final",
            "returncode": returncode,
            "completed_turns": len(turns),
            "tool_items": len(tools),
            "events_errors": bad,
            "usage": turns[-1].get("usage") if turns else None,
        }
    usage = turns[0].get("usage", {})
    return {
        "status": "received",
        "content": final,
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": usage.get("input_tokens"),
            "completion_tokens": usage.get("output_tokens"),
            "cached_input_tokens": usage.get("cached_input_tokens"),
        },
        "codex_usage": usage,
        "token_usage": usage,
        "completed_turns": 1,
        "tool_items": len(tools),
        "tool_item_types": [t.get("type") for t in tools],
    }
