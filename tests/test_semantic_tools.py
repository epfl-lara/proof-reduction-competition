"""Observable optional-search contracts; no remote or ML model calls."""

import asyncio
import sys
from types import SimpleNamespace

import pytest

from proof_eval.harness import semantic
from proof_eval.harness.prompts import SEMANTIC_TOOLS, tool_instructions


def test_optional_prompt_only_advertises_enabled_semantic_search():
    assert SEMANTIC_TOOLS not in tool_instructions("score_edges")
    assert SEMANTIC_TOOLS in tool_instructions("score_edges", semantic_search=True)


def test_semantic_scope_uses_installed_dependencies_and_rejects_widening(
    tmp_path, monkeypatch
):
    (tmp_path / "Strata").mkdir()
    assert "Mathlib" not in semantic.packages_for(tmp_path)
    assert "Strata" in semantic.packages_for(tmp_path)

    def forbidden(*args):
        raise AssertionError("An invalid request must not initialize a search model")

    monkeypatch.setattr(semantic, "_get_service", forbidden)
    config = {"index_version": "test", "version_scope": "advisory"}
    for packages in ([], ["Mathlib"], ["Physlib"], ["Std", "Mathlib"], "Std", [1]):
        with pytest.raises(ValueError, match="pinned project"):
            semantic.search(
                config, tmp_path, {"query": "a lemma", "packages": packages}, "v1"
            )
    with pytest.raises(ValueError, match="not enabled"):
        semantic.search(None, tmp_path, {"query": "a lemma"}, "v1")


@pytest.mark.parametrize(
    "tool_request",
    [
        {"query": ""},
        {"query": "\n"},
        {"query": 1},
        {"query": "x" * 501},
        {"query": "x", "limit": 0},
        {"query": "x", "limit": True},
    ],
)
def test_semantic_rejects_invalid_fields(tmp_path, tool_request):
    with pytest.raises(ValueError):
        semantic.search({}, tmp_path, tool_request, "v1")


def test_semantic_filters_backend_scope_and_bounds_response(tmp_path, monkeypatch):
    class Service:
        async def search(self, **kwargs):
            assert kwargs["packages"] == ["Std"]
            return SimpleNamespace(
                results=[
                    SimpleNamespace(
                        name=name,
                        module=module,
                        source_text="theorem t : True := by exact secret",
                        docstring=None,
                    )
                    for name, module in (
                        ("bad", "Physlib.A"),
                        ("first", "Std.A"),
                        ("extra", "Std.B"),
                    )
                ]
            )

    monkeypatch.setattr(semantic, "guard", lambda _: None)
    monkeypatch.setattr(semantic, "_get_service", lambda _: Service())
    config = {"index_version": "test", "version_scope": "advisory"}
    result = semantic.search(
        config, tmp_path, {"query": "a lemma", "limit": 1, "packages": ["Std"]}, "v1"
    )
    assert result["count"] == 1 and result["matches"][0]["name"] == "first"
    assert "secret" not in result["matches"][0]["signature"]

    async def nested():
        return semantic.search(
            config,
            tmp_path,
            {"query": "a lemma", "limit": 1, "packages": ["Std"]},
            "v1",
        )

    assert asyncio.run(nested()) == result


def test_freeze_detects_changed_index_and_embedding_assets(tmp_path, monkeypatch):
    index, model = tmp_path / "index", tmp_path / "embedding"
    index.mkdir()
    model.mkdir()
    for name in (
        "lean_explore.db",
        "informalization_faiss.index",
        "informalization_faiss_ids_map.json",
        "bm25_ids_map.json",
        "bm25_name_raw",
        "bm25_name_spaced",
    ):
        (index / name).write_text("test corpus")
    (model / "modules.json").write_text("[]")
    monkeypatch.setattr(semantic.importlib.metadata, "version", lambda _: "test")
    config = semantic.freeze(semantic.SemanticSearchConfig(index, model))
    semantic.guard(config)
    (index / "lean_explore.db").write_text("changed corpus")
    with pytest.raises(ValueError, match="asset changed"):
        semantic.guard(config)


def test_embedding_is_explicitly_cpu_and_local_files_only(monkeypatch):
    def factory(directory, **kwargs):
        assert directory == "/cached/embedding"
        assert kwargs == {"device": "cpu", "local_files_only": True}
        return object()

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(SentenceTransformer=factory),
    )
    semantic._LocalEmbedding("/cached/embedding")


@pytest.mark.parametrize(
    "source,expected",
    [
        (
            "/-- documentation := ignored -/ theorem t : True := by exact secret",
            "theorem t : True",
        ),
        ("theorem t (n : Nat := 1) : True := by exact secret", "theorem t (n : Nat"),
        ("def f : Nat → Nat\n| n => secret n", ""),
        ("/-- unclosed", ""),
    ],
)
def test_index_headers_never_return_proof_bodies(source, expected):
    assert semantic._signature(source) == expected
