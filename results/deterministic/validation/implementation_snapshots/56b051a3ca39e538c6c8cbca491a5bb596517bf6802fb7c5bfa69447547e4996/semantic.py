"""Optional offline declaration discovery from explicitly frozen LeanExplore assets."""

from __future__ import annotations

import asyncio
import importlib.metadata
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from proof_eval.evidence.io import digest, fingerprint
from proof_eval.verification.metrics import strip_comments

DEPENDENCIES = ("lean-explore", "sentence-transformers", "torch", "faiss-cpu", "bm25s")
_LOCK = threading.Lock()
_SERVICES: dict[str, Any] = {}


@dataclass(frozen=True)
class SemanticSearchConfig:
    index_directory: Path
    embedding_directory: Path


def discover() -> SemanticSearchConfig:
    """Locate already installed data and model files; never download assets."""
    try:
        from huggingface_hub import snapshot_download
        from lean_explore.config import Config

        model = snapshot_download("Qwen/Qwen3-Embedding-0.6B", local_files_only=True)
        return SemanticSearchConfig(Config.ACTIVE_CACHE_PATH.resolve(), Path(model))
    except (ImportError, OSError) as exc:
        raise ValueError(
            "Semantic search needs the optional semantic extra, fetched LeanExplore "
            "data and a cached Qwen3-Embedding-0.6B model"
        ) from exc


@lru_cache(maxsize=128)
def _asset_digest(path: str, size: int, mtime: int, ctime: int) -> str:
    return digest(path)


