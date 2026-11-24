"""Read-only lineage for completed cells reused by an explicit recovery study."""

from __future__ import annotations

import json
from pathlib import Path

from proof_eval.evidence.io import digest, read


def freeze_completed(source: Path, config: dict, packs: dict) -> dict:
    """Audit terminal successes; failed or missing cells must run afresh."""
    from .exploration_reporting import audit_cell

    source = source.resolve(strict=True)
    source_config = source / "config.json"
    old = read(source_config)
    if (source / "run.json").exists() and read(source / "run.json")[
        "status"
    ] == "running":
        raise ValueError("Cannot recover an active exploration study")
    if old.get("recovery_sources"):
        raise ValueError("Nested exploration recovery requires explicit reconciliation")
    for key in (
        "names",
        "conditions",
        "input_sha256",
        "dataset_sha256",
        "environments_sha256",
        "references_sha256",
    ):
        if old[key] != config[key]:
            raise ValueError("Recovery experiment contract changed: " + key)
    refs = {
        r["name"]: r
        for r in map(json.loads, Path(config["references"]).read_text().splitlines())
    }
    cells = {}
    for condition in config["conditions"]:
        cells[condition] = {}
        for path in sorted(
            (source / "conditions" / condition / "cells").glob("*/result.json")
        ):
            record = read(path)
            if record["status"] != "complete":
                continue
            name = record["name"]
            if (
                name not in packs
                or name in cells[condition]
                or record.get("condition") != condition
            ):
                raise ValueError("Unknown or duplicate recovery source cell")
            if (
                read(path.parent / "search/spec.json")["plan"]
                != config["conditions"][condition]
            ):
                raise ValueError("Recovery source search plan changed")
            checked = audit_cell(path.parent, packs[name]["row"], refs[name])
            cells[condition][name] = {
                "result_path": str(path),
                "result_sha256": digest(path),
                "audit": checked,
            }
    return {
        "config_path": str(source_config),
        "config_sha256": digest(source_config),
        "cells": cells,
    }


def reused_records(config: dict, condition: str) -> list[dict]:
    """Read pinned certificates without copying caches or touching source files."""
    reuse = config.get("recovery_sources")
    if not reuse:
        return []
    if digest(reuse["config_path"]) != reuse["config_sha256"]:
        raise ValueError("Recovery source configuration changed")
    records = []
    for name, item in reuse["cells"][condition].items():
        if (
            digest(item["result_path"]) != item["result_sha256"]
            or item["audit"]["status"] != "passed"
        ):
            raise ValueError("Recovery source evidence changed")
        record = read(item["result_path"])
        if record["name"] != name or record["status"] != "complete":
            raise ValueError("Invalid recovery source cell")
        records.append(record)
    return records
