"""Explicit transfer of complete original references between pinned hosts.

The producer's records and machine identity are preserved. Importing only binds
those records to the receiver's local cache keys after fresh environment checks;
it never compiles Lean, invents a measurement, or copies candidate caches.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, read, write_json

from .references import required_versions


def _record(evaluator, row: dict, version: str, record: dict, environment: str):
    if (
        record.get("status") != "prepared"
        or record.get("name") != row["name"]
        or record.get("version") != version
        or record.get("reference_code_sha256")
        != hashlib.sha256(row["src"].encode()).hexdigest()
        or record.get("length") != row["proof_length"]
        or record.get("environment_fingerprint") != environment
        or record.get("details", {}).get("timeout_seconds") != evaluator.timeout
        or not record.get("measured_at")
        or not isinstance(record.get("machine"), dict)
    ):
        raise ValueError("Prepared reference identity changed: " + row["name"])
    for field in ("heartbeats", "heartbeats_raw"):
        value = record.get(field)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError("Prepared reference has no positive heartbeat measurement")
    if record["heartbeats_raw"] / 1000 != record["heartbeats"]:
        raise ValueError("Prepared heartbeat units changed")


def export_references(evaluator, destination: Path) -> dict:
    """Freeze an exact complete cohort, including the original cache record bytes."""
    entries = []
    for name in evaluator.dataset.names:
        row = evaluator.dataset.get(name)
        for version in required_versions({"row": row}):
            _, environment, key = evaluator._context(row, version)
            path = evaluator.store.root / "references" / (key + ".json")
            raw = path.read_bytes()
            record = json.loads(raw)
            _record(evaluator, row, version, record, environment)
            if record["machine"] != evaluator.machine:
                raise ValueError("Export requires the actual producer's measurements")
            entries.append(
                {
                    "name": name,
                    "version": version,
                    "row_sha256": fingerprint(row),
                    "record_json": raw.decode(),
                    "record_sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
    bundle = {
        "schema_version": 1,
        "dataset_sha256": digest(evaluator.dataset.path),
        "names": evaluator.dataset.names,
        "producer_machine": evaluator.machine,
        "verification_timeout_seconds": evaluator.timeout,
        "entries": entries,
        "candidate_caches_included": False,
    }
    if Path(destination).exists():
        raise ValueError("Reference export already exists; inspect its exact receipt")
    write_json(destination, bundle)
    return {
        "path": str(destination),
        "sha256": digest(destination),
        "checks": len(entries),
    }


def import_references(evaluator, source: Path, expected_sha256: str) -> dict:
    """Verify all entries before installing any, retaining producer provenance."""
    if digest(source) != expected_sha256:
        raise ValueError("Prepared reference bundle hash mismatch")
    bundle = read(source)
    names = evaluator.dataset.names
    expected = {
        (name, version)
        for name in names
        for version in required_versions({"row": evaluator.dataset.get(name)})
    }
    if (
        bundle.get("schema_version") != 1
        or bundle.get("dataset_sha256") != digest(evaluator.dataset.path)
        or bundle.get("names") != names
        or bundle.get("verification_timeout_seconds") != evaluator.timeout
        or bundle.get("candidate_caches_included") is not False
        or len(bundle.get("entries", [])) != len(expected)
    ):
        raise ValueError("Prepared reference cohort or verifier policy changed")
    checked, seen = [], set()
    for entry in bundle["entries"]:
        pair = entry["name"], entry["version"]
        if pair not in expected or pair in seen:
            raise ValueError("Prepared reference version is unexpected or duplicated")
        seen.add(pair)
        row = evaluator.dataset.get(entry["name"])
        raw = entry["record_json"].encode()
        if (
            entry["row_sha256"] != fingerprint(row)
            or hashlib.sha256(raw).hexdigest() != entry["record_sha256"]
        ):
            raise ValueError("Prepared reference record hash mismatch")
        record = json.loads(raw)
        _, environment, key = evaluator._context(row, entry["version"])
        _record(evaluator, row, entry["version"], record, environment)
        if record["machine"] != bundle["producer_machine"]:
            raise ValueError("Prepared reference producer identity changed")
        existing = evaluator.store.read("references", key)
        if existing is not None and existing != record:
            raise ValueError("Receiver already has a different reference denominator")
        checked.append((key, record))
    for key, record in checked:
        with evaluator.store.locked("references", key):
            existing = evaluator.store.read("references", key)
            if existing is not None and existing != record:
                raise ValueError("Receiver reference changed during import")
            if existing is None:
                evaluator.store.write("references", key, record)
    receipt = {
        "schema_version": 1,
        "source": str(Path(source).resolve()),
        "source_sha256": expected_sha256,
        "producer_machine": bundle["producer_machine"],
        "receiver_machine": evaluator.machine,
        "record_sha256": {key: fingerprint(record) for key, record in checked},
        "checks": len(checked),
        "model_calls": 0,
        "Lean_calls": 0,
    }
    key = expected_sha256
    with evaluator.store.locked("reference_imports", key):
        existing = evaluator.store.read("reference_imports", key)
        if existing is not None and existing != receipt:
            raise ValueError("Reference import receipt changed")
        if existing is None:
            evaluator.store.write("reference_imports", key, receipt)
    return receipt