def _hash_asset(path: Path) -> str:
    stat = path.stat()
    return _asset_digest(str(path), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def freeze(config: SemanticSearchConfig) -> dict[str, Any]:
    """Pin the complete local search corpus, embedding snapshot and dependencies."""
    index, embedding = (
        config.index_directory.resolve(),
        config.embedding_directory.resolve(),
    )
    required = (
        "lean_explore.db",
        "informalization_faiss.index",
        "informalization_faiss_ids_map.json",
        "bm25_ids_map.json",
        "bm25_name_raw",
        "bm25_name_spaced",
    )
    if (
        not all((index / name).exists() for name in required)
        or not (embedding / "modules.json").is_file()
    ):
        raise ValueError(
            "Semantic search assets are incomplete; prepare them before running"
        )
    files = sorted(
        p for root in (index, embedding) for p in root.rglob("*") if p.is_file()
    )
    return {
        "index_directory": str(index),
        "embedding_directory": str(embedding),
        "index_version": index.name,
        "asset_sha256": {str(p): _hash_asset(p) for p in files},
        "dependency_versions": {
            name: importlib.metadata.version(name) for name in DEPENDENCIES
        },
        "device": "cpu",
        "rerank_top": None,
        "network": "local_files_only",
        "version_scope": "advisory index snapshot; validate against pinned project sources",
    }


def guard(config: dict[str, Any]) -> None:
    """Detect changed assets without repeatedly reading gigabytes of unchanged data."""
    for name, expected in config["dependency_versions"].items():
        if importlib.metadata.version(name) != expected:
            raise ValueError("Frozen semantic dependency changed: " + name)
    for path, expected in config["asset_sha256"].items():
        if _hash_asset(Path(path)) != expected:
            raise ValueError("Frozen semantic asset changed: " + path)


def packages_for(project: Path) -> list[str]:
    """Derive module roots from the actual project and its installed dependencies."""
    roots = [project]
    dependencies = project / ".lake/packages"
    if dependencies.is_dir():
        roots.extend(p for p in dependencies.iterdir() if p.is_dir())
    packages = {"Init", "Std", "Lean"}
    for root in roots:
        for path in root.iterdir():
            name = path.stem if path.suffix == ".lean" else path.name
            if re.fullmatch(r"[A-Z][A-Za-z0-9_]*", name) and (
                path.is_dir() or path.suffix == ".lean"
            ):
                packages.add(name)
    return sorted(packages)


class _LocalEmbedding:
    def __init__(self, directory: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(directory, device="cpu", local_files_only=True)

    async def embed(self, texts: list[str], is_query: bool = False) -> Any:
        def encode() -> Any:
            kwargs = {
                "batch_size": 8,
                "show_progress_bar": False,
                "convert_to_numpy": True,
            }
            if is_query:
                kwargs["prompt_name"] = "query"
            return self.model.encode(texts, **kwargs)

        result = await asyncio.get_running_loop().run_in_executor(None, encode)
        return SimpleNamespace(embeddings=result.tolist())


def _get_service(config: dict[str, Any]) -> Any:
    identity = fingerprint(config)
    if identity not in _SERVICES:
        from lean_explore.config import Config
        from lean_explore.search.engine import SearchEngine
        from lean_explore.search.service import Service

        index = Path(config["index_directory"])
        # LeanExplore derives its BM25 paths from this setting even with explicit
        # FAISS/database paths. Refuse a changed active corpus rather than substitute it.
        if Config.ACTIVE_CACHE_PATH.resolve() != index:
            raise ValueError(
                "Active LeanExplore corpus differs from frozen configuration"
            )
        engine = SearchEngine(
            db_url=f"sqlite+aiosqlite:///file:{index / 'lean_explore.db'}?mode=ro&uri=true",
            faiss_index_path=index / "informalization_faiss.index",
            faiss_ids_map_path=index / "informalization_faiss_ids_map.json",
            embedding_client=_LocalEmbedding(config["embedding_directory"]),
        )
        _SERVICES[identity] = Service(engine=engine)
    return _SERVICES[identity]


def _run_async(coroutine: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coroutine).result()


def _signature(source: str) -> str:
    """Return a conservative header, never the indexed implementation/proof body."""
    try:
        source = strip_comments(source)
    except ValueError:
        return ""
    declaration = re.search(r"\b(?:theorem|lemma|def|abbrev|opaque|instance)\s", source)
    if declaration is None:
        return ""
    header, assignment, _ = source[declaration.start() :].partition(":=")
    if not assignment:
        return ""
    header = re.split(r"\bwhere\b|\n\s*\|", header, maxsplit=1)[0]
    return header.strip()[:1200]


def search(
    config: dict[str, Any] | None, project: Path, request: dict[str, Any], version: str
) -> dict[str, Any]:
    if config is None:
        raise ValueError(
            "Semantic search is not enabled; select --semantic-search for a new run"
        )
    query = request.get("query")
    if (
        not isinstance(query, str)
        or not query.strip()
        or "\n" in query
        or len(query) > 500
    ):
        raise ValueError("Use one nonempty semantic query string")
    limit = request.get("limit", 10)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("Semantic search limit must be in 1..50")
    available = packages_for(project)
    requested = request.get("packages")
    if requested is not None and (
        not isinstance(requested, list)
        or not requested
        or any(not isinstance(p, str) or p not in available for p in requested)
    ):
        raise ValueError(
            "Packages must be nonempty and belong to the pinned project: "
            + ", ".join(available)
        )
    packages = sorted(set(requested or available))
    guard(config)
    # The embedding/index objects are shared between tool threads in this worker.
    with _LOCK:
        results = _run_async(
            _get_service(config).search(
                query=query, limit=limit, rerank_top=None, packages=packages
            )
        )
    matches = [
        {
            "name": r.name,
            "module": r.module,
            "signature": _signature(r.source_text),
            "docstring": (r.docstring or "").strip()[:300],
        }
        for r in results.results
        if r.module.split(".", 1)[0] in packages
    ][:limit]
    return {
        "kind": "semantic_search",
        "version": version,
        "query": query,
        "packages": packages,
        "matches": matches,
        "count": len(matches),
        "index_version": config["index_version"],
        "index_identity": fingerprint(config),
        "version_scope": config["version_scope"],
    }
