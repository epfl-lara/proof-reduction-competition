"""Explicit transfer of original denominators; never candidate or analysis caches."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

from proof_eval import Evaluator
from proof_eval.evidence.immutable import immutable, read, sha
from proof_eval.training.data import task_id, validate_reserve
from proof_eval.verification.references import required_versions


def import_original_references(
    spec: dict, dataset: Path, environments: Path, output: Path
) -> dict:
    """Bind saved successful originals to fresh cache keys, retaining measurement origin."""
    manifest_path = Path(spec["manifest"])
    if sha(manifest_path) != spec["manifest_sha256"]:
        raise ValueError("Original-reference transfer manifest changed")
    manifest = read(manifest_path)
    if (
        manifest["kind"] != "original_references_only"
        or manifest["policy_model_calls"] != 0
        or manifest["optimizer_steps"] != 0
    ):
        raise ValueError("Only pre-policy original measurements may transfer")
    source = Path(spec["preparation"])
    if sha(source / "prepared.json") != manifest["prepared_sha256"]:
        raise ValueError("Source original preparation changed")
    rows = {task_id(row): row for row in validate_reserve(dataset)}
    previous = read(source / "prepared.json")
    if previous["dataset_sha256"] != sha(dataset / "rl-reserved.jsonl"):
        raise ValueError("Original reference reserve changed")
    eligible = {
        r["task_id"]: r for r in previous["records"] if r["status"] == "prepared"
    }
    if set(eligible) != set(manifest["entries"]) or len(eligible) != spec["count"]:
        raise ValueError("Original transfer cohort is incomplete or changed")
    evaluator = Evaluator(
        dataset / "rl-reserved.jsonl", environments, output / "cache", timeout=300
    )
    imports = []
    for identity, entry in manifest["entries"].items():
        record = eligible[identity]
        pack_path = source / record["pack_path"]
        if (
            sha(pack_path) != record["pack_sha256"]
            or sha(pack_path) != entry["pack_sha256"]
        ):
            raise ValueError("Source original pack changed: " + identity)
        pack = read(pack_path)
        row = evaluator.dataset.get(rows[identity]["name"])
        if (
            pack["row"] != row
            or pack["proof"] != row["src"]
            or record["task"] != [row["source"], row["name"]]
            or set(entry["references"]) != set(required_versions(pack))
        ):
            raise ValueError("Original reference source identity changed: " + identity)
        for version, saved in entry["references"].items():
            path = source / saved["path"]
            if (
                not path.resolve().is_relative_to(source.resolve())
                or sha(path) != saved["sha256"]
            ):
                raise ValueError("Source original cache changed: " + identity)
            value = read(path)
            _, fingerprint, key = evaluator._context(row, version)
            packed = pack["incumbent"]["per_version"][version]["reference"]
            heartbeat = value.get("heartbeats")
            if (
                value.get("status") != "prepared"
                or value.get("name") != row["name"]
                or value.get("version") != version
                or value.get("reference_code_sha256")
                != hashlib.sha256(row["src"].encode()).hexdigest()
                or value.get("environment_fingerprint") != fingerprint
                or value.get("length") != row["proof_length"]
                or type(heartbeat) not in (int, float)
                or not math.isfinite(heartbeat)
                or heartbeat <= 0
                or any(packed.get(k) != v for k, v in value.items())
            ):
                raise ValueError(
                    "Original denominator/environment differs: " + identity
                )
            with evaluator.store.locked("references", key):
                current = evaluator.store.read("references", key)
                if current is not None and current != value:
                    raise ValueError("Receiving reference cache is occupied")
                if current is None:
                    evaluator.store.write("references", key, value)
            item = {
                "task_id": identity,
                "version": version,
                "source_path": str(path),
                "source_sha256": sha(path),
                "target_key": key,
                "measurement_machine": value["machine"],
                "receiving_cache_machine": evaluator.machine,
                "original_measurement_unchanged": True,
                "fresh_episode_measurement_required": True,
            }
            immutable(output / "reference-imports" / f"{identity}-{version}.json", item)
            imports.append(item)
    result = {
        "status": "imported_original_references",
        "source_manifest_sha256": sha(manifest_path),
        "tasks": len(eligible),
        "versions": len(imports),
        "policy_model_calls": 0,
        "optimizer_steps": 0,
        "compiler_calls": 0,
        "candidate_or_analysis_caches_imported": False,
        "fresh_episode_measurement_required": True,
    }
    immutable(output / "reference-import.json", result)
    return result
