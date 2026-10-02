"""Prepare cached local reference costs and export one JSONL row per problem.

Run ``python src/process_benchmark.py --help`` for the command-line interface.
Reference lengths and published heartbeat counts come directly from the input
files. Local reference compilation is explicit and cached by ``Evaluator``;
only ``--refresh`` requests a new measurement for an already prepared context.

The complete output is replaced atomically after each problem. Unprocessed rows
remain present with ``pending`` status, so interruption never looks like success.
On restart the evaluator's durable cache supplies completed measurements; the
export itself is never trusted as an environment-independent measurement cache.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

from proof_eval import Evaluator


def parse_versions(value: str) -> str | list[str]:
    """Accept the API's named selectors or explicit comma-separated labels."""
    if value in ("all", "primary"):
        return value
    labels = [label.strip() for label in value.split(",")]
    if not all(labels) or len(labels) != len(set(labels)):
        raise ValueError("--versions needs nonempty, unique version labels")
    return labels


def _requested_versions(row: dict[str, Any], versions: str | list[str]) -> list[str]:
    listed = [version for item in row["version_info"] for version in item]
    if versions == "all":
        return listed
    if versions == "primary":
        return listed[:1]
    return [versions] if isinstance(versions, str) else list(versions)


def _unavailable(message: str, *, status: str = "unavailable") -> dict[str, Any]:
    return {
        "status": status,
        "heartbeats": None,
        "heartbeats_raw": None,
        "cached": False,
        "diagnostics": [{"severity": "error", "data": message}],
    }


def _export_version(
    version: str,
    commit: str | None,
    prepared: dict[str, Any],
    cached_record: dict[str, Any],
) -> dict[str, Any]:
    # A failed explicit refresh must not be concealed by an older cache record.
    result = prepared
    if prepared.get("status") == "prepared" and cached_record.get("status") != "prepared":
        result = _unavailable("The prepared reference was unavailable during cache readback")
        result["diagnostics"].extend(cached_record.get("diagnostics", []))
    ready = result.get("status") == "prepared"
    return {
        "version": version,
        "source_commit": commit,
        "status": result.get("status", "unavailable"),
        "heartbeats": result.get("heartbeats") if ready else None,
        "heartbeats_raw": result.get("heartbeats_raw") if ready else None,
        "cached": bool(result.get("cached", False)),
        "cache_status": cached_record.get("status", "unavailable"),
        "provenance": {
            "environment_fingerprint": result.get("environment_fingerprint"),
            "machine": result.get("machine"),
            "measured_at": result.get("measured_at"),
            "reference_code_sha256": result.get("reference_code_sha256"),
            "details": result.get("details", {}),
        },
        "diagnostics": result.get("diagnostics", []),
    }


def _initial_row(row: dict[str, Any], versions: str | list[str], dataset_sha256: str) -> dict[str, Any]:
    commits = {version: commit for item in row["version_info"] for version, commit in item.items()}
    selected = _requested_versions(row, versions)
    pending = {"status": "pending", "cached": False}
    return {
        "schema_version": 1,
        "name": row["name"],
        "source": row["source"],
        "status": "pending",
        "reference_length_tokens": row["proof_length"],
        "published_heartbeats": row.get("published_heartbeats"),
        "primary_version": next(iter(commits)),
        "requested_versions": selected,
        "dataset_sha256": dataset_sha256,
        "reference_code_sha256": hashlib.sha256(row["src"].encode("utf-8")).hexdigest(),
        "per_version": {
            version: _export_version(version, commits.get(version), pending, pending)
            for version in selected
        },
    }


