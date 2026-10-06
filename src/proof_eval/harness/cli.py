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
from .restarts import RestartPolicy
from .runner import run
from .tree import FrontierPolicy, TreeSearch, dream


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for action in ("run", "prepare", "estimate", "report", "audit", "dream"):
        sub = commands.add_parser(action)
        sub.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
        if action in ("report", "audit", "dream"):
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
            "--base",
            type=Path,
            default=BASE,
            help="Frozen prepared inputs and their config.json",
        )
        sub.add_argument("--dataset", type=Path, default=RunConfig.dataset)
        sub.add_argument("--environments", type=Path, default=RunConfig.environments)
        sub.add_argument("--cache", type=Path, default=RunConfig.cache)
        sub.add_argument("--references", type=Path, default=RunConfig.references)
        sub.add_argument(
            "--restart-sessions",
            type=int,
            metavar="N",
            help="Opt-in: up to N agent sessions per theorem, restarting from the best proof",
        )
        sub.add_argument(
            "--restart-below",
            type=float,
            default=RestartPolicy.below_pct,
            metavar="PCT",
            help="Restart only while the best combined score is below PCT",
        )
        sub.add_argument(
            "--tree-expansions",
            type=int,
            metavar="N",
            help="Opt-in: host-orchestrated tree search with up to N short expansions",
        )
        sub.add_argument(
            "--tree-checks",
            type=int,
            default=TreeSearch.max_checks,
            metavar="K",
            help="Checks allowed in each tree expansion",
        )
        sub.add_argument(
            "--tree-budget",
            type=float,
            default=FrontierPolicy.budget_usd,
            metavar="USD",
            help="Projected per-problem budget for tree expansions",
        )
        sub.add_argument(
            "--final-rewrites",
            action="store_true",
            help="Opt-in: proof-theoretic and tokenizer rewrites after final cleanup",
        )
        if action == "run":
            sub.add_argument(
                "--pilot",
                action="store_true",
                help="Audit one theorem per condition before the remaining batch",
            )
    args = parser.parse_args(argv)
    try:
        output = args.output.resolve()
        if args.command == "audit":
            result = audit(output)
            write_json(output / "audit.json", result)
        elif args.command == "dream":
            result = dream(output)
            write_json(output / "dream.json", result)
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
                    "base",
                    "dataset",
                    "environments",
                    "cache",
                    "references",
                    "pilot",
                )
                if hasattr(args, key)
            }
            sessions = getattr(args, "restart_sessions", None)
            restart = (
                RestartPolicy(sessions=sessions, below_pct=args.restart_below)
                if sessions
                else None
            )
            expansions = getattr(args, "tree_expansions", None)
            tree = (
                TreeSearch(
                    FrontierPolicy(
                        max_expansions=expansions, budget_usd=args.tree_budget
                    ),
                    max_checks=args.tree_checks,
                )
                if expansions
                else None
            )
            result = run(
                RunConfig(
                    output=output,
                    conditions=conditions,
                    names=tuple(getattr(args, "name", None) or ()),
                    action=args.command,
                    restart=restart,
                    final_rewrites=getattr(args, "final_rewrites", False),
                    tree=tree,
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
