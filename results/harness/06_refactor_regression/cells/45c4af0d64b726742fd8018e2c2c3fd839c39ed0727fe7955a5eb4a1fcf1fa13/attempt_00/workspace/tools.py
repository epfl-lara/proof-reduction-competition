"""Standalone workspace client for the host's proof and source tools."""

import argparse
import json
import socket
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="op", required=True)
    for op in ("check", "goals"):
        commands.add_parser(op).add_argument("file")
    commands.add_parser("status")
    commands.add_parser("finish").add_argument("--reason", required=True)
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--version")
    search.add_argument("--limit", type=int, default=30)
    for op in ("read", "outline"):
        sub = commands.add_parser(op)
        sub.add_argument(
            "path", help="Lean source path, relative to the pinned project"
        )
        sub.add_argument("--version")
        if op == "read":
            sub.add_argument("--start", type=int, default=1)
            sub.add_argument("--end", type=int, default=180)
    args = vars(parser.parse_args())
    workspace = Path(__file__).resolve().parent
    if args["op"] in ("check", "goals"):
        path = Path(args.pop("file"))
        if not path.is_absolute():
            path = workspace / path
        args["code"] = path.read_text()
    endpoint = json.loads((workspace / "tool_service.json").read_text())
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        # Individual Lean checks retain the evaluator's existing timeout.
        # Waiting for the host is not an optimization budget.
        client.connect(endpoint["socket"])
        client.sendall(json.dumps(args, ensure_ascii=False).encode() + b"\n")
        with client.makefile("rb") as stream:
            result = json.loads(stream.readline(4 * 1024 * 1024))
    print(json.dumps(result, ensure_ascii=False))
    if result.get("kind") == "tool_error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
