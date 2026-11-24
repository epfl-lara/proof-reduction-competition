"""Read-only phase accounting and end-to-end evidence audits."""

from __future__ import annotations

from pathlib import Path

from proof_eval.evidence.audit import _implementation, _require
from proof_eval.evidence.io import digest, fingerprint, read
from proof_eval.evidence.proof_states import freeze_proof_states, guard_proof_states
from proof_eval.optimization.cohort import audit_cleanup, report_cleanup
from proof_eval.optimization.search_graph import one_sweep_plan
from proof_eval.paths import ROOT, SNAPSHOTS

from .audit import audit as audit_model


def report_pipeline(output: Path) -> dict:
    """Publish means only for complete conditions; keep every phase's time separate."""
    output = Path(output)
    config = read(output / "config.json")
    before = (
        report_cleanup(output / "before")
        if (output / "before" / "config.json").exists()
        else None
    )
    model = (
        read(output / "model" / "report.json")
        if (output / "model" / "report.json").exists()
        else {}
    )
    phases = {p.stem: read(p) for p in (output / "phases").glob("*.json")}
    run = read(output / "run.json") if (output / "run.json").exists() else {}
    terminal_error = run.get("error")
    conditions = []
    for condition in config["conditions"]:
        key = fingerprint(tuple(condition))
        summary = next(
            (
                s
                for s in model.get("conditions", [])
                if [s["model"], s["effort"]] == condition
            ),
            None,
        )
        after = (
            report_cleanup(output / "after" / key)
            if (output / "after" / key / "config.json").exists()
            else None
        )
        complete = bool(
            not terminal_error
            and phases.get("model", {}).get("status")
            in {"complete", "partial", "incomplete"}
            and summary
            and summary["complete"]
            and (
                not config["cleanup_before"]
                or before
                and before["status"] == "complete"
                and phases.get("before", {}).get("status") == "complete"
            )
            and (
                not config["cleanup_after"]
                or after
                and after["status"] == "complete"
                and phases.get("after_" + key, {}).get("status") == "complete"
            )
            and (
                output / "after" / key / "state.json"
                if config["cleanup_after"]
                else output / "model_states" / (key + ".json")
            ).exists()
        )
        conditions.append(
            {
                "model": condition[0],
                "effort": condition[1],
                "complete": complete,
                "expected": len(config["names"]),
                "model_results": summary,
                "before_cleanup": before,
                "after_cleanup": after,
                "final_mean_score": (
                    (
                        after["mean_output_score"]
                        if config["cleanup_after"]
                        else summary["mean_scores"]["combined_pct"]
                    )
                    if complete
                    else None
                ),
                "model_start_mean_score": (
                    summary.get("mean_model_start_score")
                    if summary and summary["complete"]
                    else None
                ),
                "model_gain_pp": (
                    summary.get("mean_model_gain_pp")
                    if summary and summary["complete"]
                    else None
                ),
                "selected_state": (
                    str(
                        (
                            output / "after" / key / "state.json"
                            if config["cleanup_after"]
                            else output / "model_states" / (key + ".json")
                        ).resolve()
                    )
                    if complete
                    else None
                ),
            }
        )
    finished = run.get("finished_epoch")
    return {
        "cohort_pipeline_version": 1,
        "status": (
            "complete"
            if conditions and all(c["complete"] for c in conditions)
            else "incomplete"
        ),
        "planned_cells": len(config["names"]) * len(conditions),
        "completed_cells": sum(c["expected"] for c in conditions if c["complete"]),
        "conditions": conditions,
        "phases": phases,
        "budget_scope": config["budget_scope"],
        "wall_seconds": (
            finished - run["started_epoch"] if finished is not None else None
        ),
        "starting_state": config["starting_proofs"]["source"] or "original",
        "timing_scope": config["timing_scope"],
        **({"error": terminal_error} if terminal_error else {}),
    }


