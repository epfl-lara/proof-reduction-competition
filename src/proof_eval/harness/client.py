"""Standalone workspace client for the host's proof and source tools."""

import argparse
import base64
import hashlib
import json
import os
import secrets
import shlex
import socket
import stat
from pathlib import Path

MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024


def _nonnegative(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return number


def _positive(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def _ranges(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--start-line", "--line-start", dest="line_start", type=_positive
    )
    parser.add_argument("--end-line", "--line-end", dest="line_end", type=_positive)
    parser.add_argument(
        "--start-byte", "--byte-start", dest="byte_start", type=_nonnegative
    )
    parser.add_argument("--end-byte", "--byte-end", dest="byte_end", type=_nonnegative)


def _paging(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--as-of", type=_nonnegative)
    parser.add_argument(
        "--limit", type=_positive, choices=range(1, 21), metavar="1..20"
    )
    parser.add_argument("--max-chars", type=_positive)
    parser.add_argument("--cursor")


def _history_parser(commands: argparse._SubParsersAction) -> None:
    history = commands.add_parser(
        "history", help="Query this theorem's saved proof history"
    )
    actions = history.add_subparsers(dest="action", required=True)
    find = actions.add_parser("find", help="Find exact text and related edits")
    source = find.add_mutually_exclusive_group(required=True)
    source.add_argument("--text")
    source.add_argument("--file")
    source.add_argument("--check", dest="check_id", type=_nonnegative)
    source.add_argument("--hash", dest="fragment_hash")
    _ranges(find)
    _paging(find)
    find.add_argument("--page", choices=("occurrences", "transitions"))
    find.add_argument("--view", choices=("compact", "raw"))
    overview = actions.add_parser(
        "overview",
        help="Browse distinct proofs and outcomes without opening every proof",
    )
    _paging(overview)
    show = actions.add_parser("show", help="Read a bounded saved proof excerpt")
    show.add_argument("check_id", type=_nonnegative)
    _ranges(show)
    _paging(show)
    diff = actions.add_parser("diff", help="Compare two saved full-proof outcomes")
    diff.add_argument("base_check_id", type=_nonnegative)
    diff.add_argument("check_id", type=_nonnegative)
    _paging(diff)
    expand = actions.add_parser("expand", help="Follow an exact fragment hash")
    expand.add_argument("fragment_hash")
    _paging(expand)
    expand.add_argument("--page", choices=("occurrences", "transitions"))
    expand.add_argument("--view", choices=("compact", "raw"))
    errors = actions.add_parser(
        "errors", help="Read saved Lean errors, without another check"
    )
    errors.add_argument("check_id", type=_nonnegative)
    errors.add_argument("--start-byte", dest="byte_start", type=_nonnegative)
    _paging(errors)
    status = actions.add_parser(
        "status", help="Show history counts and committed prefix"
    )
    status.add_argument("--as-of", type=_nonnegative)
    checkout = actions.add_parser(
        "checkout", help="Restore a complete proof in your workspace"
    )
    checkout.add_argument("check_id", type=_nonnegative)
    checkout.add_argument("file", help="Workspace .lean file to replace atomically")
    checkout.add_argument("--as-of", type=_nonnegative)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="op", required=True)
    check = commands.add_parser("check")
    check.add_argument("file")
    base = check.add_mutually_exclusive_group()
    base.add_argument("--base-check", dest="base_check_id", type=_nonnegative)
    base.add_argument("--base-unknown", action="store_true", default=None)
    commands.add_parser("goals").add_argument("file")
    _history_parser(commands)
    profile = commands.add_parser(
        "profile", help="Diagnostic tactic heartbeat hotspots"
    )
    profile.add_argument("file")
    profile.add_argument("--version")
    profile.add_argument("--threshold-raw", type=int, default=10_000)
    profile.add_argument("--limit", type=int, default=20)
    commands.add_parser("status")
    remember = commands.add_parser(
        "remember",
        help="Save an unverified note for same-theorem restarts when enabled",
    )
    remember.add_argument(
        "--kind", choices=("discovery", "rejected", "next"), required=True
    )
    remember.add_argument("--text", required=True)
    commands.add_parser("finish").add_argument("--reason", required=True)
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--version")
    search.add_argument("--limit", type=int, default=30)
    sem = commands.add_parser(
        "semantic_search", help="Semantic concept search in Mathlib and dependencies"
    )
    sem.add_argument("query")
    sem.add_argument("--limit", type=int, default=10)
    sem.add_argument("--package", action="append", dest="packages")
    sem.add_argument("--version")
    web_search = commands.add_parser("web_search", help="Public web discovery")
    web_search.add_argument("query")
    web_search.add_argument("--limit", type=int, default=5)
    web_search.add_argument("--domain", action="append", dest="domains")
    web_open = commands.add_parser("web_open", help="Read a public HTTPS source")
    web_open.add_argument("url")
    web_open.add_argument("--start", type=int, default=1)
    web_open.add_argument("--end", type=int, default=180)
    for op in ("read", "outline"):
        sub = commands.add_parser(op)
        sub.add_argument(
            "path", help="Lean source path, relative to the pinned project"
        )
        sub.add_argument("--version")
        if op == "read":
            sub.add_argument("--start", type=int, default=1)
            sub.add_argument("--end", type=int, default=180)
    return parser


def _request(endpoint: dict, args: dict) -> dict:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        # Individual Lean checks retain the evaluator's existing timeout.
        # Waiting for the host is not an optimization budget.
        client.connect(endpoint["socket"])
        client.sendall(json.dumps(args, ensure_ascii=False).encode() + b"\n")
        with client.makefile("rb") as stream:
            raw = stream.readline(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES or not raw.endswith(b"\n"):
                raise ValueError("Incomplete or oversized tool response")
            result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("Tool response must be a JSON object")
    return result


def _file_path(workspace: Path, filename: str) -> Path:
    path = Path(filename)
    return path if path.is_absolute() else workspace / path


def _file_fragment(path: Path, args: dict) -> str:
    """Read exact UTF-8 text; neither newline nor Unicode normalization is allowed."""
    data = path.read_bytes()
    text = data.decode("utf-8")
    if "line_start" in args or "line_end" in args:
        lines = text.splitlines(keepends=True)
        start, end = args.pop("line_start", 1), args.pop("line_end", len(lines))
        if not 1 <= start <= end <= len(lines):
            raise ValueError("Line range must be within the file (1-based, inclusive)")
        return "".join(lines[start - 1 : end])
    start, end = args.pop("byte_start", 0), args.pop("byte_end", len(data))
    if not 0 <= start <= end <= len(data):
        raise ValueError("Byte range must be within the file (0-based, half-open)")
    return data[start:end].decode("utf-8")


def _checkout_target(workspace: Path, filename: str) -> tuple[int, str]:
    """Hold the destination directory open, never following symlinks outside it."""
    path = _file_path(workspace, filename)
    try:
        relative = path.relative_to(workspace)
    except ValueError as exc:
        raise ValueError(
            "Checkout target must be inside the candidate workspace"
        ) from exc
    if ".." in relative.parts or not relative.parts or relative.suffix != ".lean":
        raise ValueError("Checkout requires a workspace .lean path without '..'")
    directory = os.open(workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts[:-1]:
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
            )
            os.close(directory)
            directory = child
        name = relative.name
        try:
            mode = os.stat(name, dir_fd=directory, follow_symlinks=False).st_mode
        except FileNotFoundError:
            pass
        else:
            if not stat.S_ISREG(mode):
                raise ValueError(
                    "Checkout target must be a regular file, never a symlink"
                )
        return directory, name
    except BaseException:
        os.close(directory)
        raise


def _atomic_replace(directory: int, name: str, data: bytes) -> None:
    temporary = ".proof-history-" + secrets.token_hex(16)
    fd = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=directory,
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass


def _checkout(endpoint: dict, args: dict, workspace: Path) -> dict:
    """Export bounded chunks, verify the whole snapshot, then replace locally."""
    filename = args.pop("file")
    directory, name = _checkout_target(workspace, filename)
    try:
        request = {**args, "action": "snapshot", "byte_start": 0}
        content = bytearray()
        identity = None
        while True:
            result = _request(endpoint, request)
            if result.get("kind") == "tool_error":
                return result
            current = (
                result["snapshot_id"],
                result["content_sha256"],
                result["total_bytes"],
                result["check_id"],
            )
            if identity is None:
                identity = current
            if (
                current != identity
                or type(current[3]) is not int
                or current[3] != args["check_id"]
            ):
                raise ValueError("Snapshot identity changed during checkout")
            total = current[2]
            if type(total) is not int or not 0 <= total <= MAX_SNAPSHOT_BYTES:
                raise ValueError("Snapshot exceeds the client export size limit")
            chunk = base64.b64decode(result["code_base64"], validate=True)
            end = len(content) + len(chunk)
            if (
                result["byte_start"] != len(content)
                or result["byte_end"] != end
                or end > total
            ):
                raise ValueError("Snapshot export returned an inconsistent byte range")
            content.extend(chunk)
            following = result["next_byte_start"]
            if following is None:
                if end != total:
                    raise ValueError("Snapshot export ended before the complete proof")
                break
            if (
                type(following) is not int
                or following != end
                or not chunk
                or end >= total
            ):
                raise ValueError("Snapshot export did not advance to the next chunk")
            request["byte_start"] = following
        exact = bytes(content)
        exact.decode("utf-8")
        if hashlib.sha256(exact).hexdigest() != identity[1]:
            raise ValueError("Snapshot export content hash does not match")
        indexed = result["indexed_through_check"]
        if type(indexed) is not int or indexed < args["check_id"]:
            raise ValueError("Snapshot export has no complete committed history prefix")
        _atomic_replace(directory, name, exact)
        return {
            "kind": "history_checkout",
            "check_id": args["check_id"],
            "base_check_id": args["check_id"],
            "file": filename,
            "snapshot_id": identity[0],
            "content_sha256": identity[1],
            "bytes": len(exact),
            "indexed_through_check": indexed,
            "base_provenance": "model_declared",
            "next_check": f"python tools.py check {shlex.quote(filename)} --base-check {args['check_id']}",
        }
    finally:
        os.close(directory)


def main() -> None:
    parser = _parser()
    args = {k: v for k, v in vars(parser.parse_args()).items() if v is not None}
    workspace = Path(__file__).resolve().parent
    try:
        if any(k in args for k in ("line_start", "line_end")) and any(
            k in args for k in ("byte_start", "byte_end")
        ):
            raise ValueError("Choose either line ranges or byte ranges, not both")
        if args["op"] in ("check", "goals", "profile"):
            path = _file_path(workspace, args.pop("file"))
            args["code"] = path.read_bytes().decode("utf-8")
        if args["op"] == "history" and args["action"] == "find" and "file" in args:
            args["text"] = _file_fragment(_file_path(workspace, args.pop("file")), args)
        endpoint = json.loads((workspace / "tool_service.json").read_text())
        result = (
            _checkout(endpoint, args, workspace)
            if args["op"] == "history" and args["action"] == "checkout"
            else _request(endpoint, args)
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"kind": "tool_error", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False))
    if result.get("kind") == "tool_error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
