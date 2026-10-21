"""Native Lemex agent adapter; no direct chat client or sampling policy.

Existing gateway credentials may be bridged from the repository's .env into
the child-only LEMEX_API_KEY. No credential is written to experiment evidence.
"""

from __future__ import annotations

import fcntl
import os
import shlex
import time
from contextlib import contextmanager
from pathlib import Path

from proof_eval.evidence.io import digest
from proof_eval.paths import ROOT

from . import execution, responses
from .events import cli_identity as executable_identity
from .events import parse_events
from .events import terminal as terminal
from .execution import Launch
from .retries import REQUEST_MAX_RETRIES, STREAM_MAX_RETRIES

MODEL = "deepseek-ai/DeepSeek-V4.1-Flash"
MODELS = {
    MODEL: {"low", "medium", "high"},
    "Qwen/Qwen3.8-Flash-Next": {"low", "medium", "xhigh"},
}
# Host admission state must live outside model-writable CLI/cache directories.
SLOT_DIRECTORY = Path.home() / ".proof-arena/lemex-slots"
SLOT_COUNT = 5


def environment(env_path: Path = ROOT / ".env") -> dict[str, str]:
    """Read only literal assignments, never source or execute a credential file."""
    env = dict(os.environ)
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip().removeprefix("export ")
            key, separator, value = line.partition("=")
            if (
                separator
                and key
                in {"LEMEX_API_KEY", "LEMEX_BASE_URL", "RCP_API_KEY", "RCP_BASE_URL"}
                and key not in env
            ):
                parts = shlex.split(value, comments=True)
                if len(parts) != 1:
                    raise ValueError(
                        "Expected a single literal credential/config value"
                    )
                env[key] = parts[0]
    key = env.get("LEMEX_API_KEY") or env.get("RCP_API_KEY")
    if not key:
        raise ValueError("Set LEMEX_API_KEY or supply the existing gateway key in .env")
    endpoint = (
        env.get("LEMEX_BASE_URL")
        or env.get("RCP_BASE_URL")
        or "https://inference.rcp.epfl.ch/v1"
    )
    clean = {k: v for k, v in env.items() if not k.startswith(("RCP_", "LEMEX_"))}
    clean.update(LEMEX_API_KEY=key, LEMEX_BASE_URL=endpoint)
    return clean


def cli_identity() -> dict:
    env = environment()
    catalog = (
        Path(
            os.environ.get(
                "PROOF_EVAL_LEMEX_CATALOG", Path.home() / ".lemex/models.json"
            )
        )
        .expanduser()
        .resolve(strict=True)
    )
    return {
        **executable_identity("lemex"),
        "base_url": env["LEMEX_BASE_URL"],
        "catalog_path": str(catalog),
        "catalog_sha256": digest(catalog),
    }


def command(
    *, model: str, effort: str, mode: str, catalog: Path, base_url: str, **kwargs
) -> list[str]:
    if model not in MODELS or effort not in MODELS[model] or mode != "score_edges":
        raise ValueError("Unsupported Lemex model, effort or search mode")
    settings = {
        "model_catalog_json": str(catalog),
        "model_provider": "lemex_gateway",
        "model_providers.lemex_gateway.name": "Lemex gateway",
        "model_providers.lemex_gateway.base_url": base_url,
        "model_providers.lemex_gateway.env_key": "LEMEX_API_KEY",
        "model_providers.lemex_gateway.wire_api": "responses",
        "model_providers.lemex_gateway.requires_openai_auth": False,
        "model_providers.lemex_gateway.supports_websockets": False,
        "model_providers.lemex_gateway.request_max_retries": REQUEST_MAX_RETRIES,
        "model_providers.lemex_gateway.stream_max_retries": STREAM_MAX_RETRIES,
    }
    return responses.command(model=model, effort=effort, settings=settings, **kwargs)


@contextmanager
def capacity():
    """At most five native sessions across concurrent host batches on this machine."""
    directory = SLOT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    while True:
        for i in range(SLOT_COUNT):
            lock = (directory / f"{i}.lock").open("a")
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                lock.close()
                continue
            try:
                # The executor also passes this descriptor to the native CLI.
                # An orphaned live CLI keeps its slot if the host exits.
                yield lock.fileno()
            finally:
                lock.close()
            return
        time.sleep(0.2)


def generate(**kwargs) -> dict:
    identity = cli_identity()

    def build(workspace, system_file, last_message, folder):
        return Launch(
            argv=command(
                binary=identity["path"],
                workspace=workspace,
                system_file=system_file,
                last_message=last_message,
                catalog=Path(identity["catalog_path"]),
                base_url=identity["base_url"],
                **{k: kwargs[k] for k in ("model", "effort", "mode", "instructions")},
            ),
            environment=environment(),
            runtime_paths=(Path.home() / ".lemex",),
            cwd=workspace,
            parse=parse_events,
            capacity=capacity,
        )

    return execution.generate(
        **kwargs,
        identity=identity,
        provider="lemex",
        authentication="child_environment_gateway_key",
        build=build,
    )
