"""Publish verified host incumbents independently of native trace diagnostics.

This reads saved proof certificates only. It never runs Lean, samples a model,
changes an outcome, or claims that a failed search used its full budget.
"""

from __future__ import annotations

import json
from pathlib import Path

from proof_eval.evidence.io import (
    digest,
    fingerprint,
    read,
    sha,
    write_json,
    write_jsonl,
)
from proof_eval.verification.feedback import all_versions_passed
from proof_eval.verification.metrics import validate_candidate
from proof_eval.verification.references import versions


def _verified_proof(row: dict, reference: dict, proof: str, evaluation: dict) -> None:
    normalized, _ = validate_candidate(row, proof)
    required = versions(row)
    if (
        evaluation.get("status") != "passed"
        or not all_versions_passed(evaluation, required)
        or evaluation.get("candidate", {}).get("code_sha256") != sha(normalized)
        or any(
            evaluation["per_version"][version].get("environment_fingerprint")
            != reference["per_version"][version]["provenance"][
                "environment_fingerprint"
            ]
            for version in required
        )
    ):
        raise ValueError("Submission proof certificate is invalid: " + row["name"])


def verified_model_solutions(model_output: Path, names: list[str]) -> tuple[list, dict]:
    """Select the best fully checked proof for every declared original problem."""
    model_output = Path(model_output)
    run = read(model_output / "run.json")
    if run.get("status") not in {"finished", "failed", "complete", "incomplete"}:
        raise ValueError("Submission model batch is still active or indeterminate")
    config = read(model_output / "config.json")
    if (
        len(names) != len(set(names))
        or set(config["names"]) != set(names)
        or len(config["conditions"]) != 1
    ):
        raise ValueError("Submission needs one exact complete problem cohort")
    base = Path(config["base_directory"])
    if digest(base / "config.json") != config["base_config_sha256"]:
        raise ValueError("Submission prepared inputs changed")
    packs = {}
    for path in (base / "inputs").glob("*.json"):
        pack = read(path)
        if pack["name"] in packs:
            raise ValueError("Duplicate submission input")
        packs[pack["name"]] = pack
    if (
        set(packs) != set(names)
        or {n: fingerprint(p) for n, p in packs.items()} != config["input_sha256"]
    ):
        raise ValueError("Submission problem identity changed")
    reference_path = Path(config["references_path"])
    if digest(reference_path) != config["references_sha256"]:
        raise ValueError("Submission reference identity changed")
    with reference_path.open(encoding="utf-8") as stream:
        reference_rows = [json.loads(line) for line in stream if line.strip()]
    references = {row["name"]: row for row in reference_rows}
    if len(reference_rows) != len(references) or not set(names) <= set(references):
        raise ValueError("Submission references do not cover the cohort")
    model, effort = config["conditions"][0]
    rows, certificates = [], {}
    for name in names:
        cell = (
            model_output / "cells" / fingerprint((name, model, effort, config["mode"]))
        )
        inp = read(cell / "input.json")
        if (inp["name"], inp["model"], inp["effort"]) != (name, model, effort):
            raise ValueError("Submission proof belongs to another condition")
        choices = [(inp["seed_proof"], inp["seed_evaluation"], "verified_seed")]
        ledger = cell / "evidence/checks.jsonl"
        if ledger.exists():
            # JSONL is delimited by LF, including proofs containing literal U+2028.
            with ledger.open(encoding="utf-8") as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    check = json.loads(line)
                    if check.get("accepted"):
                        if check.get("all_versions_passed") is not True:
                            raise ValueError(
                                "Accepted proof lacks all-version verification"
                            )
                        choices.append(
                            (check["code"], check["evaluation"], check["number"])
                        )
        for proof, evaluation, _ in choices:
            _verified_proof(packs[name]["row"], references[name], proof, evaluation)
        # Accepted host checks replace the incumbent in ledger order.
        # Score/log accounting is separate from proof validity and delivery.
        proof, evaluation, basis = choices[-1]
        rows.append({"name": name, "proof": proof})
        certificates[name] = {
            "proof_sha256": sha(proof),
            "evaluation": evaluation,
            "basis": basis,
            "input_sha256": digest(cell / "input.json"),
            "checks_sha256": digest(ledger) if ledger.exists() else None,
            "model_result_present": (cell / "result.json").exists(),
        }
    return rows, {
        "status": "ready",
        "problems": len(rows),
        "model": model,
        "effort": effort,
        "references_sha256": config["references_sha256"],
        "certificates": certificates,
        "verification": "Saved host all-version proof certificates; no new Lean or model calls",
        "optimization_status": run["status"],
    }


def publish_model_solutions(model_output: Path, output: Path, names: list[str]) -> dict:
    """Atomically publish one ready-to-submit JSONL and its proof receipt."""
    rows, receipt = verified_model_solutions(model_output, names)
    output = Path(output)
    write_jsonl(output / "submission.jsonl", rows)
    receipt.update(
        submission=str(output / "submission.jsonl"),
        sha256=digest(output / "submission.jsonl"),
    )
    write_json(output / "submission-ready.json", receipt)
    return receipt
