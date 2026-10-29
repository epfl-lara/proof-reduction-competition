"""Portable, immutable native-local profiles; preparing one starts no model."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from proof_eval.defaults import (
    LOCAL_QWEN_WORKERS,
    QWEN_COMPACTION_TOKENS,
    QWEN_CONTEXT_TOKENS,
    QWEN_TIMEOUT_SECONDS,
    VERIFICATION_TIMEOUT_SECONDS,
)
from proof_eval.evidence.io import digest, read, write_json

from .lemex_local import MODEL, MODELS, PROOFOPT_SFT_MODEL, THINKINGCAP_MODEL
from .vllm_server import REVISION, ServerConfig

REVISIONS = {
    MODEL: REVISION,
    THINKINGCAP_MODEL: "ca9f7a5ca400d8eff644a99a0803f2ba968fb05b",
    PROOFOPT_SFT_MODEL: "f4097c298a5eb404531fed0b7c60df1787e0e895",
}


def prepare(
    folder: Path,
    *,
    model: str = MODEL,
    revision: str | None = None,
    model_cache: Path | None = None,
    workers: int = LOCAL_QWEN_WORKERS,
    seconds: int = QWEN_TIMEOUT_SECONDS,
    context: int = QWEN_CONTEXT_TOKENS,
    compaction: int = QWEN_COMPACTION_TOKENS,
    verification_timeout_seconds: float = VERIFICATION_TIMEOUT_SECONDS,
    port: int = 8128,
    binary: str = "vllm",
    server_python: str | None = None,
) -> dict:
    """Create a new explicit recipe without changing the user's native home."""
    if (
        model not in MODELS
        or type(workers) is not int
        or not 1 <= workers <= 128
        or type(seconds) is not int
        or seconds <= 0
        or not 0 < compaction < context
        or type(verification_timeout_seconds) not in (int, float)
        or not 0 < verification_timeout_seconds < float("inf")
    ):
        raise ValueError("Invalid local model, capacity, deadline or context")
    revision = revision or REVISIONS[model]
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("Pin the full model revision SHA")
    server = ServerConfig(
        mode="mtp3",
        model=model,
        revision=revision,
        binary=binary,
        python=server_python,
        model_cache=str(model_cache or Path.home() / ".cache/huggingface"),
        port=port,
        max_model_len=context,
        max_num_seqs=workers,
        gpu_memory_utilization=0.95,
        profile="rcp-api-flags",
        execution_mode="compiled",
    )
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False, mode=0o700)
    catalog = read(Path(__file__).with_name("local_catalog.json"))
    entry = catalog["models"][0]
    entry.update(
        slug=model,
        display_name=model,
        context_window=context,
        max_context_window=context,
        description="Explicit local vLLM profile; native sampling defaults",
    )
    write_json(folder / "models.json", catalog)
    config = (
        f'model_provider = "local_qwen"\nmodel = {json.dumps(model)}\n'
        f'model_catalog_json = {json.dumps(str(folder / "models.json"))}\n'
        f'model_reasoning_effort = "xhigh"\nmodel_context_window = {context}\n'
        f"model_auto_compact_token_limit = {compaction}\n"
        'show_raw_agent_reasoning = true\nweb_search = "disabled"\n'
        "[features]\nplugins = false\nremote_plugin = false\n"
        "recommended_plugins = false\ntool_suggest = false\n"
        '[model_providers.local_qwen]\nname = "Local Qwen via vLLM"\n'
        f'base_url = {json.dumps(server.endpoint)}\nwire_api = "responses"\n'
        "requires_openai_auth = false\nsupports_websockets = false\n"
        "request_max_retries = 0\nstream_max_retries = 0\n"
        "stream_idle_timeout_ms = 600000\n"
        '[model_providers.local_qwen.capabilities]\nremote_compaction = "unsupported"\n'
        "[analytics]\nenabled = false\n[feedback]\nenabled = false\n"
    )
    (folder / "config.toml").write_text(config)
    value = {
        "schema_version": 1,
        "model": model,
        "revision": revision,
        "workers": workers,
        "seconds": seconds,
        "verification_timeout_seconds": verification_timeout_seconds,
        "context": context,
        "compaction": compaction,
        "effort": "xhigh",
        "restart_history": False,
        "deterministic_cleanup": False,
        "server": asdict(server),
        "files": {n: digest(folder / n) for n in ("models.json", "config.toml")},
        "model_calls": 0,
    }
    write_json(folder / "profile.json", value)
    return value


def load(folder: Path) -> tuple[dict, ServerConfig]:
    """Reject edited native settings instead of silently resuming another recipe."""
    folder = Path(folder).resolve()
    value = read(folder / "profile.json")
    if value.get("schema_version") != 1:
        raise ValueError("Unknown local profile schema")
    if set(value["files"]) != {"models.json", "config.toml"} or any(
        digest(folder / name) != pin for name, pin in value["files"].items()
    ):
        raise ValueError("Frozen local profile changed; prepare another directory")
    server = ServerConfig(**value["server"])
    verification = value.get(
        "verification_timeout_seconds", VERIFICATION_TIMEOUT_SECONDS
    )
    if type(verification) not in (int, float) or not 0 < verification < float("inf"):
        raise ValueError("Invalid frozen verification timeout")
    if (
        server.model != value["model"]
        or server.revision != value["revision"]
        or server.max_num_seqs != value["workers"]
        or server.max_model_len != value["context"]
        or value["effort"] != "xhigh"
        or value["restart_history"] is not False
        or value["deterministic_cleanup"] is not False
    ):
        raise ValueError(
            "Profile recipe differs from its frozen server/native settings"
        )
    return value, server
