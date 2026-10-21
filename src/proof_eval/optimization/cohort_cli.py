"""Run or audit a cohort-wide one-sweep deterministic phase."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from proof_eval.evidence.io import write_json
from proof_eval.harness.config import RunConfig

from .cohort import audit_cleanup, report_cleanup, run_cleanup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    for key in ("base", "dataset", "environments", "cache", "references"):
        parser.add_argument("--" + key, type=Path, default=getattr(RunConfig, key))
    parser.add_argument("--starting-proofs", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--condition", help="MODEL:EFFORT lineage for model-produced input proofs"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--audit", action="store_true")
    mode.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.audit:
            result = audit_cleanup(args.output)
            write_json(args.output / "audit.json", result)
        elif args.report:
            result = report_cleanup(args.output)
        else:
            condition = tuple(args.condition.split(":")) if args.condition else None
            if condition is not None and len(condition) != 2:
                raise ValueError("Condition must be MODEL:EFFORT")
            result = run_cleanup(
                output=args.output,
                workers=args.workers,
                starting_proofs=args.starting_proofs,
                condition=condition,
                prepare_only=args.prepare,
                **{
                    k: getattr(args, k)
                    for k in ("base", "dataset", "environments", "cache", "references")
                },
            )
        print(json.dumps(result))
        return 0 if result["status"] in {"complete", "prepared", "passed"} else 2
    except (ValueError, OSError, RuntimeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
