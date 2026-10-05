"""Run model search, estimate costs, or read and audit saved evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from proof_eval.evidence.io import read, write_json

from .audit import audit
from .config import RunConfig
from .configuration import (
    ACTIVE_CONDITIONS,
    BASE,
    DEFAULT_MODE,
    DEFAULT_OUTPUT,
    RUN_MODES,
)
from .reporting import report
from .runner import run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for action in ("run", "prepare", "estimate", "report", "audit"):
        sub = commands.add_parser(action)
        sub.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
        if action in ("report", "audit"):
            continue
        sub.add_argument("--mode", choices=RUN_MODES, default=DEFAULT_MODE)
        sub.add_argument(
            "--condition",
            action="append",
            metavar="MODEL:EFFORT",
            help="Repeat for each condition; defaults to Sol 6.1/max and Astra/max",
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
        elif args.command == "report":
            result = report(output, read(output / "config.json"))
        else:
            conditions = (
                tuple(tuple(c.split(":")) for c in args.condition)
                if args.condition
                else tuple(ACTIVE_CONDITIONS)
            )
            fields = {
                key: getattr(args, key)
                for key in (
                    "mode",
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
            result = run(
                RunConfig(
                    output=output,
                    conditions=conditions,
                    names=tuple(getattr(args, "name", None) or ()),
                    action=args.command,
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
