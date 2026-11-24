"""Finish a saved, fully exhausted model cohort without replaying search."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from proof_eval.evidence.io import digest, read, write_json
from proof_eval.evidence.solutions import verified_model_solutions
from proof_eval.evidence.submission import verify_bundle
from proof_eval.harness.audit import audit
from proof_eval.harness.submission_phases import (
    _identity,
    _normal_search_outcomes,
    _phase,
    _ready,
)
from proof_eval.paths import ROOT


def finalize(producer: Path, work: Path, parent: Path, output: Path) -> dict:
    """Audit genuine saved work and publish a separate, explicitly linked delivery."""
    producer, work, parent, output = (
        p.resolve() for p in (producer, work, parent, output)
    )
    if output == parent or output.is_relative_to(parent):
        raise ValueError("Finalization needs a separate output; preserve the failed parent")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Finalization output already exists; inspect it instead of replaying")
    recipe = verify_bundle(producer)
    identity = _identity(producer, work)
    saved = _ready(parent, "search", identity)
    if saved is None or saved.get("GPU_server_stopped") is not True:
        raise ValueError("The saved model phase is absent or its server was not stopped")
    model = parent / "search/model"
    config, terminal = read(model / "config.json"), read(model / "run.json")
    if terminal.get("status") not in {"finished", "complete"}:
        raise ValueError("Model execution is active, interrupted or incomplete")
    outcomes = _normal_search_outcomes(model, recipe)
    if outcomes["normal_completed"] != len(recipe["names"]):
        raise ValueError("Saved model work did not complete every original problem window")

    started = time.time()
    # The corrected reader checks the immutable producer bytes, original clocks,
    # native closure, LF ledgers and certificates. It never executes the producer.
    model_audit = audit(model, code_root=producer)
    if model_audit.get("status") != "passed":
        raise ValueError("Saved model audit did not pass")
    rows, certificates = verified_model_solutions(model, recipe["names"])
    if read(parent / "model-certificates.json") != certificates:
        raise ValueError("The saved selected certificates changed")
    with (parent / "model-submission.jsonl").open(encoding="utf-8") as stream:
        exported = [json.loads(line) for line in stream if line.strip()]
    if exported != rows:
        raise ValueError("The saved automatic proof export changed")
    phase_identity = {
        **identity,
        "source_kind": "saved_model_finalization",
        "parent_output": str(parent),
        "parent_search_status": saved["status"],
        "parent_diagnostics": saved["diagnostics"],
        "model_calls": 0,
        "Lean_calls": 0,
    }
    with _phase(output, "search", phase_identity) as phase:
        for name in (
            "model-submission.jsonl",
            "model-state.json",
            "model-certificates.json",
            "search-timing.json",
        ):
            shutil.copy2(parent / name, output / name)
        shutil.copy2(parent / "model-submission.jsonl", output / "submission.jsonl")
        for name in ("model-timer-finished.json", "search-ready.json", "timing.json"):
            if (parent / name).is_file():
                shutil.copy2(parent / name, output / ("parent-" + name))
        write_json(output / "finalization-audit.json", model_audit)
        receipt = {
            **phase_identity,
            "status": "complete",
            "phase": "saved_model_finalization",
            "search_completed": True,
            "proof_delivery_completed": True,
            "optimization_status": terminal["status"],
            "outcomes": outcomes,
            "problems": len(rows),
            "submission": str(output / "model-submission.jsonl"),
            "sha256": digest(output / "model-submission.jsonl"),
            "proof_state_sha256": digest(output / "model-state.json"),
            "certificates_sha256": digest(output / "model-certificates.json"),
            "diagnostics": [],
            "GPU_server_stopped": True,
            "timing": saved["timing"],
            "parent_model_config_sha256": digest(model / "config.json"),
            "parent_model_terminal_sha256": digest(model / "run.json"),
            "parent_submission_sha256": saved["sha256"],
            "auditor_source_sha256": {
                name: digest(ROOT / name)
                for name in (
                    "src/proof_eval/harness/tracking_audit.py",
                    "src/proof_eval/harness/submission_finalize.py",
                )
            },
            "verification": "Passed saved model audit and all-required-version selected host certificates",
            "parent_failure_preserved": True,
            "original_problem_clocks_unchanged": True,
        }
        write_json(output / "search-ready.json", receipt)
        write_json(
            output / "submission-ready.json",
            {
                **receipt,
                "submission": str(output / "submission.jsonl"),
                "model_submission_sha256": receipt["sha256"],
                "proof_source": "verified_model",
                "cleanup_requested": False,
                "cleanup_completed": False,
            },
        )
        phase.update(status="complete", search_completed=True, proof_delivery_completed=True)
    finished = {
        "event": "SAVED_MODEL_FINALIZATION_FINISHED",
        "started_epoch": started,
        "finished_epoch": time.time(),
        "status": "complete",
        "parent_output": str(parent),
        "parent_failure_preserved": True,
        "search_replayed": False,
        "model_calls": 0,
        "Lean_calls": 0,
        "submission_sha256": receipt["sha256"],
    }
    write_json(output / "finalization-finished.json", finished)
    print(json.dumps(finished), flush=True)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ("producer-bundle", "work", "parent", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = finalize(args.producer_bundle, args.work, args.parent, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(2, f"{type(error).__name__}: {error}\n")
    print(json.dumps({"status": receipt["status"], "problems": receipt["problems"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
