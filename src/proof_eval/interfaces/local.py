"""Prepare or run the explicit native-local recipe through the maintained harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from proof_eval.providers import local_profile
from proof_eval.providers.capture_proxy import CaptureProxy
from proof_eval.providers.vllm_server import ManagedServer, command


def main(argv=None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    boundary = arguments.index("--") if "--" in arguments else len(arguments)
    forwarded = arguments[boundary + 1 :]
    arguments = arguments[:boundary]
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("action", choices=("prepare", "serve", "run"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--model", default=local_profile.MODEL)
    parser.add_argument("--revision")
    parser.add_argument("--model-cache", type=Path)
    parser.add_argument("--workers", type=int, default=local_profile.LOCAL_QWEN_WORKERS)
    parser.add_argument(
        "--seconds", type=int, default=local_profile.QWEN_TIMEOUT_SECONDS
    )
    parser.add_argument(
        "--context", type=int, default=local_profile.QWEN_CONTEXT_TOKENS
    )
    parser.add_argument(
        "--compaction", type=int, default=local_profile.QWEN_COMPACTION_TOKENS
    )
    parser.add_argument(
        "--verification-timeout-seconds",
        type=float,
        default=local_profile.VERIFICATION_TIMEOUT_SECONDS,
    )
    parser.add_argument("--port", type=int, default=8128)
    parser.add_argument("--vllm-binary", default="vllm")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--plugin", type=Path)
    parser.add_argument("--capture-port", type=int, default=18128)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(arguments)
    if args.action == "prepare":
        value = local_profile.prepare(
            args.profile,
            model=args.model,
            revision=args.revision,
            model_cache=args.model_cache,
            workers=args.workers,
            seconds=args.seconds,
            context=args.context,
            compaction=args.compaction,
            verification_timeout_seconds=args.verification_timeout_seconds,
            port=args.port,
            binary=args.vllm_binary,
        )
        print(json.dumps(value, indent=2))
        return 0
    setup_options = {
        "--model",
        "--revision",
        "--model-cache",
        "--workers",
        "--seconds",
        "--context",
        "--compaction",
        "--verification-timeout-seconds",
        "--port",
        "--vllm-binary",
    }
    if any(a.split("=", 1)[0] in setup_options for a in arguments):
        parser.error(
            "Serving settings are frozen; prepare a new profile to change them"
        )
    profile = args.profile.resolve()
    value, server = local_profile.load(profile)
    if args.dry_run:
        print(json.dumps({"argv": command(server), "profile": value}, indent=2))
        return 0
    if args.output is None or args.plugin is None:
        parser.error("serve/run requires --output and --plugin; preview with --dry-run")
    output = args.output.resolve()
    plugin = args.plugin.resolve(strict=True)
    reserved = {
        "--provider",
        "--condition",
        "--output",
        "--model-workers",
        "--workers",
        "--problem-timeout-seconds",
        "--verification-timeout-seconds",
        "--restart-history",
        "--deterministic",
        "--budget-tracking",
        "--track-cost",
        "--track-time",
    }
    if any(
        a.startswith("--") and any(r.startswith(a.split("=", 1)[0]) for r in reserved)
        for a in forwarded
    ):
        parser.error(
            "Model, output, workers, deadline, cleanup and history come from the profile"
        )
    with ManagedServer(server, output, plugin, output / ".server.lock"):
        if args.action == "serve":
            while True:
                time.sleep(1)
        from proof_eval.harness.cli import main as harness_main

        with CaptureProxy(
            output / "capture", upstream=server.endpoint, port=args.capture_port
        ) as proxy:
            values = {
                **proxy.environment,
                "PROOF_LEMEX_LOCAL_HOME": str(profile),
                "PROOF_LEMEX_LOCAL_CAPACITY_NAMESPACE": "arena-"
                + hashlib.sha256(str(output).encode()).hexdigest()[:16],
            }
            previous = {k: os.environ.get(k) for k in values}
            os.environ.update(values)
            try:
                return harness_main(
                    [
                        "run",
                        "--provider",
                        "lemex-local",
                        "--condition",
                        value["model"] + ":" + value["effort"],
                        "--output",
                        str(output),
                        "--model-workers",
                        str(value["workers"]),
                        "--problem-timeout-seconds",
                        str(value["seconds"]),
                        "--verification-timeout-seconds",
                        str(
                            value.get(
                                "verification_timeout_seconds",
                                local_profile.VERIFICATION_TIMEOUT_SECONDS,
                            )
                        ),
                        "--budget-tracking",
                        "time",
                        "--no-deterministic",
                        *forwarded,
                    ]
                )
            finally:
                for key, old in previous.items():
                    if old is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = old


if __name__ == "__main__":
    raise SystemExit(main())
