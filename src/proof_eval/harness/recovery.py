"""Finalize controlled deadline stops solely from saved proof certificates."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from proof_eval.evidence.io import fingerprint, now, read, write_json, write_jsonl
from proof_eval.providers import deadline_cleanup, signal_scope
from proof_eval.providers.monitoring import verified_stream_stop
from proof_eval.providers.registry import adapter
from proof_eval.providers.response_usage import reconcile_usage
from proof_eval.providers.retries import reconnect_notice
from proof_eval.verification.api import Evaluator

from .attempts import attempt_folders, finish_attempt
from .configuration import starting_point
from .incumbents import select_seed
from .limits import time_budget_summary
from .outcomes import finalize_cell
from .prompts import messages
from .restart_history import scope_for
from .session import ProofSession
from .tracking import attempt_cost


def _generation(folder: Path, provider: str) -> dict:
    path = folder / "generation.json"
    if path.exists():
        return read(path)
    if not (folder / "request.json").exists():
        parsed = {
            "status": "budget_exhausted",
            "termination": "problem_deadline",
            "dispatch_status": "not_dispatched",
            "provider": provider,
            "usage": None,
            "finished_at": now(),
            "error": "Whole-problem deadline reached before native request setup",
        }
        write_json(path, parsed)
        return parsed
    events = []
    event_path = folder / "events.jsonl"
    for line in event_path.read_text().splitlines() if event_path.exists() else []:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            # A killed CLI can leave a partial last line; keep its raw bytes.
            break
    module = adapter(provider)
    request = read(folder / "request.json")
    process_path = folder / "process.json"
    process = read(process_path) if process_path.exists() else {}
    ownership_path = folder / "process_ownership.json"
    ownership = read(ownership_path) if ownership_path.exists() else None
    final_path = folder / "workspace/final.txt"
    final = final_path.read_text() if final_path.exists() else ""
    if not final:
        answers = [
            e["item"].get("text", "")
            for e in events
            if e.get("type") == "item.completed"
            and e.get("item", {}).get("type") == "agent_message"
        ]
        final = answers[-1] if answers else ""
        if not final and provider == "agy":
            responses = [
                e["result"].get("response", "")
                for e in events
                if module.terminal(e) and isinstance(e.get("result"), dict)
            ]
            final = responses[-1] if responses else ""
    kwargs = {}
    if provider == "agy":
        request = read(folder / "request.json")
        kwargs["requested_slug"] = module.slug(
            request["model"], request["reasoning_effort"]
        )
    parsed = module.parse_events(
        events,
        final,
        ownership["native_returncode"] if ownership is not None else 0,
        **kwargs,
    )
    if provider == "codex":
        request = read(folder / "request.json")
        if request["cli"].get("response_usage_schema_version") in (1, 2):
            parsed = reconcile_usage(
                folder,
                events,
                request["model"],
                parsed,
                schema_version=request["cli"]["response_usage_schema_version"],
            )
    if parsed["status"] == "received":
        final_path.write_text(parsed["content"])
    elif (
        not parsed.get("events_errors")
        or all(reconnect_notice(e) for e in parsed["events_errors"])
    ) and not any(module.terminal(e) for e in events):
        parsed.update(
            status="budget_exhausted",
            error="Whole-problem wall deadline reached; not resampled",
        )
    parsed.update(provider=provider, finished_at=now(), termination="problem_deadline")
    if provider == "lemex-local" and process.get("native_supervisor"):
        if ownership is not None:
            if ownership.get("supervisor") != {
                k: process[k] for k in ("pid", "start_ticks")
            }:
                raise ValueError("Recovered native owner identity changed")
            parsed.update(process_ownership=ownership, supervisor_returncode=0)
            if ownership.get("cleanup", {}).get("complete") is not True:
                parsed.update(
                    status="transport_error",
                    error="Native cleanup incomplete; not resampled",
                )
            if ownership.get("supervisor_signals"):
                parsed.update(
                    status="transport_error",
                    external_supervisor_signal=True,
                    error="Native supervisor received an external signal; not resampled",
                )
        elif process.get("ownership_schema_version") == 2:
            stopped = read(folder.parent / "budget_end.json")
            try:
                native = deadline_cleanup.native_stop(folder, process)
                if native is not None:
                    stopped = native
                marker = deadline_cleanup.record(
                    folder,
                    process,
                    stopped,
                    source=(
                        "native_timeout"
                        if native is not None
                        else "whole_problem_deadline"
                    ),
                )
            except deadline_cleanup.CleanupEvidenceError as error:
                parsed.update(
                    status="transport_error",
                    error=str(error),
                    host_deadline_cleanup_refusal=deadline_cleanup.refusal(
                        folder, process, stopped, error
                    ),
                )
                # The whole-problem deadline is real, but it cannot certify a
                # native owner absent from its snapshot. Persist the incomplete
                # generation so finalize_cell retains the saved best certificate.
                write_json(path, parsed)
                return parsed
            parsed.update(
                status="budget_exhausted",
                host_deadline_cleanup=marker,
                error="Whole-problem wall deadline reached; not resampled",
            )
        identity = request["cli"].get("signal_scope")
        if identity is not None:
            command = read(folder / "command.json")["isolated_argv"]
            parsed["signal_scope"] = {
                "status": "verified",
                **signal_scope.evidence(
                    folder,
                    identity,
                    command,
                    process,
                    ownership,
                    allow_partial=parsed["status"] == "budget_exhausted",
                ),
            }
            write_json(folder / "signal_scope.json", parsed["signal_scope"])
    if (
        provider == "agy"
        and verified_stream_stop(
            folder, events, request.get("cost_budget"), module.stream_usage
        )
        and parsed.get("actual_model") in (None, kwargs["requested_slug"])
    ):
        parsed.update(
            status="budget_exhausted",
            termination="cost_limit",
            cost_budget=request["cost_budget"],
            host_cost_stop_sha256=fingerprint(read(folder / "cost_stop.json")),
            error="Host stream cost guard stopped the attempt; not resampled",
        )
    write_json(path, parsed)
    return parsed


def recover_cell(
    folder: Path,
    config: dict,
    pack: dict,
    model: str,
    effort: str,
    evaluator: Evaluator,
) -> dict:
    """Never dispatch a model, compile Lean, or restart deterministic work."""
    end = read(folder / "budget_end.json")
    if not end["exhausted"]:
        raise ValueError("Deadline recovery requires a supervised deadline stop")
    result_path = folder / "result.json"
    worker_result = folder / "worker_result.json"
    if result_path.exists() and not worker_result.exists():
        # Keep the worker's exact bytes when it finalized before the supervisor.
        result_path.replace(worker_result)
    seed = starting_point(pack, config["mode"])
    seed = select_seed(config, pack, model, effort, seed)
    original = None
    if config.get("initial_pipeline_version"):
        from proof_eval.verification.references import original_evaluation

        measurement = folder / "initial_measurement.json"
        original = (
            read(measurement)["evaluation"]
            if measurement.exists()
            else original_evaluation(pack)
        )
        seed = (pack["row"]["src"], original)
    session = ProofSession(
        folder / "evidence",
        pack,
        evaluator,
        config["mode"],
        seed=seed,
        restart_scope=(
            scope_for(config, pack["name"], model, effort)
            if config.get("restart_history_version")
            else None
        ),
        original_measurement=original,
    )
    if config.get("initial_pipeline_version"):
        phase_folder = folder / "initial_optimization"
        if (phase_folder / "certificates.json").exists() and not any(
            c["origin"] == "initial_harness" for c in session.checks
        ):
            from proof_eval.optimization.bounded import finish_bounded
            from proof_eval.protocol import code_identity

            phase = (
                read(phase_folder / "result.json")
                if (phase_folder / "result.json").exists()
                else finish_bounded(
                    phase_folder,
                    pack["row"],
                    status="problem_deadline",
                    stopped=end["work_stopped_epoch"],
                )
            )
            if phase["accepted_improvements"]:
                session.cache[code_identity(session.row, phase["proof"])] = phase[
                    "evaluation"
                ]
                session.check(phase["proof"], origin="initial_harness")
    if not (folder / "input.json").exists():
        write_json(
            folder / "input.json",
            {
                "name": pack["name"],
                "model": model,
                "effort": effort,
                "mode": config["mode"],
                "messages": messages(pack, seed=seed),
                "seed_proof": session.seed_code,
                "seed_evaluation": session.seed_evaluation,
            },
        )
    generations = [
        _generation(attempt, config["provider"])
        for attempt in attempt_folders(folder)
        if (attempt / "request.json").exists() or (attempt / "attempt.json").exists()
    ]
    if config.get("attempt_evidence_version"):
        for index, attempt in enumerate(attempt_folders(folder)):
            record = read(attempt / "attempt.json")
            if record["status"] == "started":
                finish_attempt(
                    attempt,
                    session,
                    generations[index],
                    attempt_cost(
                        config,
                        model,
                        effort,
                        generations[: index + 1],
                        name=pack["name"],
                    ),
                )
    pending = session.folder / "cleanup_started.json"
    if pending.exists():
        partial = read(pending)
        origin = partial.get("origin", "final_harness")
        already_recorded = any(
            c["input_check"] == partial["input_check"] for c in session.cleanup_calls
        )
        if "job" in partial and not already_recorded:
            job = partial["job"]
            after = next(
                (
                    c
                    for c in session.checks
                    if c["origin"] == "deterministic_" + origin
                    and c["code"] == job["proof"]
                    and c["evaluation"] == job["evaluation"]
                ),
                None,
            )
            if after is not None:
                record = {
                    "number": len(session.cleanup_calls) + 1,
                    "at": now(),
                    "origin": origin,
                    "input_code_sha256": partial["input_code_sha256"],
                    "input_check": partial["input_check"],
                    "output_check": after["number"],
                    "status": job["status"],
                    "job_path": job["job_path"],
                    "job_result_sha256": job["job_result_sha256"],
                    "counters": job["counters"],
                    "reused": job.get("reused", False),
                }
                write_jsonl(
                    session.folder / "deterministic.jsonl",
                    session.cleanup_calls + [record],
                )
                session.cleanup_calls.append(record)
    before = (
        read(folder / "before_final_cleanup.json")
        if (folder / "before_final_cleanup.json").exists()
        else {
            "proof": session.best_code,
            "evaluation": deepcopy(session.best_evaluation),
        }
    )
    return finalize_cell(
        folder,
        config,
        pack,
        model,
        effort,
        session,
        generations,
        before,
        time_budget=time_budget_summary(folder, exhausted=True),
    )
