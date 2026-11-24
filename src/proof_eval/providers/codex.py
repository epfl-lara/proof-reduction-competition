"""Native Codex adapter for the shared durable agent executor."""

from __future__ import annotations

import os
import re
from pathlib import Path

from proof_eval.evidence.io import digest

from . import execution, responses
from .events import cli_identity as executable_identity
from .events import parse_events
from .events import terminal as terminal
from .execution import Launch
from .response_usage import SCHEMA_VERSION, TRACE_DIRECTORY, reconcile_usage
from .spending import codex_budget_settings

MODELS = {
    "gpt-6-astra": {"max", "high", "low"},
    "gpt-6-luna": {"max"},
    "gpt-6.1-sol": {"max"},
}


def cli_identity() -> dict:
    """Pin the native CLI and reject incomplete copies before a model request."""
    identity = executable_identity()
    version = re.match(r"codex-cli (\d+)\.(\d+)\.", identity["version"])
    if version and tuple(map(int, version.groups())) >= (0, 162):
        binary = Path(identity["path"])
        candidates = (
            binary.parent.parent / "codex-resources/codex-code-mode-host",
            binary.parent / "codex-resources/codex-code-mode-host",
            binary.parent / "codex-code-mode-host",
        )
        companion = next((path for path in candidates if path.is_file()), None)
        if companion is None or not os.access(companion, os.X_OK):
            raise ValueError(
                "Incomplete Codex CLI bundle: missing executable codex-code-mode-host; "
                "copy the complete CLI bundle before preparing a run"
            )
        identity["companions"] = {
            "codex-code-mode-host": {
                "path": str(companion.resolve()),
                "sha256": digest(companion),
            }
        }
        identity["response_usage_schema_version"] = SCHEMA_VERSION
    return identity


def command(
    *, mode: str, model: str, effort: str, service_tier: str = "standard", **kwargs
) -> list[str]:
    if (
        model not in MODELS
        or effort not in MODELS[model]
        or mode not in ("correctness", "score", "score_edges")
    ):
        raise ValueError("Unsupported model, effort or experiment mode")
    if service_tier not in ("standard", "fast"):
        raise ValueError("Unsupported Codex service tier")
    if service_tier == "fast":
        kwargs["settings"] = {**(kwargs.get("settings") or {}), "service_tier": "fast"}
    return responses.command(model=model, effort=effort, **kwargs)


def generate(*, service_tier: str = "standard", **kwargs) -> dict:
    if service_tier not in ("standard", "fast"):
        raise ValueError("Unsupported Codex service tier")
    identity = cli_identity()

    def build(workspace, system_file, last_message, folder):
        traced = identity.get("response_usage_schema_version") in (1, 2)

        def parse(events, final, returncode):
            result = parse_events(events, final, returncode)
            return (
                reconcile_usage(
                    folder,
                    events,
                    kwargs["model"],
                    result,
                    schema_version=identity["response_usage_schema_version"],
                )
                if traced
                else result
            )

        return Launch(
            argv=command(
                binary=identity["path"],
                workspace=workspace,
                system_file=system_file,
                last_message=last_message,
                settings=codex_budget_settings(kwargs.get("cost_budget")),
                service_tier=service_tier,
                **{k: kwargs[k] for k in ("model", "effort", "mode", "instructions")},
            ),
            environment={
                **{
                    k: v
                    for k, v in os.environ.items()
                    if not k.startswith(("RCP_", "LEMEX_"))
                    and k != "CODEX_ROLLOUT_TRACE_ROOT"
                },
                **(
                    {"CODEX_ROLLOUT_TRACE_ROOT": str(folder / TRACE_DIRECTORY)}
                    if traced
                    else {}
                ),
            },
            runtime_paths=(
                Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))),
            ),
            cwd=workspace,
            parse=parse,
        )

    return execution.generate(
        **kwargs,
        identity=identity,
        provider="codex",
        authentication="existing_codex_login",
        service_tier="fast" if service_tier == "fast" else None,
        build=build,
    )
