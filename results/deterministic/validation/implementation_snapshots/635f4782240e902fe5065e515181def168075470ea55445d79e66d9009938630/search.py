"""Resumable per-theorem and batch model search; orchestration only."""

from __future__ import annotations

import fcntl
import json
from copy import deepcopy
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, now, read, write_json
from proof_eval.optimization.jobs import DeterministicCleanup
from proof_eval.paths import ROOT
from proof_eval.protocol import code_identity, extract_declaration
from proof_eval.providers.contracts import AgentGenerator
from proof_eval.providers.costs import CostConfig, generations_cost
from proof_eval.verification.api import Evaluator
from proof_eval.verification.feedback import build_validity_feedback
from proof_eval.verification.references import required_versions

from .agent import generate
from .configuration import (
    BASE,
    DETERMINISTIC_MODES,
    guard,
    historical,
    score_control,
    starting_point,
    structural_control,
)
from .prompts import messages
from .session import ProofSession


def run_cell(
    output: Path,
    config: dict,
    pack: dict,
    model: str,
    effort: str,
    evaluator: Evaluator,
    generator: AgentGenerator = generate,
) -> dict:
    mode = config["mode"]
    folder = output / "cells" / fingerprint((pack["name"], model, effort, mode))
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".cell.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (folder / "result.json").exists():
            return read(folder / "result.json")

        def checked_guard():
            return guard(config, pack, evaluator)

        checked_guard()
        seed = starting_point(pack, mode) if mode in DETERMINISTIC_MODES else None
        cleanup = None
        if seed is not None:
            base = read(Path(config.get("base_directory", BASE)) / "config.json")
            provenance = {
                "input_sha256": config["input_sha256"][pack["name"]],
                "contexts": base["contexts"][pack["name"]],
                "references_sha256": fingerprint(
                    {
                        v: e["reference"]
                        for v, e in pack["incumbent"]["per_version"].items()
                    }
                ),
                "code_sha256": config["code_sha256"],
            }
            cleanup = DeterministicCleanup(
                config["deterministic_jobs"], pack, evaluator, provenance, checked_guard
            )
        session = ProofSession(
            folder / "evidence",
            pack,
            evaluator,
            mode,
            guard=checked_guard,
            seed=seed,
            cleanup=cleanup,
        )
        context = {
            "name": pack["name"],
            "source_file": pack["row"]["file_path"],
            "required_versions": required_versions(pack),
            "source_projects": {
                v: str(evaluator.projects[(pack["row"]["source"], v)])
                for v in required_versions(pack)
            },
        }
        initial = messages(pack, seed=seed) if seed else messages(pack)
        write_json(
            folder / "input.json",
            {
                "name": pack["name"],
                "model": model,
                "effort": effort,
                "mode": mode,
                "messages": initial,
                "seed_proof": session.seed_code,
                "seed_evaluation": session.seed_evaluation,
            },
        )
        generations = []
        final_code, final_feedback = "", None
        max_rounds = config["max_outer_correctness_repairs"]
        for round_number in range(max_rounds + 1):
            checked_guard()
            request = deepcopy(initial)
            if round_number:
                request[1]["content"] += (
                    "\nCorrectness repair only. Repair this proposal using the following compiler feedback.\n"
                    + json.dumps(
                        {
                            "previous_declaration": final_code,
                            "correctness_feedback": final_feedback,
                        },
                        ensure_ascii=False,
                    )
                )
                # A failed unverified final is allowed another correctness-only turn.
                session.finished = None
                (session.folder / "finished.json").unlink(missing_ok=True)
            generation = generator(
                folder=folder / f"attempt_{round_number:02d}",
                messages=request,
                model=model,
                effort=effort,
                mode=mode,
                session=session,
                context=context,
                expected_cli=config["cli"],
                provider=config.get("provider", "codex"),
            )
            generations.append(generation)
            if generation["status"] != "received":
                break
            try:
                final_code = extract_declaration(
                    generation["content"], generation["finish_reason"]
                )
            except ValueError:
                final_code = generation["content"]
            before = len(session.checks)
            final_feedback = session.check(final_code, origin="final_harness")
            final_eval = (
                session.checks[-1]["evaluation"]
                if len(session.checks) > before
                else None
            )
            if mode != "correctness" or session.first_valid_code is not None:
                break
            if final_eval is None or final_eval["status"] not in (
                "invalid",
                "failed",
                "passed",
            ):
                break
            final_feedback = build_validity_feedback(final_eval, session.versions)
        checked_guard()
        before_final_cleanup = {
            "proof": session.best_code,
            "evaluation": deepcopy(session.best_evaluation),
        }
        if mode in DETERMINISTIC_MODES:
            session.deterministic(session.best_code, origin="final_harness")
        control_path, control = historical(pack["name"], model, effort)
        if (
            control_path
            and digest(control_path)
            != config["historical_control_sha256"][str(control_path.relative_to(ROOT))]
        ):
            raise ValueError("Historical control changed")
        historical_score = (
            control["selected_evaluation"]["scores"]["combined_pct"]
            if control
            else None
        )
        first_valid = next(
            (r for r in session.checks if r["all_versions_passed"]), None
        )
        unavailable = any(
            r["evaluation"]["status"] == "incomplete" for r in session.checks
        )
        structural_score = None
        if mode != "correctness":
            structural_path, structural = structural_control(
                pack["name"], model, effort
            )
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
                if generations[-1]["status"] == "received" and not unavailable
                else "incomplete"
            ),
            "generation_status": generations[-1]["status"],
            "generations": generations,
            "selected_proof": session.best_code,
            "selected_evaluation": session.best_evaluation,
            "first_valid_evaluation": (
                first_valid["evaluation"] if first_valid else None
            ),
            "first_valid_proof": first_valid["code"] if first_valid else None,
            "historical_score": historical_score,
            "gain_over_historical_pp": (
                None
                if historical_score is None
                else session.best_evaluation["scores"]["combined_pct"]
                - historical_score
            ),
            "structural_control_score": structural_score,
            "gain_over_structural_control_pp": (
                None
                if structural_score is None
                else session.best_evaluation["scores"]["combined_pct"]
                - structural_score
            ),
            "score_gain_after_first_valid_pp": (
                None
                if first_valid is None
                else session.best_evaluation["scores"]["combined_pct"]
                - first_valid["evaluation"]["scores"]["combined_pct"]
            ),
            "checks": len(session.checks),
            "agent_tool_checks": sum(
                r["origin"] == "agent_tool" for r in session.checks
            ),
            "valid_checks": sum(r["all_versions_passed"] for r in session.checks),
            "improvements": sum(r["accepted"] for r in session.checks),
            "stop": session.finished
            or {
                "kind": (
                    "model_final"
                    if generations[-1]["status"] == "received"
                    else "infrastructure"
                ),
                "reason": (
                    "Agent returned a final declaration"
                    if generations[-1]["status"] == "received"
                    else generations[-1].get("error")
                ),
            },
            "finished_at": now(),
        }
        if "cost_assumptions" in config:
            result["cost"] = generations_cost(
                CostConfig(model, effort, **config["cost_assumptions"]),
                generations,
                budget_usd=config["budget_usd_per_problem"],
            )
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
            tool_calls = [
                c for c in session.cleanup_calls if c["origin"] == "agent_tool"
            ]
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
                    else session.best_evaluation["scores"]["combined_pct"]
                    - control_score
                ),
                deterministic_calls=len(session.cleanup_calls),
                deterministic_tool_calls=len(tool_calls),
                valid_changed_proposals=len(valid_proposals),
                proposals_with_tool_cleanup=len(covered),
                deterministic_tool_coverage_pct=(
                    100 * len(covered) / len(valid_proposals)
                    if valid_proposals
                    else None
                ),
                incomplete_cleanups=sum(
                    c["status"] not in ("complete", "skipped_invalid")
                    for c in session.cleanup_calls
                ),
            )
            if result["incomplete_cleanups"]:
                result["status"] = "incomplete"
        write_json(folder / "result.json", result)
        return result
