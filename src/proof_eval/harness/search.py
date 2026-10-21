"""Resumable per-theorem and batch model search; orchestration only."""

from __future__ import annotations

import fcntl
import json
import time
from copy import deepcopy
from pathlib import Path

from proof_eval.evidence.io import fingerprint, read, write_json
from proof_eval.optimization.jobs import DeterministicCleanup
from proof_eval.protocol import extract_declaration
from proof_eval.providers.contracts import AgentGenerator
from proof_eval.providers.costs import CostConfig
from proof_eval.providers.retries import RECOVERY_BACKOFF_SECONDS
from proof_eval.providers.spending import native_cost_guard
from proof_eval.verification.api import Evaluator
from proof_eval.verification.feedback import build_validity_feedback
from proof_eval.verification.initial import measure_original, private_evaluator
from proof_eval.verification.references import required_versions

from .agent import generate
from .attempts import finish_attempt, record_stop, start_attempt
from .configuration import (
    BASE,
    DETERMINISTIC_MODES,
    guard,
    starting_point,
)
from .incumbents import select_seed
from .initial import initial_optimization
from .limits import time_budget_summary
from .outcomes import finalize_cell
from .prompts import budget_suffix, messages
from .restart_history import add_history, build_history, scope_for
from .session import ProofSession
from .tracking import CLEANUP_RESERVE_SECONDS, attempt_cost, stop_decision


def run_cell(
    output: Path,
    config: dict,
    pack: dict,
    model: str,
    effort: str,
    evaluator: Evaluator,
    generator: AgentGenerator = generate,
) -> dict:
    """Run a theorem under its track budget, including custom generators."""
    if config.get("first_attempt_condition") is not None:
        raise ValueError("Mixed-model search is retired; saved runs are read-only")
    if "problem_timeout_seconds" in config or config.get("budget_tracking") is not None:
        from .budget import run_cell as supervised_cell

        supervised_config = {
            "problem_timeout_seconds": (
                None if config.get("budget_tracking") == "cost" else 57 * 60
            ),
            **config,
        }
        return supervised_cell(
            output,
            supervised_config,
            pack,
            model,
            effort,
            evaluator,
            generator=None if generator is generate else generator,
        )
    return _run_cell(output, config, pack, model, effort, evaluator, generator)


