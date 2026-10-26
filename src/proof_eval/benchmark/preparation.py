"""Freeze original-only input packs from complete prepared references.

This function never invokes Lean or prepares missing references. It is used
only after explicit CPU preparation (and an explicit reference transfer when
moving hosts), so GPU admission cannot trigger another compiler pass.
"""

from __future__ import annotations

import fcntl
import math
from dataclasses import dataclass
from pathlib import Path

from proof_eval import Evaluator
from proof_eval.evidence.io import digest, fingerprint, read, write_json, write_jsonl
from proof_eval.paths import PACKAGE, ROOT
from proof_eval.verification.metrics import token_count, validate_candidate
from proof_eval.verification.references import (
    check_references,
    original_evaluation,
    required_versions,
)

from .process import _export_version, _initial_row

SOURCE_EXCERPT_CHARACTERS = 6000


@dataclass(frozen=True)
class PreparedInputs:
    base: Path
    references: Path
    packs: dict[str, dict]


def _source_context(row: dict, evaluator: Evaluator) -> str:
    relative = row.get("file_path")
    if not relative:
        return row.get("header", "")
    version = next(iter(row["version_info"][0]))
    project = evaluator.projects[(row["source"], version)]
    source = (project / relative).resolve()
    if not source.is_relative_to(project):
        raise ValueError("Benchmark file_path escapes configured project")
    text = source.read_text()
    target = row["src"] if text.count(row["src"]) == 1 else row["statement"]
    if text.count(target) != 1:
        raise ValueError(
            "Reference statement is not unique in pinned source: " + row["name"]
        )
    return text[: text.index(target)][-SOURCE_EXCERPT_CHARACTERS:]


def _original_pack(row: dict, evaluator: Evaluator) -> dict:
    versions = required_versions({"row": row})
    references = evaluator.get_reference(row["name"])["versions"]
    for version, reference in references.items():
        heartbeats = reference.get("heartbeats")
        if (
            type(heartbeats) not in (int, float)
            or not math.isfinite(heartbeats)
            or heartbeats <= 0
        ):
            raise ValueError(
                "Scoring needs a positive heartbeat reference: "
                + row["name"]
                + "/"
                + version
            )
    source_context = _source_context(row, evaluator)
    pack = {
        "name": row["name"],
        "row": row,
        "proof": row["src"],
        "incumbent": {
            "schema_version": 1,
            "name": row["name"],
            "status": "passed",
            "primary_version": versions[0],
            "requested_versions": versions,
            "all_versions": versions,
            "reference": {
                "length": row["proof_length"],
                "published_heartbeats": row.get("published_heartbeats"),
            },
            "per_version": {v: {"reference": references[v]} for v in versions},
        },
        "source_context": source_context,
        "source_excerpt_characters": len(source_context),
    }
    pack["incumbent"] = original_evaluation(pack)
    return pack


def load_prepared(base: Path, evaluator: Evaluator) -> PreparedInputs:
    """Validate a frozen preparation and cached references without measuring."""
    config = read(base / "config.json")
    request = read(base / "request.json")
    if base.name != fingerprint(request) or any(
        config.get(k) != v for k, v in request.items()
    ):
        raise ValueError("Prepared input identity changed")
    if config["names"] != evaluator.dataset.names:
        raise ValueError("Prepared cohort changed")
    for relative, expected in config["artifact_sha256"].items():
        if digest(base / relative) != expected:
            raise ValueError("Prepared input artifact changed: " + relative)
    if digest(evaluator.dataset.path) != config["dataset_sha256"]:
        raise ValueError("Prepared dataset changed")
    packs = {}
    for name in config["names"]:
        pack = read(base / "inputs" / (fingerprint(name) + ".json"))
        if (
            pack["name"] != name
            or pack["row"] != evaluator.dataset.get(name)
            or pack["proof"] != pack["row"]["src"]
        ):
            raise ValueError("Prepared task differs from input: " + name)
        if fingerprint(pack) != config["input_sha256"][name]:
            raise ValueError("Prepared theorem changed: " + name)
        check_references(evaluator, pack, config)
        packs[name] = pack
    return PreparedInputs(base, base / "reference_values.jsonl", packs)


def freeze_prepared_inputs(
    evaluator: Evaluator, environments: Path, cache: Path
) -> PreparedInputs:
    """Read all-version reference records and freeze packs; zero compiler calls."""
    rows = [evaluator.dataset.get(name) for name in evaluator.dataset.names]
    contexts, records, exported = {}, {}, []
    for row in rows:
        _, body = validate_candidate(row, row["src"])
        if token_count(body) != row["proof_length"]:
            raise ValueError("Original token count differs from fixed denominator")
        snapshot, keys = evaluator.reference_snapshot(row["name"], expected_row=row)
        refs = snapshot["versions"]
        if set(refs) != set(required_versions({"row": row})) or any(
            v.get("status") != "prepared" for v in refs.values()
        ):
            raise ValueError("CPU reference preparation is incomplete: " + row["name"])
        contexts[row["name"]] = keys
        records[row["name"]] = fingerprint(refs)
        value = _initial_row(row, "all", digest(evaluator.dataset.path))
        for version, item in value["per_version"].items():
            ref = refs[version]
            value["per_version"][version] = _export_version(
                version, item["source_commit"], ref, ref
            )
        value["status"] = "prepared"
        exported.append(value)
    pins = {
        str(p.relative_to(ROOT)): digest(p)
        for p in [
            Path(__file__),
            PACKAGE / "benchmark/process.py",
            *sorted((PACKAGE / "verification").glob("*.py")),
        ]
    }
    imports = {
        p.name: digest(p)
        for p in sorted((evaluator.store.root / "reference_imports").glob("*.json"))
    }
    spec = {
        "preparation_version": 3,
        "dataset_sha256": digest(evaluator.dataset.path),
        "environment_config_sha256": digest(environments),
        "contexts": contexts,
        "names": evaluator.dataset.names,
        "code_sha256": pins,
        "source_excerpt_characters": SOURCE_EXCERPT_CHARACTERS,
        "reference_sha256": records,
        "reference_import_receipt_sha256": imports,
        "compiler_calls": 0,
    }
    base = Path(cache) / "prepared_inputs" / fingerprint(spec)
    base.mkdir(parents=True, exist_ok=True)
    with (base / ".prepare.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (base / "config.json").exists():
            return load_prepared(base, evaluator)
        if (base / "request.json").exists():
            raise ValueError("Input freeze has an unknown prior intent; inspect it")
        write_json(base / "request.json", spec)
        write_jsonl(base / "reference_values.jsonl", exported)
        packs = {row["name"]: _original_pack(row, evaluator) for row in rows}
        for name, pack in packs.items():
            write_json(base / "inputs" / (fingerprint(name) + ".json"), pack)
        artifacts = {"reference_values.jsonl": digest(base / "reference_values.jsonl")}
        artifacts.update(
            {
                str(p.relative_to(base)): digest(p)
                for p in sorted((base / "inputs").glob("*.json"))
            }
        )
        write_json(
            base / "config.json",
            {
                **spec,
                "input_sha256": {n: fingerprint(p) for n, p in packs.items()},
                "artifact_sha256": artifacts,
            },
        )
    return load_prepared(base, evaluator)
