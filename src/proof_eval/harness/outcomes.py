"""Select and describe a theorem outcome from host-owned, verified evidence."""

from __future__ import annotations

import time
from pathlib import Path

from proof_eval.evidence.io import digest, now, read, write_json
from proof_eval.paths import ROOT
from proof_eval.protocol import code_identity

from .attempts import attempt_folders
from .configuration import (
    DETERMINISTIC_MODES,
    historical,
    score_control,
    structural_control,
)
from .session import ProofSession
from .tracking import attempt_cost


def finalize_cell(
    folder: Path,
    config: dict,
    pack: dict,
    model: str,
    effort: str,
    session: ProofSession,
    generations: list[dict],
    before_final_cleanup: dict,
    *,
    time_budget: dict | None = None,
) -> dict:
    """No Lean/model calls: keep the best certified ledger proof after any stop."""
    mode = config["mode"]
    final_generation = (
        generations[-1]
        if generations
        else {
            "status": (
                "budget_exhausted"
                if time_budget and time_budget["exhausted"]
                else "not_started"
            )
        }
    )
    control_path, control = historical(pack["name"], model, effort)
    if (
        control_path
        and digest(control_path)
        != config["historical_control_sha256"][str(control_path.relative_to(ROOT))]
    ):
        raise ValueError("Historical control changed")
    historical_score = (
        control["selected_evaluation"]["scores"]["combined_pct"] if control else None
    )
    first_valid = next((r for r in session.checks if r["all_versions_passed"]), None)
    unavailable = any(r["evaluation"]["status"] == "incomplete" for r in session.checks)
    host_stop = (
        read(folder / "search_stop.json")
        if (folder / "search_stop.json").exists()
        else None
    )
    controlled_cost_stop = final_generation.get("termination") == "cost_limit"
    structural_score = None
    if mode != "correctness":
        structural_path, structural = structural_control(pack["name"], model, effort)
        if structural_path:
            if (
                digest(structural_path)
                != config["structural_control_sha256"][
                    str(structural_path.relative_to(ROOT))
                ]
            ):
                raise ValueError("Structural control changed")
            structural_score = structural["selected_evaluation"]["scores"][
                "combined_pct"
            ]
    result = {
        "provider": config.get("provider", "codex"),
        "name": pack["name"],
        "model": model,
        "effort": effort,
        "mode": mode,
        "status": (
            "complete"
            if (
                final_generation["status"] == "received"
                or controlled_cost_stop
                or (host_stop and host_stop["kind"] == "cost_reserve")
                or (
                    final_generation["status"] == "budget_exhausted"
                    and time_budget
                    and time_budget["exhausted"]
                )
            )
            and not unavailable
            else "incomplete"
        ),
        "generation_status": final_generation["status"],
        "generations": generations,
        "selected_proof": session.best_code,
        "selected_evaluation": session.best_evaluation,
        "first_valid_evaluation": (first_valid["evaluation"] if first_valid else None),
        "first_valid_proof": first_valid["code"] if first_valid else None,
        "historical_score": historical_score,
        "gain_over_historical_pp": (
            None
            if historical_score is None
            else session.best_evaluation["scores"]["combined_pct"] - historical_score
        ),
        "structural_control_score": structural_score,
        "gain_over_structural_control_pp": (
            None
            if structural_score is None
            else session.best_evaluation["scores"]["combined_pct"] - structural_score
        ),
        "score_gain_after_first_valid_pp": (
            None
            if first_valid is None
            else session.best_evaluation["scores"]["combined_pct"]
            - first_valid["evaluation"]["scores"]["combined_pct"]
        ),
        "checks": len(session.checks),
        "agent_tool_checks": sum(r["origin"] == "agent_tool" for r in session.checks),
        "valid_checks": sum(r["all_versions_passed"] for r in session.checks),
        "improvements": sum(r["accepted"] for r in session.checks),
        "stop": (
            {"kind": "time_limit", "reason": "Whole-problem wall deadline reached"}
            if time_budget and time_budget["exhausted"]
            else host_stop or session.finished
        )
        or {
            "kind": (
                "model_final"
                if final_generation["status"] == "received"
                else "infrastructure"
            ),
            "reason": (
                "Agent returned a final declaration"
                if final_generation["status"] == "received"
                else final_generation.get("error")
            ),
        },
        "finished_at": now(),
    }
    if "cost_assumptions" in config:
        result["cost"] = attempt_cost(
            config, model, effort, generations, name=pack["name"], final=True
        )
    if config.get("budget_tracking") is not None:
        result["budget_tracking"] = config["budget_tracking"]
        result["budget_outcome"] = {
            "stop_kind": result["stop"]["kind"],
            "cost_known": (
                result.get("cost", {}).get("total_usd") is not None
                and result.get("cost", {}).get("complete_usage") is not False
            ),
            "cost_enforcement": (
                (
                    "host_stream_usage"
                    if config.get("provider") == "agy"
                    else "native_response_boundaries"
                )
                if config["budget_tracking"] == "cost"
                else "whole_problem_deadline"
            ),
            "hard_cost_cap": False,
        }
        if config.get("usage_policy") == "best_effort":
            result["usage_policy"] = "best_effort"
            result["budget_outcome"]["cost_estimated"] = (
                result.get("cost", {}).get("total_usd") is not None
            )
            result["budget_outcome"]["usage_complete"] = (
                result.get("cost", {}).get("complete_usage") is not False
                and result.get("cost", {}).get("total_usd") is not None
            )
    if config.get("attempt_evidence_version"):
        result["attempts"] = [
            read(path / "attempt.json") for path in attempt_folders(folder)
        ]
    if host_stop and host_stop["kind"] in (
        "infrastructure",
        "unknown_usage",
        "unknown_cost",
        "unknown_price",
        "transport_recovery_limit",
    ):
        result["status"] = "incomplete"
    if mode in DETERMINISTIC_MODES:
        score_path, control = score_control(pack["name"], model, effort)
        if (
            score_path
            and digest(score_path)
            != config["score_control_sha256"][str(score_path.relative_to(ROOT))]
        ):
            raise ValueError("Score-only control changed")
        control_score = (
            control["selected_evaluation"]["scores"]["combined_pct"]
            if control
            else None
        )
        valid_proposals = {
            r["code_sha256"]
            for r in session.checks
            if r["origin"] in ("agent_tool", "deterministic_input", "final_harness")
            and r["all_versions_passed"]
            and not r["duplicate"]
            and r["code_sha256"] != code_identity(pack["row"], session.seed_code)
        }
        tool_calls = [c for c in session.cleanup_calls if c["origin"] == "agent_tool"]
        covered = valid_proposals & {
            c["input_code_sha256"]
            for c in tool_calls
            if c["status"] != "skipped_invalid"
        }
        result.update(
            seed_proof=session.seed_code,
            seed_evaluation=session.seed_evaluation,
            before_final_cleanup=before_final_cleanup,
            final_cleanup_gain_pp=session.best_evaluation["scores"]["combined_pct"]
            - before_final_cleanup["evaluation"]["scores"]["combined_pct"],
            score_control_score=control_score,
            gain_over_score_control_pp=(
                None
                if control_score is None
                else session.best_evaluation["scores"]["combined_pct"] - control_score
            ),
            deterministic_calls=len(session.cleanup_calls),
            deterministic_tool_calls=len(tool_calls),
            valid_changed_proposals=len(valid_proposals),
            proposals_with_tool_cleanup=len(covered),
            deterministic_tool_coverage_pct=(
                100 * len(covered) / len(valid_proposals) if valid_proposals else None
            ),
            incomplete_cleanups=sum(
                c["status"] not in ("complete", "skipped_invalid")
                for c in session.cleanup_calls
            ),
        )
        if result["incomplete_cleanups"]:
            result["status"] = "incomplete"
    if time_budget is not None:
        result["time_budget"] = time_budget
        result["final_cleanup_status"] = (
            "complete"
            if any(c["origin"] == "final_harness" for c in session.cleanup_calls)
            else (
                "interrupted_time_limit"
                if (session.folder / "cleanup_started.json").exists()
                and read(session.folder / "cleanup_started.json").get(
                    "origin", "final_harness"
                )
                == "final_harness"
                else (
                    "skipped_time_limit"
                    if time_budget["exhausted"]
                    else "not_applicable"
                )
            )
        )
        if time_budget["exhausted"] and final_generation["status"] not in (
            "received",
            "budget_exhausted",
        ):
            result["status"] = "incomplete"
    if config.get("proof_theory_cleanup_version"):
        initial_call = next(
            (c for c in session.cleanup_calls if c["origin"] == "initial_harness"), None
        )
        result["initial_cleanup_status"] = (
            initial_call["status"]
            if initial_call
            else (
                "interrupted_time_limit"
                if (session.folder / "cleanup_started.json").exists()
                and read(session.folder / "cleanup_started.json").get("origin")
                == "initial_harness"
                else "skipped_time_limit"
            )
        )
    if config.get("initial_pipeline_version"):
        initial_path = folder / "initial_measurement.json"
        phase_path = folder / "initial_optimization/result.json"
        result["final_cleanup_status"] = "disabled"
        result["initial_measurement_status"] = (
            "complete" if initial_path.exists() else "interrupted"
        )
        result["initial_cleanup_status"] = (
            read(phase_path)["status"] if phase_path.exists() else "interrupted"
        )
        result["initial_cleanup_gain_pp"] = (
            read(phase_path)["gain_pp"] if phase_path.exists() else 0.0
        )
        result["pipeline_elapsed_seconds"] = (
            time.time() - read(folder / "problem_started.json")["started_epoch"]
        )
        if not initial_path.exists():
            result["status"] = "incomplete"
    if config.get("deterministic_checkpoint"):
        checkpoint_path = folder / "checkpoint.json"
        start = (
            read(checkpoint_path)["model_start_score"]
            if checkpoint_path.exists()
            else None
        )
        result["model_start_score"] = start
        result["model_gain_pp"] = (
            result["selected_evaluation"]["scores"]["combined_pct"] - start
            if start is not None
            else None
        )
    if config.get("model_phase_version"):
        if config.get("starting_proofs"):
            selected_path = folder / "starting_proof.json"
            start = (
                read(selected_path)["model_start_score"]
                if selected_path.exists()
                else None
            )
        elif config.get("deterministic_checkpoint"):
            start = result["model_start_score"]
        else:
            measured = folder / "initial_measurement.json"
            start = (
                read(measured)["evaluation"]["scores"]["combined_pct"]
                if measured.exists()
                else None
            )
        result["model_start_score"] = start
        result["model_gain_pp"] = (
            result["selected_evaluation"]["scores"]["combined_pct"] - start
            if start is not None
            else None
        )
        result["model_phase_elapsed_seconds"] = result["pipeline_elapsed_seconds"]
        result["phase_accounting"] = "model_only_external_cleanup_excluded"
        if start is None:
            result["status"] = "incomplete"
    write_json(folder / "result.json", result)
    return result
