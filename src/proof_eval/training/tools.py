"""Early readiness of the unchanged host tools and explicit offline assets."""

from __future__ import annotations

import os
from pathlib import Path

from proof_eval.evidence.immutable import canonical, read, sha


def freeze_host_tools(plan: dict) -> dict:
    """Hash all explicit assets and run one CPU embedding query, never policy inference."""
    from proof_eval.harness import semantic, web

    assets = plan["semantic_assets"]
    root = Path(assets["root"]).resolve()
    manifest_path = root / "manifest.json"
    if sha(manifest_path) != assets["manifest_sha256"]:
        raise ValueError("Semantic asset manifest changed")
    manifest = read(manifest_path)
    index = root / assets["index_version"]
    embedding = root / assets["embedding_revision"]
    # LeanExplore reads these at its first import, including in trainer children.
    os.environ["LEAN_EXPLORE_CACHE_DIR"] = str(root)
    os.environ["LEAN_EXPLORE_VERSION"] = assets["index_version"]
    frozen = semantic.freeze(semantic.SemanticSearchConfig(index, embedding))
    expected = {str(root / rel): v["sha256"] for rel, v in manifest["files"].items()}
    if frozen["asset_sha256"] != expected or any(
        (root / rel).stat().st_size != value["bytes"]
        for rel, value in manifest["files"].items()
    ):
        raise ValueError("Semantic assets differ from the explicit manifest")
    probe = assets["probe"]
    found = semantic.search(
        frozen,
        Path(probe["project"]),
        {"query": "sum of natural numbers", "limit": 2},
        probe["version"],
    )
    if found["count"] < 1:
        raise RuntimeError("Actual local semantic query returned no declarations")
    return {
        "semantic_config": frozen,
        "web_config": web.freeze(),
        "probe": found,
        "asset_manifest_sha256": sha(manifest_path),
        "policy_model_calls": 0,
        "embedding_model_calls": 1,
        "embedding_device": "cpu",
    }


def verify_search_after_training_patch(plan: dict, release: Path, tools: dict) -> dict:
    """Replay a saved tool request after the real Megatron RoPE registration."""
    import hashlib
    from types import SimpleNamespace

    from mcore_bridge.model.rope import get_rope_inv_freq
    from transformers.modeling_rope_utils import ROPE_INIT_FUNCTIONS

    from proof_eval.training.data import task_id, validate_reserve
    from proof_eval.training.semantic_process import search_isolated
    from proof_eval.verification.references import required_versions

    get_rope_inv_freq(
        SimpleNamespace(
            multi_latent_attention=False,
            partial_rotary_factor=1.0,
            kv_channels=128,
            rope_scaling=None,
            rotary_base=10000.0,
            max_position_embeddings=32768,
            original_max_position_embeddings=None,
            hidden_size=1024,
            num_attention_heads=8,
        )
    )
    bridge_function = ROPE_INIT_FUNCTIONS["default"]
    if not bridge_function.__module__.startswith("mcore_bridge"):
        raise RuntimeError("Actual Megatron RoPE registration was not exercised")
    spec = plan["semantic_regression"]
    row = next(
        r
        for r in validate_reserve(release / "dataset")
        if task_id(r) == spec["task_id"]
    )
    version = spec["request"].get("version") or required_versions({"row": row})[0]
    environment = read(Path(plan["source_environments"]))
    project = next(
        p["path"]
        for p in environment["projects"]
        if p["source"] == row["source"] and p["version"] == version
    )
    request_pin = hashlib.sha256(canonical(spec["request"])).hexdigest()
    if request_pin != spec["request_sha256"]:
        raise ValueError("Saved failing semantic request changed")
    response = search_isolated(
        tools["semantic_config"],
        Path(project),
        spec["request"],
        version,
        Path(plan["home"]) / "post-training-import-tool-regression",
        timeout_seconds=180,
    )
    if ROPE_INIT_FUNCTIONS["default"] is not bridge_function:
        raise RuntimeError("Tool regression changed the policy's RoPE registry")
    return {
        "status": "passed",
        "request_sha256": request_pin,
        "task_id": spec["task_id"],
        "version": version,
        "response": response,
        "parent_rope_unchanged": True,
        "parent_training_patch_present": True,
        "policy_model_calls": 0,
        "embedding_model_calls": 1,
    }
