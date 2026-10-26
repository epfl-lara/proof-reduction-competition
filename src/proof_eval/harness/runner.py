"""Resumable per-theorem and batch model search; orchestration only."""

from __future__ import annotations

import fcntl
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from proof_eval import Evaluator
from proof_eval.evidence.io import digest, now, read, write_json

from .budget import run_cell
from .config import RunConfig
from .configuration import (
    guard,
    load_inputs,
    preflight_costs,
    prepare,
)
from .reporting import report


def run(args: RunConfig) -> dict:
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == "report":
            return report(output, read(output / "config.json"))
        conditions = list(args.conditions)
        if args.action == "estimate":
            result = preflight_costs(conditions, args.provider)
            write_json(output / "cost_estimate.json", result)
            return result
        packs = load_inputs(Path(args.base).resolve())
        config = prepare(
            output,
            args.mode,
            packs,
            conditions=conditions,
            provider=args.provider,
            problem_timeout_seconds=args.problem_timeout_seconds,
            budget_tracking=args.budget_tracking,
            budget_usd_per_problem=args.budget_usd_per_problem,
            usage_policy=args.usage_policy,
            restart_history=args.restart_history,
            proof_theory_cleanup=args.proof_theory_cleanup,
            initial_pipeline=True,
            original_measurement_policy=args.original_measurement_policy,
            initial_methods=args.deterministic_methods if args.deterministic else (),
            initial_seconds=args.deterministic_seconds,
            max_budget_restarts=args.max_budget_restarts,
            max_transport_restarts=args.max_transport_restarts,
            incumbents_from=args.incumbents_from,
            carry_budgets_from=args.carry_budgets_from,
            deterministic_checkpoint=args.deterministic_checkpoint,
            starting_proofs=args.starting_proofs,
            semantic_search=args.semantic_search,
            web_search=args.web_search,
            base_directory=Path(args.base).resolve(),
            paths={
                "dataset_path": str(Path(args.dataset).resolve()),
                "environments_path": str(Path(args.environments).resolve()),
                "references_path": str(Path(args.references).resolve()),
                "references_sha256": digest(args.references),
                "verification_timeout_seconds": args.verification_timeout_seconds,
                **(
                    {"local_capacity_slots": args.workers}
                    if args.provider == "lemex-local"
                    else {}
                ),
            },
        )
        evaluator = Evaluator(
            args.dataset,
            args.environments,
            args.cache,
            timeout=args.verification_timeout_seconds,
        )
        for pack in packs.values():
            guard(config, pack, evaluator)
        if args.action == "prepare":
            return report(output, config)
        if args.names and not set(args.names) <= set(config["names"]):
            raise ValueError("Unknown theorem name")
        selected = [n for n in config["names"] if not args.names or n in args.names]
        work = [
            (name, model, effort)
            for name in selected
            for model, effort in config["conditions"]
        ]
        ended = threading.Event()
        failures = []

        def reporter():
            while not ended.wait(30):
                try:
                    report(output, config)
                except Exception as error:
                    write_json(
                        output / "reporter_error.json",
                        {"at": now(), "error": str(error)},
                    )

        thread = threading.Thread(target=reporter, daemon=True)
        thread.start()
        write_json(
            output / "run.json",
            {
                "status": "running",
                "started_at": now(),
                "workers": args.workers,
                "selected_names": selected,
                "mode": args.mode,
            },
        )
        try:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = {
                    pool.submit(
                        run_cell, output, config, packs[name], model, effort, evaluator
                    ): (name, model, effort)
                    for name, model, effort in work
                }
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        print(
                            json.dumps(
                                {
                                    k: result[k]
                                    for k in (
                                        "name",
                                        "model",
                                        "effort",
                                        "status",
                                        "gain_over_historical_pp",
                                        "checks",
                                    )
                                }
                            ),
                            flush=True,
                        )
                        if result["status"] != "complete":
                            stop = result.get("stop") or {}
                            failures.append(
                                {
                                    "cell": futures[future],
                                    "error": stop.get("reason")
                                    or result["generation_status"],
                                    "generation_status": result["generation_status"],
                                    "stop_kind": stop.get("kind"),
                                }
                            )
                    except Exception as error:
                        failures.append(
                            {
                                "cell": futures[future],
                                "error": f"{type(error).__name__}: {error}",
                            }
                        )
                    report(output, config)
        except Exception as error:
            failures.append({"error": f"{type(error).__name__}: {error}"})
            raise
        finally:
            ended.set()
            thread.join()
            write_json(
                output / "run.json",
                {
                    "status": "failed" if failures else "finished",
                    "at": now(),
                    "failures": failures,
                },
            )
        result = report(output, config)
        if failures:
            raise RuntimeError(
                "Some cells are incomplete; inspect run.json, saved requests are not resampled"
            )
        return result
