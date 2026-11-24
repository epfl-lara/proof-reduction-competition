"""Google Antigravity (``agy``) CLI adapter with explicit prompt transport.

Antigravity print mode has no system-prompt channel, so the harness system
policy, tool instructions and user message are concatenated into one prompt and
passed to ``-p``. Those sections therefore reach this provider as user-level
instructions. Selection evidence comes from the stream-json ``init`` event; it
records the requested model selection, not the backend identity.
"""

from __future__ import annotations

import os
from functools import partial
from pathlib import Path

from . import execution
from .costs import USAGE_FIELDS
from .events import cli_identity as executable_identity
from .execution import Launch

MODEL = "gemini-3.8-flash"
MODELS = {MODEL: {"low", "medium", "high"}}
AGENT = "code"
SUCCESS = "SUCCESS"
# A single argv element must stay below the Linux limit (131072 bytes); fail
# loudly rather than surfacing an opaque E2BIG from the child process.
MAX_PROMPT_BYTES = 120_000
USAGE_COUNTERS = (
    "input_tokens",
    "output_tokens",
    "thinking_tokens",
    "cache_read_tokens",
)


def cli_identity() -> dict:
    return executable_identity("agy")


def slug(model: str, effort: str) -> str:
    if model not in MODELS or effort not in MODELS[model]:
        raise ValueError(
            "The Antigravity condition is a supported gemini-3.x slug and effort"
        )
    return model + "-" + effort


