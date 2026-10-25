"""Missing packages/assets fail before reserving GPUs or preparing originals."""

import json
from unittest.mock import patch

import pytest

from proof_eval.evidence.immutable import sha
from proof_eval.harness import semantic, web
from proof_eval.training.tools import freeze_host_tools


def fixture_assets(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAN_EXPLORE_CACHE_DIR", "test-original")
    monkeypatch.setenv("LEAN_EXPLORE_VERSION", "test-original")
    data = tmp_path / "index" / "lean_explore.db"
    data.parent.mkdir()
    data.write_bytes(b"example corpus")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "files": {
                    "index/lean_explore.db": {
                        "sha256": sha(data),
                        "bytes": data.stat().st_size,
                    }
                }
            }
        )
    )
    plan = {
        "semantic_assets": {
            "root": str(tmp_path),
            "manifest_sha256": sha(manifest),
            "index_version": "index",
            "embedding_revision": "model",
            "probe": {"project": str(tmp_path / "project"), "version": "v4.27.0"},
        }
    }
    return plan, data


def test_full_tools_preflight_uses_explicit_assets_and_exercises_local_search(
    tmp_path, monkeypatch
):
    plan, data = fixture_assets(tmp_path, monkeypatch)
    frozen = {"asset_sha256": {str(data): sha(data)}}
    seen = []
    monkeypatch.setattr(
        semantic, "freeze", lambda config: (seen.append(config), frozen)[1]
    )
    monkeypatch.setattr(
        semantic,
        "search",
        lambda *args: {"count": 1, "matches": [{"name": "Nat.sum_range"}]},
    )
    monkeypatch.setattr(web, "freeze", lambda: {"enabled": True})
    result = freeze_host_tools(plan)
    assert seen == [
        semantic.SemanticSearchConfig(tmp_path / "index", tmp_path / "model")
    ]
    assert result["policy_model_calls"] == 0 and result["embedding_model_calls"] == 1
    assert result["semantic_config"] == frozen
    assert result["web_config"] == {"enabled": True}
    import os

    assert os.environ["LEAN_EXPLORE_CACHE_DIR"] == str(tmp_path)
    assert os.environ["LEAN_EXPLORE_VERSION"] == "index"


def test_changed_assets_cannot_be_admitted_even_if_query_would_work(
    tmp_path, monkeypatch
):
    plan, data = fixture_assets(tmp_path, monkeypatch)
    original = sha(data)
    data.write_bytes(b"changed")
    monkeypatch.setattr(
        semantic, "freeze", lambda _: {"asset_sha256": {str(data): original}}
    )
    with (
        patch.object(semantic, "search") as search,
        pytest.raises(ValueError, match="Semantic assets differ"),
    ):
        freeze_host_tools(plan)
    search.assert_not_called()


def test_missing_semantic_package_is_not_silently_disabled(tmp_path, monkeypatch):
    plan, _ = fixture_assets(tmp_path, monkeypatch)

    def missing(_):
        raise ModuleNotFoundError("lean_explore")

    monkeypatch.setattr(semantic, "freeze", missing)
    with pytest.raises(ModuleNotFoundError, match="lean_explore"):
        freeze_host_tools(plan)


def test_preflight_rejects_unusable_search_results(tmp_path, monkeypatch):
    plan, data = fixture_assets(tmp_path, monkeypatch)
    monkeypatch.setattr(
        semantic, "freeze", lambda _: {"asset_sha256": {str(data): sha(data)}}
    )
    monkeypatch.setattr(semantic, "search", lambda *args: {"count": 0})
    with pytest.raises(RuntimeError, match="no declarations"):
        freeze_host_tools(plan)
