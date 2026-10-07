"""Run model search, estimate costs, or read and audit saved evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from proof_eval.evidence.io import read, write_json
from proof_eval.providers.registry import DEFAULT_CONDITIONS

from .audit import audit
from .config import RunConfig
from .configuration import (
    BASE,
    DEFAULT_OUTPUT,
)
from .reporting import report
from .runner import run
from .semantic import discover


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    replay_command = commands.add_parser("replay", help="Replay saved evidence offline")
    replay_command.add_argument("--run", type=Path, action="append", required=True)
    replay_command.add_argument("--protocol", type=Path, required=True)
    replay_command.add_argument("--output", type=Path, required=True)
    replay_command.add_argument("--pilot", action="store_true")
    replay_command.add_argument("--descriptive-only", action="store_true")
    for action in ("run", "prepare", "estimate", "report", "audit"):
        sub = commands.add_parser(action)
        sub.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
        if action in ("report", "audit"):
            continue
        sub.add_argument(
            "--provider", choices=tuple(DEFAULT_CONDITIONS), default="codex"
        )
        sub.add_argument(
            "--condition",
            action="append",
            metavar="MODEL:EFFORT",
            help="Repeat MODEL:EFFORT; defaults to the selected provider's active conditions",
        )
        if action == "estimate":
            continue
        sub.add_argument("--name", action="append")
        sub.add_argument("--workers", type=int, default=5)
        sub.add_argument(
            "--semantic-search",
            action="store_true",
            help="Enable offline LeanExplore using already cached, frozen data and CPU embeddings",
        )
        sub.add_argument(
            "--web-search",
            action="store_true",
            help="Enable host-owned public web search and documentation retrieval with saved evidence",
        )
        sub.add_argument(
            "--problem-timeout-seconds",
            type=float,
            default=RunConfig.problem_timeout_seconds,
            help="Whole-problem wall time, including Lean tools and cleanup (default: 3420 seconds)",
        )
        tracking = sub.add_mutually_exclusive_group()
        tracking.add_argument(
            "--budget-tracking",
            choices=("cost", "time"),
            default=None,
            help="Force-stop tracking mode: 'cost' or 'time'",
        )
        tracking.add_argument(
            "--track-cost",
            dest="budget_tracking",
            action="store_const",
            const="cost",
            help="Alias for --budget-tracking cost",
        )
        tracking.add_argument(
            "--track-time",
            dest="budget_tracking",
            action="store_const",
            const="time",
            help="Alias for --budget-tracking time",
        )
        sub.add_argument(
            "--budget-usd",
            dest="budget_usd_per_problem",
            type=float,
            default=RunConfig.budget_usd_per_problem,
            help="Per-problem cost budget cap in USD (default: 3.0)",
        )
        sub.add_argument(
            "--max-budget-restarts",
            type=int,
            default=RunConfig.max_budget_restarts,
            help="Restart safety limit when tracking is enabled; 20 permits 21 total attempts",
        )
        sub.add_argument(
            "--base",
            type=Path,
            default=BASE,
            help="Frozen prepared inputs and their config.json",
        )
        sub.add_argument("--dataset", type=Path, default=RunConfig.dataset)
        sub.add_argument(
            "--max-transport-restarts",
            type=int,
            default=RunConfig.max_transport_restarts,
            help="Fresh sessions after terminal transient failures, sharing the original deadline (default: 2)",
        )
        sub.add_argument(
            "--incumbents-from",
            type=Path,
            help="Seed from saved, verified results for the same model condition; use a new output",
        )
        sub.add_argument(
            "--carry-budgets-from",
            type=Path,
            help="Carry known prior spend, original deadlines and same-condition proofs into a new runtime/output",
        )
        sub.add_argument("--environments", type=Path, default=RunConfig.environments)
        sub.add_argument("--cache", type=Path, default=RunConfig.cache)
        sub.add_argument("--references", type=Path, default=RunConfig.references)
        if action == "run":
            sub.add_argument(
                "--pilot",
                action="store_true",
                help="Audit one theorem per condition before the remaining batch",
            )
    args = parser.parse_args(argv)
    try:
        if args.command == "replay":
            from .replay_reporting import run_replay

            result = run_replay(
                args.run,
                args.protocol,
                args.output,
                pilot=args.pilot,
                descriptive_only=args.descriptive_only,
            )
            print(
                json.dumps(
                    {"status": result["status"], "gate": result["gate"]["verdict"]}
                )
            )
            return 0
        output = args.output.resolve()
        if args.command == "audit":
            saved_report = (
                read(output / "report.json")
                if (output / "report.json").exists()
                else {}
            )
            if "protocol_sha256" in saved_report:
                from .replay_reporting import audit_replay

                result = audit_replay(output)
            else:
                result = audit(output)
            write_json(output / "audit.json", result)
        elif args.command == "report":
            result = report(output, read(output / "config.json"))
        else:
            conditions = (
                tuple(tuple(c.split(":")) for c in args.condition)
                if args.condition
                else DEFAULT_CONDITIONS[args.provider]
            )
            fields = {
                key: getattr(args, key)
                for key in (
                    "provider",
                    "workers",
                    "problem_timeout_seconds",
                    "budget_tracking",
                    "budget_usd_per_problem",
                    "max_budget_restarts",
                    "max_transport_restarts",
                    "incumbents_from",
                    "carry_budgets_from",
                    "base",
                    "dataset",
                    "environments",
                    "cache",
                    "references",
                    "pilot",
                )
                if hasattr(args, key)
            }
            result = run(
                RunConfig(
                    output=output,
                    conditions=conditions,
                    names=tuple(getattr(args, "name", None) or ()),
                    action=args.command,
                    semantic_search=(
                        discover() if getattr(args, "semantic_search", False) else None
                    ),
                    web_search=getattr(args, "web_search", False),
                    **fields,
                )
            )
        if args.command == "estimate":
            brief = [
                {
                    "target": s["configuration"],
                    "source": s["source_configuration"],
                    **s["summary"],
                }
                for s in result["scenarios"]
            ]
        else:
            brief = {
                key: result[key]
                for key in (
                    "status",
                    "terminal_cells",
                    "planned_cells",
                    "completed_cells",
                )
                if key in result
            }
        print(json.dumps(brief))
        return 0
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
