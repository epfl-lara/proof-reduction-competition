"""Early readiness of the unchanged host tools and explicit offline assets."""

from __future__ import annotations

import os
from pathlib import Path

from proof_eval.evidence.immutable import read, sha


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