def _run_cell(
    output: Path,
    config: dict,
    pack: dict,
    model: str,
    effort: str,
    evaluator: Evaluator,
    generator: AgentGenerator = generate,
) -> dict:
    """Internal worker; new configurations require the supervisor's budget marker."""
    if config.get("first_attempt_condition") is not None:
        raise ValueError("Mixed-model search is retired; saved runs are read-only")
    mode = config["mode"]
    folder = output / "cells" / fingerprint((pack["name"], model, effort, mode))
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".cell.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (folder / "result.json").exists():
            return read(folder / "result.json")
        if config.get("initial_pipeline_version"):
            if not (folder / "problem_started.json").exists():
                raise ValueError(
                    "Original measurement requires the supervisor-owned problem clock"
                )
            evaluator = private_evaluator(evaluator, folder, pack)

        def checked_guard():
            return guard(config, pack, evaluator)

        checked_guard()
        seed = (
            measure_original(
                evaluator,
                folder,
                pack,
                timeout_retries=config.get("initial_measurement_timeout_retries", 0),
            )
            if config.get("initial_pipeline_version")
            else (starting_point(pack, mode) if mode in DETERMINISTIC_MODES else None)
        )
        if seed is not None and not config.get("initial_pipeline_version"):
            seed = select_seed(config, pack, model, effort, seed)
        cleanup = None
        if seed is not None and not config.get("initial_pipeline_version"):
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
                config["deterministic_jobs"],
                pack,
                evaluator,
                provenance,
                checked_guard,
                **(
                    {"methods": tuple(config["deterministic_methods"])}
                    if config.get("proof_theory_cleanup_version")
                    else {}
                ),
            )
        budget = (
            read(folder / "budget_started.json")
            if (folder / "budget_started.json").exists()
            else None
        )
        if config.get("problem_timeout_seconds") is not None and budget is None:
            raise ValueError(
                "A prepared theorem must run under the durable deadline supervisor"
            )
        session = ProofSession(
            folder / "evidence",
            pack,
            evaluator,
            mode,
            guard=checked_guard,
            seed=seed,
            cleanup=cleanup,
            deadline_at=budget["deadline_epoch"] if budget else None,
            problem_timeout_seconds=budget["timeout_seconds"] if budget else None,
            semantic_config=config.get("semantic_search"),
            web_config=config.get("web_search"),
            restart_scope=(
                scope_for(config, pack["name"], model, effort)
                if config.get("restart_history_version")
                else None
            ),
            original_measurement=(
                seed[1] if config.get("initial_pipeline_version") else None
            ),
        )
        if config.get("initial_pipeline_version"):
            initial_optimization(session, folder, config, budget)
        if config.get("proof_theory_cleanup_version") and not any(
            call["origin"] == "initial_harness" for call in session.cleanup_calls
        ):
            initial_cleanup = DeterministicCleanup(
                config["deterministic_jobs"],
                pack,
                evaluator,
                provenance,
                checked_guard,
                methods=tuple(config["initial_deterministic_methods"]),
            )
            session.deterministic(
                seed[0], origin="initial_harness", cleanup=initial_cleanup
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
        if config.get("web_search") is not None:
            context["web_search"] = config["web_search"]
        initial = messages(
            pack,
            seed=(
                (session.best_code, session.best_evaluation)
                if config.get("proof_theory_cleanup_version")
                or config.get("initial_pipeline_version")
                else seed
            ),
            web_search=config.get("web_search") is not None,
        )
        if (
            config.get("proof_theory_cleanup_version")
            or config.get("initial_pipeline_version")
        ) and (folder / "input.json").exists():
            initial = read(folder / "input.json")["messages"]
        budget_tracking = config.get("budget_tracking")
        budget_usd = config.get("budget_usd_per_problem", 3.0)
        max_restarts = config.get("max_budget_restarts", 20)
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
        max_rounds = (
            config.get("max_outer_correctness_repairs", 0)
            if mode == "correctness"
            else (max_restarts if budget_tracking in ("cost", "time") else 0)
        )
        max_rounds += config.get("max_transport_restarts", 0)
        transport_restarts_used = 0
        for round_number in range(max_rounds + 1):
            checked_guard()
            admission_epoch = time.time()
            remaining = budget["deadline_epoch"] - admission_epoch if budget else None
            if remaining is not None and remaining <= 0:
                record_stop(
                    folder,
                    {
                        "kind": "time_limit",
                        "reason": "Whole-problem wall deadline reached",
                    },
                    round_number - 1 if generations else None,
                    at_epoch=admission_epoch,
                )
                break
            if (
                round_number
                and remaining is not None
                and remaining
                <= config.get("cleanup_reserve_seconds", CLEANUP_RESERVE_SECONDS)
            ):
                record_stop(
                    folder,
                    {
                        "kind": "cleanup_reserve",
                        "reason": "Remaining whole-problem time is reserved for final cleanup",
                    },
                    round_number - 1,
                    at_epoch=admission_epoch,
                )
                break
            cost_before = attempt_cost(
                config, model, effort, generations, name=pack["name"]
            )
            if round_number == 0:
                request = deepcopy(initial)
            elif mode == "correctness":
                request = deepcopy(initial)
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
                session.reset_for_attempt()
            else:
                request = messages(
                    pack,
                    seed=(session.best_code, session.best_evaluation),
                    web_search=config.get("web_search") is not None,
                )
                session.reset_for_attempt()
            cost_guard = None
            if budget_tracking == "cost":
                total = cost_before["total_usd"]
                if (
                    round_number == 0
                    and total is not None
                    and total >= budget_usd - 1e-12
                ):
                    record_stop(
                        folder,
                        {
                            "kind": "cost_reserve",
                            "reason": "Prior spending already reached the problem budget",
                        },
                        None,
                    )
                    break
                if total is None or total >= budget_usd - 1e-12:
                    raise RuntimeError(
                        "Attempt admission requires known spending below the budget"
                    )
                cost_guard = native_cost_guard(
                    config.get("provider", "codex"),
                    CostConfig(model, effort, **config.get("cost_assumptions", {})),
                    budget_usd - total,
                )
                if cost_guard.get("limit_tokens") == 0:
                    record_stop(
                        folder,
                        {
                            "kind": "cost_reserve",
                            "reason": "Remaining estimated budget cannot fund one conservatively priced output token",
                        },
                        round_number - 1 if generations else None,
                    )
                    break
            if session.restart_history is not None:
                session.restart_history.attempt = round_number
                add_history(
                    request,
                    build_history(
                        session.restart_history.scope,
                        session.checks,
                        session.restart_history.events,
                        session.seed_code,
                    ),
                )
            request[1]["content"] += budget_suffix(
                config, budget, cost_before, remaining, round_number
            )
            if round_number == 0:
                initial = request
                saved_input = read(folder / "input.json")
                write_json(folder / "input.json", {**saved_input, "messages": initial})
            timeout = (
                min(config["generation_timeout"], max(0.0, remaining))
                if budget
                else None
            )
            attempt_folder = folder / f"attempt_{round_number:02d}"
            if config.get("attempt_evidence_version"):
                start_attempt(
                    attempt_folder,
                    session,
                    request,
                    round_number,
                    cost_before,
                    timeout,
                    cost_guard,
                    remaining,
                )
            generation = generator(
                folder=attempt_folder,
                messages=request,
                model=model,
                effort=effort,
                mode=mode,
                session=session,
                context=context,
                expected_cli=config["cli"],
                provider=config.get("provider", "codex"),
                **({"timeout": timeout} if "problem_timeout_seconds" in config else {}),
                **({"cost_budget": cost_guard} if cost_guard else {}),
                **(
                    {"instructions": config["tool_instructions"]}
                    if "tool_instructions" in config
                    else {}
                ),
            )
            generations.append(generation)
            if generation["status"] != "received":
                cost_after = attempt_cost(
                    config, model, effort, generations, name=pack["name"]
                )
                if config.get("attempt_evidence_version"):
                    finish_attempt(attempt_folder, session, generation, cost_after)
                decision_epoch = time.time()
                stop = stop_decision(
                    config,
                    generation,
                    cost_after,
                    unavailable=any(
                        check["evaluation"]["status"] == "incomplete"
                        for check in session.checks
                    ),
                    round_number=round_number,
                    time_remaining=(
                        budget["deadline_epoch"] - decision_epoch if budget else None
                    ),
                    transport_restarts_used=transport_restarts_used,
                )
                if stop is None:
                    if generation.get("termination") != "cost_limit":
                        delay = RECOVERY_BACKOFF_SECONDS * 2 ** min(
                            transport_restarts_used, 5
                        )
                        transport_restarts_used += 1
                        # The supervisor owns this wait and retains the same deadline.
                        time.sleep(delay)
                    continue
                record_stop(folder, stop, round_number, at_epoch=decision_epoch)
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
            cost_after = attempt_cost(
                config, model, effort, generations, name=pack["name"]
            )
            if config.get("attempt_evidence_version"):
                finish_attempt(attempt_folder, session, generation, cost_after)
            if mode == "correctness":
                if session.first_valid_code is not None:
                    break
                if final_eval is None or final_eval["status"] not in (
                    "invalid",
                    "failed",
                    "passed",
                ):
                    break
                final_feedback = build_validity_feedback(final_eval, session.versions)
            else:
                decision_epoch = time.time()
                stop = stop_decision(
                    config,
                    generation,
                    cost_after,
                    unavailable=any(
                        check["evaluation"]["status"] == "incomplete"
                        for check in session.checks
                    ),
                    round_number=round_number,
                    time_remaining=(
                        budget["deadline_epoch"] - decision_epoch if budget else None
                    ),
                    transport_restarts_used=transport_restarts_used,
                )
                if stop is not None:
                    # Default runs retain the model's factual finish reason.
                    if stop["kind"] == "model_final" and session.finished:
                        stop = session.finished
                    record_stop(folder, stop, round_number, at_epoch=decision_epoch)
                    break
        checked_guard()
        before_final_cleanup = {
            "proof": session.best_code,
            "evaluation": deepcopy(session.best_evaluation),
        }
        write_json(folder / "before_final_cleanup.json", before_final_cleanup)
        if mode in DETERMINISTIC_MODES and not config.get("initial_pipeline_version"):
            session.deterministic(session.best_code, origin="final_harness")
        return finalize_cell(
            folder,
            config,
            pack,
            model,
            effort,
            session,
            generations,
            before_final_cleanup,
            time_budget=time_budget_summary(folder, exhausted=False),
        )
