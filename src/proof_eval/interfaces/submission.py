"""Prepare, verify, search or clean up an inference-only open-track submission."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from proof_eval.harness.submission import (
    initialize,
    verify_initialization,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("setup", "verify", "run", "search", "cleanup"):
        command = sub.add_parser(action, allow_abbrev=False)
        command.add_argument("--bundle", type=Path, required=True)
        command.add_argument("--work", type=Path, required=True)
        if action in ("setup", "run"):
            command.add_argument("--prepared-reference-bundle", type=Path)
            command.add_argument("--prepared-reference-sha256")
        if action in ("run", "search", "cleanup"):
            command.add_argument("--output", type=Path, required=True)
        if action in ("run", "search"):
            command.add_argument("--dry-run", action="store_true")
        if action == "run":
            command.add_argument(
                "--cleanup",
                action=argparse.BooleanOptionalAction,
                default=None,
                help="CPU cleanup after the model server stops (recipe default: enabled); --no-cleanup exports model proofs only",
            )
    args = parser.parse_args(argv)
    try:
        bundle, work = args.bundle.resolve(), args.work.resolve()
        if args.action == "setup":
            from proof_eval.harness.submission_phases import prepare

            result = prepare(
                bundle,
                work,
                prepared_reference_bundle=args.prepared_reference_bundle,
                prepared_reference_sha256=args.prepared_reference_sha256,
            )
        elif args.action == "verify":
            recipe, cpu = verify_initialization(bundle, work)
            result = {
                "status": "ready",
                "problems": len(recipe["names"]),
                "base": cpu["base"],
            }
        else:
            from proof_eval.harness import submission_phases

            if args.action == "run" and (
                args.prepared_reference_bundle is not None
                or args.prepared_reference_sha256 is not None
            ):
                initialize(
                    bundle,
                    work,
                    prepared_reference_bundle=args.prepared_reference_bundle,
                    prepared_reference_sha256=args.prepared_reference_sha256,
                )
            action = getattr(submission_phases, args.action)
            kwargs = {"preview": args.dry_run} if args.action != "cleanup" else {}
            if args.action == "run":
                kwargs["final_cleanup"] = args.cleanup
            result = action(bundle, work, args.output.resolve(), **kwargs)
        print(json.dumps(result, indent=2))
        return 2 if result.get("status") in {"incomplete", "failed"} else 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(2, f"{type(error).__name__}: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