def audit_pipeline(output: Path) -> dict:
    """Verify phase barriers, source linkage, all-version evidence and final exports."""
    output = Path(output)
    config, packs = read(output / "config.json"), read(output / "packs.json")
    _require(
        config["cohort_pipeline_version"] == 1
        and config["budget_scope"] == "model_phase"
        and config["cleanup_plan"]
        == one_sweep_plan(config["cleanup_plan"]["budget"]["min_gain"]).record(),
        "Unsupported pipeline accounting",
    )
    for relative, expected in config["code_sha256"].items():
        _implementation(relative, expected, ROOT, SNAPSHOTS, "cohort pipeline")
    for path, expected in config["file_sha256"].items():
        _require(digest(path) == expected, "Pipeline input changed")
    _require(
        config["input_sha256"] == {n: fingerprint(p) for n, p in packs.items()},
        "Pipeline packs changed",
    )
    references = Path(config["model"]["references"])
    guard_proof_states(config["starting_proofs"], packs, references)
    result = report_pipeline(output)
    _require(result["status"] == "complete", "Pipeline is incomplete")
    model_config = read(output / "model" / "config.json")
    _require(
        not model_config["initial_deterministic_methods"],
        "Cleanup leaked into model jobs",
    )
    for key in (
        "provider",
        "conditions",
        "budget_tracking",
        "problem_timeout_seconds",
        "budget_usd_per_problem",
    ):
        _require(
            model_config[key] == config["model"][key],
            "Model phase settings changed: " + key,
        )
    _require(
        set(model_config["names"]) == set(config["names"])
        and bool(model_config.get("restart_history_version"))
        == config["model"]["restart_history"],
        "Model cohort or history policy changed",
    )
    model_audit = audit_model(output / "model")
    phases = result["phases"]
    _require(phases["model"]["status"] == "complete", "Model phase did not complete")
    if config["cleanup_before"]:
        audit_cleanup(output / "before")
        before_config = read(output / "before" / "config.json")
        _require(
            before_config["starting_proofs"] == config["starting_proofs"],
            "Initial cleanup did not use the requested starting state",
        )
        _require(
            before_config["workers"] == config["before_workers"]
            and before_config["plan"] == config["cleanup_plan"],
            "Initial cleanup workers or plan changed",
        )
        _require(
            phases["before"]["finished_epoch"] <= phases["model"]["started_epoch"],
            "Model phase overlapped initial cleanup",
        )
        source = output / "before" / "state.json"
    else:
        source = config["starting_proofs"]["source"]
    if source is not None:
        expected_state = freeze_proof_states(Path(source), packs, references)
        _require(
            model_config.get("starting_proofs") == expected_state,
            "Model starting state differs from selected cleanup state",
        )
    else:
        _require(
            not model_config.get("starting_proofs"),
            "Original-start pipeline unexpectedly imported another proof state",
        )
    records = [read(p) for p in (output / "model" / "cells").glob("*/result.json")]
    for item in result["conditions"]:
        condition = (item["model"], item["effort"])
        key = fingerprint(condition)
        model_state = freeze_proof_states(
            output / "model_states" / (key + ".json"),
            packs,
            references,
            condition=condition,
        )
        selected = {
            r["name"]: r for r in records if (r["model"], r["effort"]) == condition
        }
        _require(set(selected) == set(packs), "Model result cohort changed")
        for name, record in selected.items():
            _require(
                model_state["cells"][name]["proof"] == record["selected_proof"],
                "Model state export changed",
            )
        if config["cleanup_after"]:
            folder = output / "after" / key
            audit_cleanup(folder)
            after_config = read(folder / "config.json")
            _require(
                after_config["workers"] == config["after_workers"]
                and after_config["plan"] == config["cleanup_plan"],
                "Final cleanup workers or plan changed",
            )
            _require(
                after_config["starting_proofs"] == model_state
                and after_config["condition"] == list(condition),
                "Final cleanup used another condition's results",
            )
            _require(
                phases["model"]["finished_epoch"]
                <= phases["after_" + key]["started_epoch"],
                "Final cleanup overlapped model batch",
            )
    return {
        "status": "passed",
        "conditions": len(result["conditions"]),
        "completed_cells": result["completed_cells"],
        "model_audit": model_audit,
        "config_sha256": digest(output / "config.json"),
    }
