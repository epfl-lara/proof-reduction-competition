"""JSON command-line interface for agents and batch jobs."""

import argparse
import json
import sys
from pathlib import Path

from proof_eval.verification.api import EvaluationNotReady, Evaluator


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="data/benchmark_data_warmup.jsonl")
    parser.add_argument("--heartbeats", default=None)
    parser.add_argument("--environments", default="environments.local.json")
    parser.add_argument("--cache", default=".proof-eval")
    from proof_eval.defaults import VERIFICATION_TIMEOUT_SECONDS

    parser.add_argument("--timeout", type=float, default=VERIFICATION_TIMEOUT_SECONDS)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("environments", help="List required pinned projects")
    for command in ("reference", "prepare", "evaluate", "reward"):
        sub = commands.add_parser(command)
        sub.add_argument("name", help="Exact benchmark theorem ID")
        sub.add_argument(
            "--versions",
            default="all",
            help="all, primary, or comma-separated version labels",
        )
        if command == "prepare":
            sub.add_argument(
                "--refresh",
                action="store_true",
                help="Explicitly replace the cached local reference",
            )
        if command in ("evaluate", "reward"):
            sub.add_argument(
                "--code-file", default="-", help="Lean source file, or - for stdin"
            )
            sub.add_argument(
                "--body",
                action="store_true",
                help="Input contains only the replacement proof body",
            )
        if command == "reward":
            sub.add_argument(
                "--metric",
                choices=("combined", "length", "heartbeat", "compatibility"),
                default="combined",
            )
            sub.add_argument("--invalid-reward", type=float, default=0.0)
    profiling = commands.add_parser(
        "profile", help="Diagnostic tactic heartbeat hotspots"
    )
    profiling.add_argument("name", help="Exact benchmark theorem ID")
    profiling.add_argument(
        "--code-file", default="-", help="Lean declaration, or - for stdin"
    )
    profiling.add_argument(
        "--version", help="One required version; defaults to primary"
    )
    profiling.add_argument("--threshold-raw", type=int, default=10_000)
    profiling.add_argument("--limit", type=int, default=20)
    profiling.add_argument(
        "--output", help="Save the complete diagnostic trace as JSON"
    )
    server = commands.add_parser("serve", help="Start the localhost JSON HTTP API")
    server.add_argument("--port", type=int, default=8765)
    server.add_argument("--workers", type=int, default=2)
    args = parser.parse_args(argv)
    try:
        evaluator = Evaluator(
            args.dataset,
            args.environments,
            args.cache,
            heartbeats_path=args.heartbeats,
            timeout=args.timeout,
        )
        if args.command == "serve":
            from proof_eval.interfaces.http import serve

            serve(evaluator, port=args.port, workers=args.workers)
            return 0
        if args.command == "environments":
            result = evaluator.environments()
        elif args.command == "profile":
            from proof_eval.evidence.io import write_json
            from proof_eval.verification.profile_trace import profile_view
            from proof_eval.verification.profiling import ProfileConfig, profile

            code = (
                sys.stdin.read()
                if args.code_file == "-"
                else Path(args.code_file).read_text()
            )
            diagnostic = profile(
                evaluator,
                args.name,
                code,
                config=ProfileConfig(args.version, args.threshold_raw, args.limit),
            )
            if args.output:
                write_json(args.output, diagnostic)
            result = profile_view(diagnostic)
        else:
            versions = (
                args.versions.split(",") if "," in args.versions else args.versions
            )
            if args.command == "reference":
                result = evaluator.get_reference(args.name, versions=versions)
            elif args.command == "prepare":
                result = evaluator.prepare_reference(
                    args.name, versions=versions, refresh=args.refresh
                )
            else:
                code = (
                    sys.stdin.read()
                    if args.code_file == "-"
                    else Path(args.code_file).read_text()
                )
                kwargs = {
                    "versions": versions,
                    "input_kind": "body" if args.body else "declaration",
                }
                if args.command == "evaluate":
                    result = evaluator.evaluate(args.name, code, **kwargs)
                else:
                    result = {
                        "reward": evaluator.reward(
                            args.name,
                            code,
                            metric=args.metric,
                            invalid_reward=args.invalid_reward,
                            **kwargs,
                        )
                    }
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ValueError, KeyError, OSError, EvaluationNotReady) as exc:
        print(
            json.dumps({"error": str(exc), "type": type(exc).__name__}), file=sys.stderr
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
