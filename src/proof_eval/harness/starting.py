"""Fresh admission of an explicitly selected proof state into a model phase."""

from __future__ import annotations

import time
from pathlib import Path

from proof_eval.evidence.audit import _require
from proof_eval.evidence.io import digest, fingerprint, read, write_json
from proof_eval.protocol import code_identity
from proof_eval.verification.references import require_valid, score


def _item(config: dict, row: dict) -> dict:
    state = config["starting_proofs"]
    item = state["cells"][row["name"]]
    _require(
        state["version"] == 1
        and item["row_sha256"] == state["rows_sha256"][row["name"]]
        and item["proof_sha256"] == code_identity(row, item["proof"])
        and (
            state["source"] is None or digest(state["source"]) == state["source_sha256"]
        ),
        "Explicit starting proof changed",
    )
    return item


def adopt_starting_proof(session, folder: Path, config: dict) -> None:
    """Check once in the private cell cache and retain the best valid incumbent."""
    item = _item(config, session.row)
    marker = folder / "starting_proof_started.json"
    result_path = folder / "starting_proof.json"
    existing = [c for c in session.checks if c["origin"] == "initial_starting_proof"]
    if not existing:
        if marker.exists():
            raise ValueError(
                "Indeterminate starting-proof measurement; inspect evidence"
            )
        write_json(
            marker, {"started_epoch": time.time(), "identity": fingerprint(item)}
        )
        # The original is already freshly checked in this same model phase. Other
        # states have never entered this cell's private candidate cache.
        session.check(item["proof"], origin="initial_starting_proof")
        existing = [session.checks[-1]]
    if len(existing) != 1:
        raise ValueError("Duplicate starting-proof measurement")
    check = existing[0]
    require_valid(check["evaluation"], session.row, item["proof"])
    if not result_path.exists():
        write_json(
            result_path,
            {
                "version": 1,
                "identity": fingerprint(item),
                "check_number": check["number"],
                "check_sha256": fingerprint(check),
                "finished_epoch": time.time(),
                "source_score": item.get("source_score"),
                "verified_starting_score": score(check["evaluation"]),
                "adopted": check["accepted"],
                "model_start_score": (
                    score(check["evaluation"])
                    if check["accepted"]
                    else score(session.original)
                ),
                "model_start_proof_sha256": code_identity(
                    session.row,
                    item["proof"] if check["accepted"] else session.row["src"],
                ),
                "original_measurement_reused": code_identity(session.row, item["proof"])
                == code_identity(session.row, session.row["src"]),
            },
        )


def audit_starting_proof(
    config: dict, folder: Path, row: dict, checks: list, result: dict
) -> None:
    """Audit immutable lineage, measurement admission, selected seed and gain split."""
    item = _item(config, row)
    marker = read(folder / "starting_proof_started.json")
    saved = read(folder / "starting_proof.json")
    boundary = read(folder / "initial_phase.json")
    check = checks[0]
    original = read(folder / "initial_measurement.json")
    selected_score = (
        score(check["evaluation"])
        if check["accepted"]
        else score(original["evaluation"])
    )
    _require(
        marker["identity"] == saved["identity"] == fingerprint(item)
        and original["finished_epoch"]
        <= marker["started_epoch"]
        <= saved["finished_epoch"]
        <= boundary["finished_epoch"]
        and boundary["starting_proof_sha256"] == digest(folder / "starting_proof.json")
        and check["origin"] == "initial_starting_proof"
        and check["code"] == item["proof"]
        and saved["check_number"] == check["number"] == 1
        and saved["check_sha256"] == fingerprint(check)
        and saved["verified_starting_score"] == score(check["evaluation"])
        and saved["model_start_score"] == selected_score
        and saved["source_score"] == item.get("source_score")
        and saved["adopted"] == check["accepted"]
        and saved["original_measurement_reused"]
        == (code_identity(row, item["proof"]) == code_identity(row, row["src"]))
        and saved["model_start_proof_sha256"]
        == code_identity(row, item["proof"] if check["accepted"] else row["src"])
        and all(
            v.get("cached") is False
            for v in check["evaluation"]["per_version"].values()
        ),
        "Starting-proof measurement or phase boundary changed",
    )
    require_valid(check["evaluation"], row, item["proof"])
    _require(
        result["model_start_score"] == selected_score
        and result["model_phase_elapsed_seconds"] == result["pipeline_elapsed_seconds"]
        and result["phase_accounting"] == "model_only_external_cleanup_excluded"
        and abs(
            result["model_gain_pp"]
            - (score(result["selected_evaluation"]) - selected_score)
        )
        < 1e-9,
        "Starting-proof model gain changed",
    )
