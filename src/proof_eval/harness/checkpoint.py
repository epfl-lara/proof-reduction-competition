"""Explicit, audited deterministic starting points for untimed closed-track runs."""

from __future__ import annotations

import json
import time
from pathlib import Path

from proof_eval.evidence.audit import _require
from proof_eval.evidence.io import digest, fingerprint, read, write_json
from proof_eval.optimization.exploration_reporting import audit_cell
from proof_eval.protocol import code_identity
from proof_eval.providers.registry import MODEL_TRACKS
from proof_eval.verification.references import require_valid, score


def validate_checkpoint_policy(config: dict) -> None:
    """Preprocessed starts are opt-in and unavailable to time-budget conditions."""
    if (
        not config.get("initial_pipeline_version")
        or config["budget_tracking"] != "cost"
        or config["problem_timeout_seconds"] is not None
        or config["initial_deterministic_methods"]
        or config["mode"] == "correctness"
        or any(MODEL_TRACKS[m] != "closed" for m, _ in config["conditions"])
    ):
        raise ValueError(
            "Deterministic checkpoints require untimed closed-track cost search "
            "with --no-deterministic and fresh original measurements"
        )


def freeze_checkpoint(source: Path, packs: dict, references: Path) -> dict:
    """Audit a complete model-free exploration condition and freeze its proofs."""
    source = source.resolve(strict=True)
    refs = {r["name"]: r for r in map(json.loads, references.read_text().splitlines())}
    paths = sorted((source / "cells").glob("*/result.json"))
    records = {read(p)["name"]: p for p in paths}
    if len(paths) != len(records) or set(records) != set(packs):
        raise ValueError("Checkpoint must cover the complete declared cohort")
    cells = {}
    for name, pack in packs.items():
        path = records[name]
        result = read(path)
        if result["status"] != "complete":
            raise ValueError("Incomplete deterministic checkpoint: " + name)
        checked = audit_cell(path.parent, pack["row"], refs[name])
        cells[name] = {
            "source_result": str(path),
            "source_sha256": digest(path),
            "audit": checked,
            "proof": result["proof"],
            "proof_sha256": code_identity(pack["row"], result["proof"]),
            "source_score": score(result["evaluation"]),
            "source_gain_pp": result["gain_pp"],
        }
    return {"version": 1, "source": str(source), "cells": cells}


def guard_checkpoint(config: dict, row: dict) -> dict:
    """Verify the chosen source remains the explicitly pinned deterministic result."""
    validate_checkpoint_policy(config)
    item = config["deterministic_checkpoint"]["cells"][row["name"]]
    _require(
        digest(item["source_result"]) == item["source_sha256"]
        and code_identity(row, item["proof"]) == item["proof_sha256"],
        "Deterministic checkpoint changed",
    )
    return item


def adopt_checkpoint(session, folder: Path, config: dict) -> None:
    """Freshly check the checkpoint once; never replay an interrupted check."""
    item = guard_checkpoint(config, session.row)
    marker = folder / "checkpoint_started.json"
    result_path = folder / "checkpoint.json"
    existing = [c for c in session.checks if c["origin"] == "initial_checkpoint"]
    if not existing:
        if marker.exists():
            raise ValueError("Indeterminate checkpoint measurement; inspect evidence")
        write_json(
            marker, {"started_epoch": time.time(), "identity": fingerprint(item)}
        )
        session.check(item["proof"], origin="initial_checkpoint")
        existing = [session.checks[-1]]
    if len(existing) != 1:
        raise ValueError("Duplicate checkpoint measurement")
    check = existing[0]
    require_valid(check["evaluation"], session.row, item["proof"])
    if not check["accepted"] and code_identity(
        session.row, item["proof"]
    ) != code_identity(session.row, session.row["src"]):
        raise ValueError(
            "Checkpoint did not retain its improvement on fresh verification"
        )
    if not result_path.exists():
        write_json(
            result_path,
            {
                "identity": fingerprint(item),
                "check_number": check["number"],
                "check_sha256": fingerprint(check),
                "finished_epoch": time.time(),
                "model_start_score": score(check["evaluation"]),
                "source_score": item["source_score"],
            },
        )


def audit_checkpoint(config: dict, folder: Path, row: dict, checks: list) -> None:
    """Verify source lineage, fresh measurement, startup boundary and score split."""
    item = guard_checkpoint(config, row)
    started = read(folder / "checkpoint_started.json")
    saved = read(folder / "checkpoint.json")
    boundary = read(folder / "initial_phase.json")
    check = checks[0]
    _require(
        started["identity"] == saved["identity"] == fingerprint(item)
        and started["started_epoch"]
        >= read(folder / "initial_measurement.json")["finished_epoch"]
        and saved["finished_epoch"] >= started["started_epoch"]
        and boundary["finished_epoch"] >= saved["finished_epoch"]
        and boundary["checkpoint_sha256"] == digest(folder / "checkpoint.json")
        and check["origin"] == "initial_checkpoint"
        and check["code"] == item["proof"]
        and saved["check_number"] == check["number"] == 1
        and saved["check_sha256"] == fingerprint(check)
        and saved["model_start_score"] == score(check["evaluation"])
        and saved["source_score"] == item["source_score"]
        and (check["accepted"] or item["proof"] == row["src"])
        and all(
            v.get("cached") is False
            for v in check["evaluation"]["per_version"].values()
        ),
        "Checkpoint measurement or startup boundary changed",
    )