def process_problem(
    evaluator: Evaluator,
    row: dict[str, Any],
    *,
    versions: str | list[str],
    dataset_sha256: str,
    refresh: bool = False,
) -> dict[str, Any]:
    """Prepare once, read the cache, and retain explicit failures in one row."""
    exported = _initial_row(row, versions, dataset_sha256)
    try:
        prepared = evaluator.prepare_reference(row["name"], versions=versions, refresh=refresh)
    except Exception as exc:
        prepared = {"versions": {
            version: _unavailable(f"{type(exc).__name__}: {exc}")
            for version in exported["requested_versions"]
        }}
    try:
        reference = evaluator.get_reference(row["name"], versions=versions)
    except Exception as exc:
        reference = {"versions": {
            version: _unavailable(f"{type(exc).__name__}: {exc}")
            for version in exported["requested_versions"]
        }}
    for version, value in exported["per_version"].items():
        missing = _unavailable("Evaluator returned no result for the requested version")
        exported["per_version"][version] = _export_version(
            version,
            value["source_commit"],
            prepared.get("versions", {}).get(version, missing),
            reference.get("versions", {}).get(version, missing),
        )
    exported["status"] = (
        "prepared" if all(item["status"] == "prepared" for item in exported["per_version"].values())
        else "incomplete"
    )
    return exported


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def _output_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_name(path.name + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def process_benchmark(
    evaluator: Evaluator,
    output_path: str | Path = ".proof-eval/benchmark_values.jsonl",
    *,
    versions: str | list[str] = "all",
    names: list[str] | None = None,
    refresh: bool = False,
    protected_paths: tuple[str | Path, ...] = (),
) -> dict[str, Any]:
    """Checkpoint every row and return compact preparation totals.

    A failing problem never removes another problem from the export. Exceptions
    from individual measurements become unavailable results; interrupts still
    propagate after the last atomic checkpoint. Explicit version labels have
    the same meaning as in ``Evaluator``: labels absent from a problem produce
    an unavailable result rather than silently selecting another toolchain.
    """
    output = Path(output_path).expanduser().resolve()
    dataset_path = Path(evaluator.dataset.path).resolve()
    inputs = {dataset_path, dataset_path.with_name("benchmark_heartbeats.jsonl")}
    inputs.update(Path(path).expanduser().resolve() for path in protected_paths)
    if output in inputs:
        raise ValueError("Output path must not overwrite dataset, heartbeat, or environment inputs")
    selected_names = list(evaluator.dataset.names if names is None else names)
    if not selected_names or len(selected_names) != len(set(selected_names)):
        raise ValueError("Select at least one problem, without duplicate names")
    if isinstance(versions, str):
        versions = parse_versions(versions)
    elif not versions or not all(isinstance(v, str) and v for v in versions) or len(versions) != len(set(versions)):
        raise ValueError("Select nonempty, unique version labels")
    source_rows = [evaluator.dataset.get(name) for name in selected_names]
    dataset_sha256 = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    rows = [_initial_row(row, versions, dataset_sha256) for row in source_rows]
    with _output_lock(output):
        _atomic_jsonl(output, rows)
        for index, row in enumerate(source_rows):
            rows[index] = process_problem(
                evaluator, row, versions=versions, dataset_sha256=dataset_sha256, refresh=refresh,
            )
            _atomic_jsonl(output, rows)
    outcomes = [value for row in rows for value in row["per_version"].values()]
    prepared = sum(value["status"] == "prepared" for value in outcomes)
    return {
        "problems": len(rows),
        "prepared_versions": prepared,
        "unavailable_versions": len(outcomes) - prepared,
        "cached_versions": sum(value["status"] == "prepared" and value["cached"] for value in outcomes),
        "output": str(output),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="data/benchmark_data_warmup.jsonl")
    parser.add_argument("--heartbeats", default=None)
    parser.add_argument("--environments", default="environments.local.json")
    parser.add_argument("--cache", default=".proof-eval")
    parser.add_argument("--output", default=".proof-eval/benchmark_values.jsonl")
    parser.add_argument("--versions", default="all", help="all, primary, or comma-separated version labels")
    parser.add_argument("--name", action="append", help="Exact problem name; repeat to select multiple problems")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--refresh", action="store_true", help="Explicitly remeasure existing local baselines")
    args = parser.parse_args(argv)
    try:
        evaluator = Evaluator(
            args.dataset, args.environments, args.cache,
            heartbeats_path=args.heartbeats, timeout=args.timeout,
        )
        protected = tuple(path for path in (args.dataset, args.heartbeats, args.environments) if path is not None)
        summary = process_benchmark(
            evaluator, args.output, versions=parse_versions(args.versions), names=args.name,
            refresh=args.refresh, protected_paths=protected,
        )
        print(json.dumps(summary, ensure_ascii=False, allow_nan=False))
        return 2 if summary["unavailable_versions"] else 0
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
