"""Thin explicit CLI for model-free preparation and frozen GRPO execution."""

from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path

from proof_eval.evidence.immutable import immutable
from proof_eval.training.config import TrainingRelease


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "prepare-imports", "run"):
        command = commands.add_parser(name)
        command.add_argument("--release", type=Path, required=True)
        command.add_argument("--plan", type=Path, required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--dataset-dir", type=Path, required=True)
    prepare.add_argument("--environments", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--system-prompt", type=Path, required=True)
    prepare.add_argument("--workers", type=int, default=4)
    prepare.add_argument("--episode-seconds", type=int, default=1800)
    prepare.add_argument("--timeout-retries", type=int, choices=(0, 1), default=0)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        from proof_eval.training.prepare import prepare as prepare_references

        result = prepare_references(
            args.dataset_dir,
            args.environments,
            args.output,
            args.system_prompt,
            args.episode_seconds,
            workers=args.workers,
            timeout_retries=args.timeout_retries,
        )
        print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))
        return 0
    release = TrainingRelease(args.release.resolve(), args.plan.resolve())
    plan = release.plan()
    from proof_eval.training import runner

    if args.command == "preflight":
        checked = runner.preflight_only(plan, release.root)
        print(json.dumps(checked))
        return checked["returncode"]
    if args.command == "prepare-imports":
        from proof_eval.training.imports import restore_imports

        runner.verify_sources(plan, release.root)
        runner.configure_harness(plan, release.root)
        result = restore_imports(
            plan,
            Path(plan["root"]),
            Path(plan["home"]),
            release.root / "dataset",
            Path(plan["source_environments"]),
        )
        print(json.dumps(result, indent=2))
        return 0
    try:
        runner.run(release.plan_path, release.root)
    except BaseException as error:
        failure = {
            "at_epoch": time.time(),
            "error": str(error),
            "type": type(error).__name__,
            "traceback": traceback.format_exc(),
            "automatic_model_replay": False,
        }
        for base in (Path(plan["root"]), Path(plan["home"])):
            if base.exists():
                immutable(base / "failed.json", failure)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