def environment() -> dict[str, str]:
    """Preserve the existing login; never leak another provider's credentials."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("RCP_", "LEMEX_"))}
    env["AGY_CLI_DISABLE_AUTO_UPDATE"] = "true"
    return env


def runtime_paths() -> tuple[Path, ...]:
    """Login state and PTY devices required by the native command tool.

    /dev/ptmx allocates a terminal; its slave devices live in /dev/pts. Both
    paths are needed on hosts where /dev/ptmx is a separate device inode.
    Source projects and host evidence remain read-only.
    """
    return (Path.home() / ".gemini", Path("/dev/ptmx"), Path("/dev/pts"))


def command(
    *,
    binary: str,
    workspace: Path,
    prompt: str,
    model: str,
    effort: str,
    source_projects: list[str],
) -> list[str]:
    selected = slug(model, effort)
    if len(prompt.encode()) > MAX_PROMPT_BYTES:
        raise ValueError(
            "Merged Antigravity prompt exceeds the safe command-line limit"
        )
    argv = [
        str(binary),
        "--output-format",
        "stream-json",
        "--agent",
        AGENT,
        "--model",
        selected,
        "--dangerously-skip-permissions",
        "--disable-slash-commands",
        "--log-file",
        str(workspace / "agy.log"),
    ]
    for directory in sorted({str(workspace), *source_projects}):
        argv += ["--add-dir", str(directory)]
    return argv + ["-p=" + prompt]


def terminal(event: object) -> bool:
    """The streaming terminal record; recognized by deadline recovery."""
    return isinstance(event, dict) and event.get("event") == "result"


def token_usage(raw: dict | None) -> dict | None:
    """Normalize reported counters; Antigravity omits cache writes here.

    Reported input excludes cache reads, so the common total adds them back and
    keeps a zero cache-write placeholder that the usage validator accepts.
    """
    if not isinstance(raw, dict) or any(
        type(raw.get(k)) is not int or raw[k] < 0 for k in USAGE_COUNTERS
    ):
        return None
    reads = raw["cache_read_tokens"]
    usage = {
        "input_tokens": raw["input_tokens"] + reads,
        "cached_input_tokens": reads,
        "cache_write_input_tokens": 0,
        "output_tokens": raw["output_tokens"],
        "reasoning_output_tokens": raw["thinking_tokens"],
    }
    if usage["reasoning_output_tokens"] > usage["output_tokens"]:
        return None
    return usage


def stream_usage(events: list[dict]) -> dict | None:
    """Observed usage: replace per-step snapshots; never add the session total.

    ACTIVE/DONE updates can repeat one step's usage. The terminal result instead
    reports the whole conversation. Before that result, the sum is a lower
    bound because in-flight and unreported steps are unknown.
    """
    inits = [e for e in events if e.get("event") == "init"]
    if len(inits) != 1 or not isinstance(inits[0].get("conversation_id"), str):
        return None
    conversation = inits[0]["conversation_id"]
    steps = {}
    for event in events:
        if event.get("event") == "result":
            result = event.get("result")
            if (
                isinstance(result, dict)
                and result.get("conversation_id") == conversation
            ):
                usage = token_usage(result.get("usage"))
                if usage is not None:
                    return usage
        step = event.get("step_update")
        if (
            event.get("event") != "step_update"
            or not isinstance(step, dict)
            or step.get("conversation_id") != conversation
            or type(step.get("step_index")) is not int
            or step["step_index"] < 0
        ):
            continue
        usage = token_usage(step.get("usage"))
        if usage is not None:
            steps[step["step_index"]] = usage
    if not steps:
        return None
    return {
        field: sum(usage[field] for usage in steps.values()) for field in USAGE_FIELDS
    }


def parse_events(
    events: list[dict],
    final: str,
    returncode: int,
    *,
    requested_slug: str | None = None,
) -> dict:
    events = [e for e in events if isinstance(e, dict)]
    inits = [e for e in events if e.get("event") == "init"]
    results = [e for e in events if e.get("event") == "result"]
    steps = [
        e["step_update"]
        for e in events
        if e.get("event") == "step_update" and isinstance(e.get("step_update"), dict)
    ]
    tools = [s for s in steps if s.get("step_type") == "tool"]
    terminal_result = (
        results[-1]["result"]
        if results and isinstance(results[-1].get("result"), dict)
        else {}
    )
    init = (
        inits[0]["init"]
        if len(inits) == 1 and isinstance(inits[0].get("init"), dict)
        else {}
    )
    raw_usage = (
        terminal_result.get("usage")
        if isinstance(terminal_result.get("usage"), dict)
        else None
    )
    denied = terminal_result.get("denied_actions")
    conversation_id = terminal_result.get("conversation_id")
    base = {
        "returncode": returncode,
        "conversation_id": conversation_id,
        "actual_model": init.get("model"),
        "requested_model": requested_slug,
        "agy_result": terminal_result,
        "agy_usage": raw_usage,
        "token_usage": token_usage(raw_usage) if results else stream_usage(events),
        "usage_complete": len(results) == 1 and token_usage(raw_usage) is not None,
        "cache_write_reported": False,
        "completed_turns": len(results),
        "tool_items": len(tools),
        "tool_item_types": [t.get("tool_name") for t in tools],
        "denied_actions": denied if isinstance(denied, list) else [],
    }
    if (
        returncode
        or len(inits) != 1
        or len(results) != 1
        or terminal_result.get("status") != SUCCESS
        or not isinstance(terminal_result.get("response"), str)
        or not terminal_result["response"].strip()
        or not isinstance(conversation_id, str)
        or not conversation_id.strip()
        or conversation_id
        != (inits[0].get("conversation_id") if len(inits) == 1 else None)
    ):
        return {
            **base,
            "status": "transport_error",
            "error": "Antigravity did not produce one successful terminal result",
        }
    # Missing selection evidence is not a mismatch; contradictory evidence is.
    if (
        requested_slug is not None
        and base["actual_model"] is not None
        and base["actual_model"] != requested_slug
    ):
        return {
            **base,
            "status": "model_mismatch",
            "error": f"Requested {requested_slug}, received {base['actual_model']}",
        }
    if final.strip() and final.strip() != terminal_result["response"].strip():
        raise ValueError("Saved final differs from the Antigravity terminal result")
    return {
        **base,
        "status": "received",
        "content": terminal_result["response"],
        "finish_reason": "stop",
        "tool_outcome": (
            "completed_with_denials" if base["denied_actions"] else "completed"
        ),
    }


def generate(**kwargs) -> dict:
    identity = cli_identity()

    def build(workspace, system_file, last_message, folder):
        requested = slug(kwargs["model"], kwargs["effort"])
        prompt = "\n\n".join(
            part.rstrip()
            for part in (
                system_file.read_text(),
                kwargs["instructions"],
                (folder / "prompt.txt").read_text(),
            )
            if part.strip()
        )
        return Launch(
            argv=command(
                binary=identity["path"],
                workspace=workspace,
                prompt=prompt,
                model=kwargs["model"],
                effort=kwargs["effort"],
                source_projects=list(kwargs["context"]["source_projects"].values()),
            ),
            environment=environment(),
            runtime_paths=runtime_paths(),
            cwd=workspace,
            parse=partial(parse_events, requested_slug=requested),
            stream_usage=stream_usage,
        )

    return execution.generate(
        **kwargs,
        identity=identity,
        provider="agy",
        authentication="existing_antigravity_login",
        build=build,
    )
