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
from .pipeline import PipelineConfig, run_pipeline
from .pipeline_reporting import audit_pipeline, report_pipeline
from .reporting import report
from .runner import run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    replay_command = commands.add_parser(
        "replay", help="Replay saved evidence offline", allow_abbrev=False
    )
    replay_command.add_argument("--run", type=Path, action="append", required=True)
    replay_command.add_argument("--protocol", type=Path, required=True)
    replay_command.add_argument("--output", type=Path, required=True)
    replay_command.add_argument("--pilot", action="store_true")
    replay_command.add_argument("--descriptive-only", action="store_true")
    for action in ("run", "prepare", "estimate", "report", "audit"):
        sub = commands.add_parser(action, allow_abbrev=False)
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
        sub.add_argument(
            "--starting-proofs",
            type=Path,
            help="Explicit starting state.json, cleanup output directory or name/proof JSONL; default: original dataset proofs",
        )
        sub.add_argument(
            "--deterministic-checkpoint",
            type=Path,
            help="Explicit audited exploration condition for untimed closed-track starts; requires --no-deterministic",
        )
        sub.add_argument(
            "--deterministic",
            action=argparse.BooleanOptionalAction,
            default=None,
            help="Cohort cleanup before/after search; default off for Qwen and on for other models; an explicit flag overrides the model default",
        )
        sub.add_argument(
            "--cleanup-before",
            action=argparse.BooleanOptionalAction,
            default=None,
            help="Run cleanup before model calls (default off for Qwen, on for other models)",
        )
        sub.add_argument(
            "--cleanup-after",
            action=argparse.BooleanOptionalAction,
            default=None,
            help="Run cleanup after the model batch (default off for Qwen, on for other models)",
        )
        sub.add_argument("--cleanup-workers", type=int, default=8)
        sub.add_argument("--before-workers", type=int)
        sub.add_argument("--after-workers", type=int)
        sub.add_argument(
            "--proof-theory-cleanup",
            action="store_true",
            help="Compatibility flag: the one-sweep portfolio already includes PR #1 methods",
        )
        sub.add_argument(
            "--restart-history",
            action=argparse.BooleanOptionalAction,
            default=RunConfig.restart_history,
            help="Bounded same-theorem restart history (default: disabled; --restart-history enables it)",
        )
        sub.add_argument(
            "--workers",
            "--model-workers",
            type=int,
            default=None,
            help="Model workers (default: 10 for local Qwen, 5 for Sol/gateway Qwen); cleanup has its own workers",
        )
        sub.add_argument(
            "--semantic-search",
            action=argparse.BooleanOptionalAction,
            default=RunConfig.semantic_search,
            help="Offline LeanExplore with cached, frozen CPU embeddings (default: enabled; --no-semantic-search disables it)",
        )
        sub.add_argument(
            "--web-search",
            action=argparse.BooleanOptionalAction,
            default=RunConfig.web_search,
            help="Host-owned public web discovery with saved evidence (default: enabled; --no-web-search disables it)",
        )
        sub.add_argument(
            "--problem-timeout-seconds",
            type=float,
            default=RunConfig.problem_timeout_seconds,
            help="Model-phase wall time per theorem; default: Qwen 28800 seconds, other open models 3420, closed models no wall deadline",
        )
        sub.add_argument(
            "--original-measurement-policy",
            choices=("fresh", "prepared"),
            default=None,
            help="Original admission: reuse verified prepared references for local Qwen; fresh measurement for other providers",
        )
        sub.add_argument(
            "--verification-timeout-seconds",
            type=float,
            default=RunConfig.verification_timeout_seconds,
            help="Per Lean check wall deadline (default: 600 seconds); included in the original model-phase clock",
        )
        tracking = sub.add_mutually_exclusive_group()
        tracking.add_argument(
            "--budget-tracking",
            choices=("auto", "cost", "time"),
            default="auto",
            help="Budget policy (default: auto; open models use time, closed models use cost)",
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
            "--usage-policy",
            choices=("strict", "best_effort"),
            default=None,
            help="Incomplete usage: best_effort estimates and retries for new Codex cost runs; strict stops on missing counters",
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
            help="Optimization restart safety limit under the original problem budget; default: Qwen 10000, other models 20",
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
            saved_config = read(output / "config.json")
            if saved_config.get("cohort_pipeline_version"):
                result = audit_pipeline(output)
            elif "protocol_sha256" in saved_report:
                from .replay_reporting import audit_replay

                result = audit_replay(output)
            else:
                result = audit(output)
            write_json(output / "audit.json", result)
        elif args.command == "report":
            saved_config = read(output / "config.json")
            result = (
                report_pipeline(output)
                if saved_config.get("cohort_pipeline_version")
                else report(output, saved_config)
            )
            write_json(output / "report.json", result)
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
                    "verification_timeout_seconds",
                    "original_measurement_policy",
                    "budget_tracking",
                    "budget_usd_per_problem",
                    "usage_policy",
                    "restart_history",
                    "proof_theory_cleanup",
                    "starting_proofs",
                    "deterministic_checkpoint",
                    "max_budget_restarts",
                    "max_transport_restarts",
                    "incumbents_from",
                    "carry_budgets_from",
                    "base",
                    "dataset",
                    "environments",
                    "cache",
                    "references",
                )
                if hasattr(args, key)
            }
            model_args = RunConfig(
                output=output,
                conditions=conditions,
                names=tuple(getattr(args, "name", None) or ()),
                action=args.command,
                semantic_search=getattr(
                    args, "semantic_search", RunConfig.semantic_search
                ),
                web_search=getattr(args, "web_search", RunConfig.web_search),
                **fields,
            )
            if (
                args.command == "estimate"
                or model_args.deterministic_checkpoint is not None
            ):
                if (
                    model_args.deterministic_checkpoint is not None
                    and args.deterministic is not False
                ):
                    raise ValueError(
                        "Legacy deterministic checkpoints require --no-deterministic; use --starting-proofs for phase workflows"
                    )
                result = run(model_args)
            else:
                result = run_pipeline(
                    PipelineConfig(
                        model=model_args,
                        cleanup_before=(
                            False
                            if args.deterministic is False
                            else (
                                args.cleanup_before
                                if args.cleanup_before is not None
                                else args.deterministic
                            )
                        ),
                        cleanup_after=(
                            False
                            if args.deterministic is False
                            else (
                                args.cleanup_after
                                if args.cleanup_after is not None
                                else args.deterministic
                            )
                        ),
                        cleanup_workers=args.cleanup_workers,
                        before_workers=args.before_workers,
                        after_workers=args.after_workers,
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
        return 2 if result.get("status") in {"incomplete", "partial", "failed"} else 0
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
