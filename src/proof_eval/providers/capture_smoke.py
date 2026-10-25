"""Validate real local native clients and their complete training capture."""

from __future__ import annotations

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from proof_eval.evidence.io import write_json

from . import lemex_local


def _successful_nonce_command(output: Path, nonce: str) -> dict:
    """Require durable native execution evidence, rather than tool counters."""
    path = output / "events.jsonl"
    if path.is_file():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            item = event.get("item", {})
            if (
                event.get("type") == "item.completed"
                and item.get("type") == "command_execution"
                and item.get("status") == "completed"
                and type(item.get("exit_code")) is int
                and item["exit_code"] == 0
                and item.get("aggregated_output") == nonce
            ):
                return item
    raise RuntimeError("Native smoke lacks a completed successful nonce shell command")


def native_capture_smoke(
    folder: Path, workers: int, source_project: Path, capture_root: Path
) -> dict:
    """Use synthetic shell tasks, never a training/RL problem or task budget."""
    folder.mkdir(parents=True, exist_ok=False)
    identity = lemex_local.cli_identity()
    if identity["context_settings"]["model_context_window"] != 266400:
        raise ValueError("Native smoke requires the fixed collection context")
    stop = threading.Event()
    live_samples = []

    def sample_processes() -> None:
        while not stop.wait(0.1):
            live = {}
            for cmdline in Path("/proc").glob("[0-9]*/cmdline"):
                try:
                    argv = cmdline.read_bytes().split(b"\0")
                    if not argv or argv[0].decode() != identity["path"]:
                        continue
                    cwd = (cmdline.parent / "cwd").resolve(strict=True)
                    if not cwd.is_relative_to(folder):
                        continue
                    client = cwd.relative_to(folder).parts[0]
                    stat = (
                        (cmdline.parent / "stat").read_text().rsplit(")", 1)[1].split()
                    )
                    live[client] = {
                        "pid": int(cmdline.parent.name),
                        "start_ticks": stat[19],
                    }
                except (OSError, IndexError, UnicodeDecodeError):
                    continue
            live_samples.append({"epoch": time.time(), "clients": live})

    def one(index: int) -> dict:
        started = time.time()
        nonce = "arena-capture-smoke-" + str(index)
        output = folder / f"client-{index}"
        result = lemex_local.generate(
            folder=output,
            capacity_slots=workers,
            messages=[
                {
                    "role": "system",
                    "content": "Validate shell execution and return the requested literal text.",
                },
                {
                    "role": "user",
                    "content": "Use the shell tool once to run printf "
                    + nonce
                    + ". Then answer exactly "
                    + nonce
                    + ". Do not perform other work.",
                },
            ],
            model=lemex_local.MODEL,
            effort="xhigh",
            mode="score_edges",
            session=SimpleNamespace(best_code="", row={"name": nonce}),
            context={"source_projects": {"v4.29.1": str(source_project)}},
            expected_cli=identity,
            instructions="Use the native shell tool once and return the requested literal text.",
            tool_service=lambda session, workspace: nullcontext(),
            timeout=300,
        )
        content = result.get("content", "")
        if (
            result["status"] != "received"
            or not isinstance(content, str)
            or not re.search(r"(?<![\w-])" + re.escape(nonce) + r"(?![\w-])", content)
        ):
            raise RuntimeError(
                "Native synthetic capture smoke did not return its nonce"
            )
        if result.get("completed_turns") != 1 or result.get("tool_items", 0) < 1:
            raise RuntimeError("Native smoke missed its completed turn/tool call")
        command = _successful_nonce_command(output, nonce)
        if not result["process_ownership"]["cleanup"]["complete"]:
            raise RuntimeError("Native smoke left owned descendants")
        attribution = json.loads((output / "capture.json").read_text())
        traces = list(Path(attribution["native_trace_root"]).rglob("trace.jsonl"))
        if not traces or not any(p.stat().st_size for p in traces):
            raise RuntimeError("Native rollout context/reasoning trace was not written")
        route = attribution["base_url"].split("/a/", 1)[1].split("/", 1)[0]
        requests = list((capture_root / "attempts" / route / "requests").glob("*"))
        complete = [
            p
            for p in requests
            if (p / "receipt.json").exists()
            and json.loads((p / "receipt.json").read_text())["status"] == "complete"
        ]
        if not complete or any(
            not (p / "request.body").stat().st_size
            or not (p / "response.body").stat().st_size
            for p in complete
        ):
            raise RuntimeError(
                "Native client lacks attributed raw HTTP context/output capture"
            )
        return {
            "index": index,
            "started_epoch": started,
            "finished_epoch": time.time(),
            "status": "passed",
            "tool_items": result.get("tool_items"),
            "successful_nonce_command_id": command.get("id"),
            "native_trace_files": [str(p) for p in traces],
            "complete_captured_requests": len(complete),
            "attribution": attribution["attribution"],
        }

    sampler = threading.Thread(target=sample_processes, daemon=True)
    sampler.start()
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(one, range(workers)))
    finally:
        stop.set()
        sampler.join(timeout=5)
        write_json(folder / "native-process-samples.json", live_samples)
    overlap = min(r["finished_epoch"] for r in rows) - max(
        r["started_epoch"] for r in rows
    )
    if overlap <= 0:
        raise RuntimeError("The measured native clients did not overlap")
    peak_native = max((len(s["clients"]) for s in live_samples), default=0)
    if peak_native != workers:
        raise RuntimeError(
            f"Expected {workers} live native clients; observed {peak_native}"
        )
    receipt = {
        "status": "passed",
        "workers": workers,
        "overlap_seconds": overlap,
        "context_tokens": 266400,
        "cli": identity,
        "rows": rows,
        "peak_live_native_clients": peak_native,
    }
    write_json(folder / "receipt.json", receipt)
    return receipt
