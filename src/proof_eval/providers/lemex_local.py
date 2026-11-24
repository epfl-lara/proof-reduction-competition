"""Native Lemex against an explicitly selected local vLLM Responses server."""

from __future__ import annotations

import json
import os
import re
import socket
from pathlib import Path
from urllib.request import urlopen

from proof_eval.evidence.io import digest, write_json

from . import (
    capture_proxy,
    execution,
    lemex,
    native_resources,
    readonly_mounts,
    responses,
    signal_scope,
)
from .events import cli_identity as executable_identity
from .events import parse_events as parse_native_events
from .events import terminal as terminal
from .execution import Launch

MODEL = "Qwen/Qwen3.8-Flash-Next-FP8"
THINKINGCAP_MODEL = "bottlecapai/ThinkingCap-Qwen3.8-Flash-Next-FP8"
PROOFOPT_SFT_MODEL = "EPFL-LARA/Qwen3.8-Flash-Next-ProofOpt-SFT-step148-FP8"
MODELS = {
    m: {"low", "medium", "xhigh"}
    for m in (MODEL, THINKINGCAP_MODEL, PROOFOPT_SFT_MODEL)
}


def parse_events(events, final, returncode):
    """Local native turns may finish after tools/reasoning without answer text.

    This records no returned proof. The time-tracked host can start another
    optimization turn from its verified incumbent under the same deadline.
    """
    return parse_native_events(events, final, returncode, allow_empty_final=True)


def home() -> Path:
    """Resolve an isolated profile; never read or change gateway credentials."""
    value = os.environ.get("PROOF_LEMEX_LOCAL_HOME")
    if not value:
        raise ValueError(
            "Set PROOF_LEMEX_LOCAL_HOME to the prepared local Lemex profile"
        )
    return Path(value).resolve(strict=True)


def cli_identity() -> dict:
    import tomllib

    scope = signal_scope.configured_identity()
    profile = home()
    config = tomllib.loads((profile / "config.toml").read_text())
    provider = config["model_providers"][config["model_provider"]]
    endpoint = provider["base_url"].rstrip("/")
    with urlopen(endpoint + "/models", timeout=5) as response:
        models = json.load(response)
    served = {m["id"] for m in models["data"]}
    if not served.intersection(MODELS):
        raise ValueError("Local vLLM does not serve the pinned FP8 model")
    catalog = profile / "models.json"
    manifest = profile.parent / "server_manifest.json"
    return {
        **executable_identity("lemex"),
        "home": str(profile),
        "served_models": sorted(served),
        "base_url": endpoint,
        "catalog_path": str(catalog),
        "catalog_sha256": digest(catalog),
        "config_sha256": digest(profile / "config.toml"),
        "context_settings": lemex.context_settings(profile / "config.toml"),
        "authentication_source": "local_server_no_api_key",
        "terminal_schema_version": 2,
        "ownership_schema_version": 2,
        "signal_scope": scope,
        "native_resources": native_resources.identity(),
        "filesystem_guard": readonly_mounts.identity(),
        "server_manifest_sha256": digest(manifest) if manifest.exists() else None,
    }


def environment(profile: Path) -> dict[str, str]:
    """Use the isolated native defaults and omit unrelated remote API keys."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("RCP_", "LEMEX_", "PROOF_LEMEX_CAPTURE_"))
        and not k.startswith("PROOF_SIGNAL_SCOPE_")
        and k
        not in {
            "OPENAI_API_KEY",
            "PROOF_LEMEX_LOCAL_CAPACITY_NAMESPACE",
            readonly_mounts.ENVIRONMENT,
        }
    }
    env["LEMEX_HOME"] = str(profile)
    return env


def command(
    *, model: str, effort: str, mode: str, catalog: Path, base_url: str, **kwargs
) -> list[str]:
    if model not in MODELS or effort not in MODELS[model] or mode != "score_edges":
        raise ValueError("Unsupported local Lemex condition")
    argv = responses.command(
        model=model,
        effort=effort,
        load_user_config=True,
        settings={
            "include_environment_context": True,
            "model_catalog_json": str(catalog),
            "model_provider": "local_qwen",
            "model_providers.local_qwen.name": "Local Qwen via vLLM",
            "model_providers.local_qwen.base_url": base_url,
            "model_providers.local_qwen.wire_api": "responses",
            "model_providers.local_qwen.requires_openai_auth": False,
            "model_providers.local_qwen.supports_websockets": False,
            "model_providers.local_qwen.capabilities.remote_compaction": "unsupported",
        },
        **kwargs,
    )
    argv.insert(1, "--no-daemon")
    return argv


def _capacity(slots: int = 5):
    """Limit local sessions independently on each host or pod."""
    if type(slots) is not int or not 1 <= slots <= 128:
        raise ValueError("Local native capacity must be an integer from 1 to 128")
    directory = Path.home() / ".proof-arena/lemex-local-slots" / socket.gethostname()
    namespace = os.environ.get("PROOF_LEMEX_LOCAL_CAPACITY_NAMESPACE")
    if namespace is not None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", namespace):
            raise ValueError("Invalid local capacity namespace")
        directory = directory / namespace
    return lemex.capacity(directory=directory, slots=slots)


def generate(*, capacity_slots: int = 5, **kwargs) -> dict:
    identity = cli_identity()
    profile = Path(identity["home"])
    if kwargs["model"] not in identity["served_models"]:
        raise ValueError("Local server does not serve the requested model")

    def build(workspace, system_file, last_message, folder):
        endpoint = identity["base_url"]
        env = environment(profile)
        capture = os.environ.get("PROOF_LEMEX_CAPTURE_ENDPOINT")
        if capture:
            token = os.environ.get("PROOF_LEMEX_CAPTURE_REGISTRATION_TOKEN")
            if not token:
                raise ValueError("Capture registration credential is missing")
            metadata = {
                "provider": "lemex-local",
                "model": kwargs["model"],
                "effort": kwargs["effort"],
                "task": getattr(kwargs.get("session"), "row", {}).get("name"),
                "cell": folder.parent.name,
                "attempt": folder.name,
                "attempt_directory": str(folder),
                "request_sha256": digest(folder / "request.json"),
            }
            endpoint = capture_proxy.register_attempt(capture, token, metadata)
            trace = workspace / "rollout-traces"
            trace.mkdir(exist_ok=True)
            env["CODEX_ROLLOUT_TRACE_ROOT"] = str(trace)
            write_json(
                folder / "capture.json",
                {
                    "base_url": endpoint,
                    "native_trace_root": str(trace),
                    "attribution": metadata,
                },
            )
        return Launch(
            argv=command(
                binary=identity["path"],
                workspace=workspace,
                system_file=system_file,
                last_message=last_message,
                catalog=Path(identity["catalog_path"]),
                base_url=endpoint,
                **{k: kwargs[k] for k in ("model", "effort", "mode", "instructions")},
            ),
            environment=env,
            runtime_paths=(profile,),
            cwd=workspace,
            parse=parse_events,
            capacity=lambda: _capacity(capacity_slots),
        )

    return execution.generate(
        **kwargs,
        identity=identity,
        provider="lemex-local",
        authentication="local_server_no_api_key",
        build=build,
    )
