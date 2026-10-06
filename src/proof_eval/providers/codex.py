"""Native Codex adapter for the shared durable agent executor."""

from __future__ import annotations

import os
from pathlib import Path

from . import execution, responses
from .events import cli_identity, parse_events
from .execution import Launch
from .spending import codex_budget_settings

MODELS = {
    "gpt-6-astra": {"max", "high", "low"},
    "gpt-6-luna": {"max"},
    "gpt-6.1-sol": {"max"},
}


def command(*, mode: str, model: str, effort: str, **kwargs) -> list[str]:
    if (
        model not in MODELS
        or effort not in MODELS[model]
        or mode not in ("correctness", "score", "score_edges")
    ):
        raise ValueError("Unsupported model, effort or experiment mode")
    return responses.command(model=model, effort=effort, **kwargs)


def generate(**kwargs) -> dict:
    identity = cli_identity()

    def build(workspace, system_file, last_message, folder):
        return Launch(
            argv=command(
                binary=identity["path"],
                workspace=workspace,
                system_file=system_file,
                last_message=last_message,
                settings=codex_budget_settings(kwargs.get("cost_budget")),
                **{k: kwargs[k] for k in ("model", "effort", "mode", "instructions")},
            ),
            environment={
                k: v
                for k, v in os.environ.items()
                if not k.startswith(("RCP_", "LEMEX_"))
            },
            runtime_paths=(
                Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))),
            ),
            cwd=workspace,
            parse=parse_events,
        )

    return execution.generate(
        **kwargs,
        identity=identity,
        provider="codex",
        authentication="existing_codex_login",
        build=build,
    )
