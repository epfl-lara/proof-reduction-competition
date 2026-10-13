"""Explicit source harvesting, separate from search and reference preparation."""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from proof_eval.benchmark.harvest import (
    SourceSnapshot,
    balanced_select,
    signature_key,
    task_from_range,
)
from proof_eval.benchmark.quality import (
    QualityConfig,
    intake_reason,
    select_like_benchmark,
    shape_summary,
)
from proof_eval.evidence.io import digest, now, sha, write_json, write_jsonl
from proof_eval.verification.dataset import Dataset


@dataclass(frozen=True)
class CorpusConfig:
    """A bounded, model-free task extraction; it prepares no heartbeat cache."""

    sources: tuple[SourceSnapshot, ...]
    output: Path
    exclude_dataset: Path
    limit: int = 2000
    minimum_count: int = 1000
    min_tokens: int = 222
    max_tokens: int = 5000
    min_lines: int = 47
    max_per_file: int = 8
    max_file_bytes: int = 512_000
    seed: int = 20261008
    parser_timeout_seconds: int = 1800
    match_benchmark: bool = True
    max_per_group: int = 32


def _git(project: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(project), *args], text=True
    ).strip()


def _source_files(snapshot: SourceSnapshot, config: CorpusConfig) -> list[Path]:
    if _git(snapshot.project, "rev-parse", "HEAD") != snapshot.revision:
        raise ValueError(f"Source revision changed: {snapshot.source}")
    if _git(snapshot.project, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError(f"Tracked source changed: {snapshot.source}")
    paths = subprocess.check_output(
        ["git", "-C", str(snapshot.project), "ls-files", "-z", "--", *snapshot.roots]
    ).split(b"\0")
    files = [
        snapshot.project / p.decode()
        for p in paths
        if p.endswith(b".lean")
        and (snapshot.project / p.decode()).stat().st_size <= config.max_file_bytes
    ]
    # Stratify a capped source by its first directory below the source root.
    groups: dict[str, list[Path]] = {}
    for path in files:
        relative = path.relative_to(snapshot.project)
        group = "/".join(relative.parts[:2])
        groups.setdefault(group, []).append(path)
    groups = {
        key: sorted(
            value, key=lambda p: sha(f"{config.seed}:{p.relative_to(snapshot.project)}")
        )
        for key, value in sorted(groups.items())
    }
    ordered = []
    while groups:
        for key in list(groups):
            ordered.append(groups[key].pop())
            if not groups[key]:
                del groups[key]
    return ordered[: snapshot.file_limit] if snapshot.file_limit else ordered


def _parse(
    snapshot: SourceSnapshot, files: list[Path], folder: Path, timeout: int
) -> list[dict[str, Any]]:
    folder = folder.resolve()
    folder.mkdir(parents=True)
    spec = folder / "input.json"
    helper = Path(__file__).with_name("harvest_commands.lean")
    write_json(
        spec, {"imports": snapshot.grammar_imports, "paths": list(map(str, files))}
    )
    command = ["lake", "env", "lean", "--run", str(helper), str(spec)]
    grammar_version = (snapshot.grammar_project / "lean-toolchain").read_text().strip()
    write_json(
        folder / "started.json",
        {
            "at": now(),
            "command": command,
            "cwd": str(snapshot.grammar_project),
            "grammar_toolchain": grammar_version,
            "helper_sha256": digest(helper),
        },
    )
    with (
        (folder / "output.jsonl").open("w") as output,
        (folder / "stderr.txt").open("w") as err,
    ):
        result = subprocess.run(
            command,
            cwd=snapshot.grammar_project,
            stdout=output,
            stderr=err,
            timeout=timeout,
            check=False,
        )
    write_json(folder / "finished.json", {"at": now(), "returncode": result.returncode})
    if result.returncode:
        raise ValueError(f"Parser failed; see {folder / 'output.jsonl'}")
    records = [
        json.loads(line) for line in (folder / "output.jsonl").read_text().splitlines()
    ]
    if len(records) != len(files) or {r["path"] for r in records} != set(
        map(str, files)
    ):
        raise ValueError("Parser did not return exactly one record per input file")
    return records


def build_corpus(config: CorpusConfig) -> dict[str, Any]:
    """Extract reproducible tasks. Compilation and reference prep are explicit later steps."""
    positive = (
        config.limit,
        config.minimum_count,
        config.min_tokens,
        config.max_tokens,
        config.min_lines,
        config.max_per_file,
        config.max_file_bytes,
        config.parser_timeout_seconds,
        config.max_per_group,
    )
    if any(type(value) is not int or value < 1 for value in positive):
        raise ValueError("Corpus bounds must be positive integers")
    if config.min_tokens > config.max_tokens or config.minimum_count > config.limit:
        raise ValueError("Inconsistent corpus bounds")
    if not config.sources or len({s.source for s in config.sources}) != len(
        config.sources
    ):
        raise ValueError("Expected distinct source snapshots")
    if config.output.exists():
        raise ValueError("Output already exists; use a new directory")
    benchmark = Dataset(config.exclude_dataset)
    heldout = [benchmark.get(name) for name in benchmark.names]
    excluded_files = {
        (r["source"], r["file_path"]) for r in heldout if r.get("file_path")
    }
    excluded_names = set(benchmark.names)
    excluded_signatures = {signature_key(r["statement"]) for r in heldout}
    config.output.mkdir(parents=True)
    candidates = []
    inventory = {}
    pins = []
    quality = QualityConfig(
        min_tokens=config.min_tokens,
        max_tokens=config.max_tokens,
        min_proof_lines=config.min_lines,
        max_per_file=config.max_per_file,
        max_per_group=config.max_per_group,
        seed=config.seed,
    )
    for snapshot in config.sources:
        files = _source_files(snapshot, config)
        before = {str(path): digest(path) for path in files}
        print(
            f"Parsing {snapshot.source}: {len(files)} pinned source files", flush=True
        )
        parsed = _parse(
            snapshot,
            files,
            config.output / "extraction" / snapshot.source,
            config.parser_timeout_seconds,
        )
        reasons: Counter[str] = Counter()
        for result in parsed:
            path = Path(result["path"])
            relative = str(path.relative_to(snapshot.project))
            if digest(path) != before[str(path)]:
                raise ValueError(f"Source changed during extraction: {path}")
            if result["errors"]:
                reasons["files_with_parser_errors"] += 1
                continue
            if (snapshot.source, relative) in excluded_files:
                reasons["benchmark_files"] += 1
                continue
            raw = path.read_bytes()
            for record in result["records"]:
                reasons["parsed_declarations"] += 1
                try:
                    row = task_from_range(snapshot, path, raw, record, seed=config.seed)
                except (ValueError, UnicodeError) as exc:
                    reasons[f"rejected:{str(exc)}"] += 1
                    continue
                meta = row["training_metadata"]
                if (
                    row["name"] in excluded_names
                    or meta["signature_key"] in excluded_signatures
                ):
                    reasons["benchmark_theorems"] += 1
                elif reason := intake_reason(row, quality):
                    reasons[reason] += 1
                else:
                    candidates.append(row)
                    reasons["eligible"] += 1
        inventory[snapshot.source] = {
            "files_scanned": len(files),
            "counts": dict(reasons),
        }
        write_json(config.output / "inventory.partial.json", inventory)
        pins.append(
            {
                "source": snapshot.source,
                "url": snapshot.url,
                "revision": snapshot.revision,
                "version": snapshot.version,
                "roots": snapshot.roots,
                "file_limit": snapshot.file_limit,
                "grammar_imports": snapshot.grammar_imports,
                "grammar_version": (snapshot.grammar_project / "lean-toolchain")
                .read_text()
                .strip(),
                "grammar_revision": _git(snapshot.grammar_project, "rev-parse", "HEAD"),
            }
        )
        print(f"{snapshot.source}: {reasons['eligible']} eligible tasks", flush=True)
    selected = (
        select_like_benchmark(candidates, heldout, limit=config.limit, config=quality)
        if config.match_benchmark
        else balanced_select(
            candidates,
            limit=config.limit,
            seed=config.seed,
            max_per_file=config.max_per_file,
        )
    )
    if len(selected) < config.minimum_count:
        raise ValueError(
            f"Only {len(selected)} tasks survived; see inventory.partial.json"
        )
    paths = {}
    for split in ("train", "dev", "test"):
        rows = [r for r in selected if r["training_metadata"]["split"] == split]
        path = config.output / f"{split}.jsonl"
        write_jsonl(path, rows)
        paths[split] = {"count": len(rows), "sha256": digest(path)}
    write_jsonl(config.output / "tasks.jsonl", selected)
    Dataset(
        config.output / "tasks.jsonl"
    )  # Check the actual downstream loader contract.
    report = {
        "schema": 1,
        "created_at": now(),
        "kind": "arena_refactoring_tasks_for_rsi_rl",
        "count": len(selected),
        "requested_limit": config.limit,
        "tasks_sha256": digest(config.output / "tasks.jsonl"),
        "splits": paths,
        "sources": pins,
        "inventory": inventory,
        "selected_by_source": dict(Counter(r["source"] for r in selected)),
        "excluded_dataset_sha256": digest(config.exclude_dataset),
        "filters": {
            "min_tokens": config.min_tokens,
            "max_tokens": config.max_tokens,
            "min_proof_nonempty_lines": config.min_lines,
            "max_per_file": config.max_per_file,
            "max_file_bytes": config.max_file_bytes,
            "max_per_group": config.max_per_group,
        },
        "length_matching": config.match_benchmark,
        "benchmark_shape": shape_summary(heldout),
        "task_shape": shape_summary(selected),
        "seed": config.seed,
        "compiler_checked": 0,
        "prepared_heartbeat_references": 0,
        "status": "parsed_task_corpus_requires_compilation_and_reference_preparation",
    }
    write_json(config.output / "manifest.json", report)
    return report
