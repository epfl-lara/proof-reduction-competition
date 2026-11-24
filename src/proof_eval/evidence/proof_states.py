"""Portable proof starting states, with explicit identities and model lineage.

Importing a state never imports evaluation caches or trusts its score. Every consumer
must freshly verify its proofs against the unchanged dataset and reference values.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, read, write_json
from proof_eval.protocol import code_identity
from proof_eval.verification.metrics import validate_candidate

VERSION = 1


def _lineage(value: dict | None) -> dict:
    result = dict(value or {"kind": "external"})
    if not isinstance(result.get("kind"), str):
        raise ValueError("Proof-state lineage requires a kind")
    model, effort = result.get("model"), result.get("effort")
    if (model is None) != (effort is None) or (
        model is not None
        and (not isinstance(model, str) or not isinstance(effort, str))
    ):
        raise ValueError("Model-produced proof lineage requires model and effort")
    if result["kind"] == "model" and model is None:
        raise ValueError("Model-produced proof lineage requires model and effort")
    return result


def validate_lineage(state: dict, condition: tuple[str, str]) -> None:
    """Reject reuse of another model/effort condition's explicitly labelled proof."""
    for name, cell in state["cells"].items():
        lineage = _lineage(cell["lineage"])
        if lineage.get("model") is not None and (
            lineage["model"],
            lineage["effort"],
        ) != tuple(condition):
            raise ValueError(
                "Starting proof belongs to another model condition: " + name
            )


def _references(references: Path, packs: dict) -> str:
    records = [
        json.loads(line) for line in references.read_text().split("\n") if line.strip()
    ]
    names = [record["name"] for record in records]
    if len(names) != len(set(names)) or not set(packs) <= set(names):
        raise ValueError("References do not cover the complete declared cohort")
    return digest(references)


def _cell(name: str, record: str | dict, pack: dict, lineage: dict | None) -> dict:
    if isinstance(record, str):
        record = {"proof": record}
    if not isinstance(record, dict):
        raise ValueError("Invalid proof-state record: " + name)
    if record.get("name", name) != name:
        raise ValueError("Proof-state name changed: " + name)
    proof = record.get("proof", record.get("selected_proof", record.get("code")))
    if not isinstance(proof, str):
        raise ValueError("Proof state needs a complete declaration: " + name)
    row = pack["row"]
    validate_candidate(row, proof)
    row_hash, proof_hash = fingerprint(row), code_identity(row, proof)
    for key, expected in (("row_sha256", row_hash), ("proof_sha256", proof_hash)):
        if key in record and record[key] != expected:
            raise ValueError("Proof-state identity changed: " + name + "/" + key)
    inherited = _lineage(record.get("lineage", lineage))
    if record.get("model") is not None or record.get("effort") is not None:
        model_lineage = _lineage(
            {
                "kind": "model",
                "model": record.get("model"),
                "effort": record.get("effort"),
            }
        )
        if inherited.get("model") is not None and any(
            inherited[key] != model_lineage[key] for key in ("model", "effort")
        ):
            raise ValueError("Conflicting model lineage: " + name)
        inherited = {**inherited, **model_lineage}
    evaluation = record.get("evaluation", record.get("selected_evaluation"))
    source_score = record.get("source_score")
    if source_score is None and evaluation:
        source_score = evaluation.get("scores", {}).get("combined_pct")
    if source_score is not None and (
        type(source_score) not in (int, float) or not math.isfinite(source_score)
    ):
        raise ValueError("Invalid informational source score: " + name)
    return {
        "proof": proof,
        "proof_sha256": proof_hash,
        "row_sha256": row_hash,
        "lineage": inherited,
        "source_score": source_score,
    }


def _manifest(
    packs: dict, references: Path, records: dict, lineage: dict | None
) -> dict:
    if not packs or set(records) != set(packs):
        raise ValueError("Proof state must cover the exact complete declared cohort")
    return {
        "proof_state_version": VERSION,
        "references_sha256": _references(references, packs),
        "rows_sha256": {name: fingerprint(pack["row"]) for name, pack in packs.items()},
        "cells": {
            name: _cell(name, records[name], pack, lineage)
            for name, pack in packs.items()
        },
        "score_policy": "Informational source scores; fresh verification required",
    }


def export_proof_states(
    path: Path,
    packs: dict,
    references: Path,
    records: dict,
    *,
    lineage: dict | None = None,
) -> dict:
    """Write a portable state; preserve per-record model lineage across cleanup."""
    manifest = _manifest(packs, references, records, lineage)
    path = Path(path)
    if path.exists() and read(path) != manifest:
        raise ValueError("Existing proof state differs; choose a new output")
    write_json(path, manifest)
    return manifest


def freeze_proof_states(
    source: Path | None,
    packs: dict,
    references: Path,
    *,
    condition: tuple[str, str] | None = None,
) -> dict:
    """Pin originals, an exported manifest, or explicit organizer name/code JSONL.

    Raw JSONL has unknown external provenance unless model/effort are supplied.
    It is never represented as audited or model-free evidence.
    """
    references = Path(references)
    if source is None:
        state = _manifest(
            packs,
            references,
            {name: pack["row"]["src"] for name, pack in packs.items()},
            {"kind": "original"},
        )
        path = None
    else:
        path = Path(source).expanduser().resolve(strict=True)
        if path.is_dir():
            path = (path / "state.json").resolve(strict=True)
        if path.suffix == ".jsonl":
            rows = [
                json.loads(line)
                for line in path.read_text().split("\n")
                if line.strip()
            ]
            records = {row["name"]: row for row in rows}
            if len(rows) != len(records):
                raise ValueError("Duplicate proof-state theorem")
            state = _manifest(packs, references, records, {"kind": "external"})
        else:
            saved = read(path)
            if saved.get("proof_state_version") != VERSION:
                raise ValueError(
                    "Unsupported proof-state manifest; use state.json or JSONL"
                )
            state = _manifest(packs, references, saved["cells"], None)
            if any(saved.get(key) != state[key] for key in state):
                raise ValueError(
                    "Proof-state manifest identity or denominators changed"
                )
    frozen = {
        "version": VERSION,
        **state,
        "source": str(path) if path else None,
        "source_sha256": digest(path) if path else None,
    }
    if condition is not None:
        validate_lineage(frozen, condition)
    return frozen


def guard_proof_states(
    state: dict,
    packs: dict,
    references: Path,
    *,
    condition: tuple[str, str] | None = None,
) -> None:
    """Recheck source bytes, dataset rows, denominator identity and condition scope."""
    if state.get("version") != VERSION:
        raise ValueError("Unsupported frozen proof-state version")
    current = freeze_proof_states(
        Path(state["source"]) if state["source"] is not None else None,
        packs,
        references,
        condition=condition,
    )
    if current != state:
        raise ValueError("Frozen starting proof state changed")
