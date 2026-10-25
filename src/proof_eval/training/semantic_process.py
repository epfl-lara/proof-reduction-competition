"""Owned, finite semantic queries without inheriting Megatron's Python globals."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

from proof_eval.evidence.immutable import immutable, read, sha


class SemanticProcessError(RuntimeError):
    """A tool infrastructure failure, not an invalid model argument or reward zero."""


def semantic_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for name in (
        "RANK",
        "LOCAL_RANK",
        "WORLD_SIZE",
        "LOCAL_WORLD_SIZE",
        "MASTER_ADDR",
        "MASTER_PORT",
        "GROUP_RANK",
        "ROLE_RANK",
        "TORCHELASTIC_RUN_ID",
    ):
        environment.pop(name, None)
    environment.update(
        CUDA_VISIBLE_DEVICES="",
        PYTHONNOUSERSITE="1",
        HF_HUB_OFFLINE="1",
        TOKENIZERS_PARALLELISM="false",
        OMP_NUM_THREADS="4",
        MKL_NUM_THREADS="4",
    )
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    return environment


def search_isolated(
    config: dict,
    project: Path,
    request: dict,
    version: str,
    evidence: Path,
    *,
    timeout_seconds: int = 90,
) -> dict:
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 180:
        raise ValueError("Semantic process timeout must be within 1..180 seconds")
    folder = evidence / ("semantic-" + uuid.uuid4().hex)
    folder.mkdir(parents=True, exist_ok=False)
    pin = immutable(
        folder / "request.json",
        {
            "config": config,
            "project": str(project),
            "request": request,
            "version": version,
            "timeout_seconds": timeout_seconds,
        },
    )
    command = [sys.executable, "-m", "proof_eval.training.semantic_worker", str(folder)]
    immutable(
        folder / "intent.json",
        {
            "command": command,
            "request_sha256": pin,
            "at_epoch": time.time(),
            "automatic_retry": False,
        },
    )
    try:
        with (
            (folder / "stdout.log").open("xb") as out,
            (folder / "stderr.log").open("xb") as err,
        ):
            result = subprocess.run(
                command,
                env=semantic_environment(),
                stdout=out,
                stderr=err,
                timeout=timeout_seconds + 10,
            )
    except subprocess.TimeoutExpired as error:
        immutable(
            folder / "parent-failed.json",
            {
                "error": str(error),
                "at_epoch": time.time(),
                "child_reaped": True,
                "automatic_retry": False,
            },
        )
        raise SemanticProcessError(
            "Isolated semantic process exceeded its bound; exact evidence: "
            + str(folder)
        ) from error
    immutable(
        folder / "exit.json",
        {
            "returncode": result.returncode,
            "at_epoch": time.time(),
            "automatic_retry": False,
        },
    )
    if result.returncode:
        failed = (
            read(folder / "failed.json") if (folder / "failed.json").is_file() else {}
        )
        if failed.get("type") == "ValueError":
            raise ValueError(failed["error"])
        raise SemanticProcessError(
            "Isolated semantic tool failed: " + str(failed.get("error", folder))
        )
    finished = read(folder / "finished.json")
    if (
        finished["request_sha256"] != pin
        or finished["result_sha256"] != sha(folder / "result.json")
        or finished["source_sha256"]
        != sha(Path(__file__).with_name("semantic_worker.py"))
    ):
        raise SemanticProcessError("Isolated semantic tool result identity changed")
    return read(folder / "result.json")
