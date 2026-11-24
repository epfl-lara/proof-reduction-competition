"""Scope, prompt pointers and durable query evidence for exact proof history."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

from proof_eval.evidence.io import fingerprint, now, write_jsonl

if TYPE_CHECKING:
    from proof_eval.evidence.proof_history import ProofHistory

VERSION = 2
SUPPORTED_VERSIONS = (1, 2)


def scope_for(config: dict, pack: dict, model: str, effort: str) -> dict:
    """Bind retrieval to a frozen run, prepared context and model condition."""
    if (
        type(config.get("proof_history_version")) is not int
        or config["proof_history_version"] not in SUPPORTED_VERSIONS
    ):
        raise ValueError("Unsupported proof history version")
    return {
        "version": config["proof_history_version"],
        "run_id": config["proof_history_run_id"],
        "name": pack["name"],
        "model": model,
        "effort": effort,
        "mode": config["mode"],
        "input_sha256": config["input_sha256"][pack["name"]],
        "dataset_sha256": config["dataset_sha256"],
        "environment_config_sha256": config["environment_config_sha256"],
        "references_sha256": config["references_sha256"],
        "source_context_sha256": fingerprint(pack.get("source_context")),
        "reference_context_sha256": fingerprint(
            {
                version: {
                    "reference": record.get("reference"),
                    "environment_fingerprint": record.get("environment_fingerprint"),
                }
                for version, record in pack["incumbent"]["per_version"].items()
            }
        ),
        "runtime_sha256": fingerprint(config["code_sha256"]),
    }


def best_check_id(checks: list[dict], seed_code: str, best_code: str) -> int:
    """Identify the exact selected snapshot, preserving duplicate event identities."""
    for check in reversed(checks):
        if check["accepted"] and check["code"] == best_code:
            return check["number"]
    if best_code == seed_code:
        return 0
    raise ValueError("Best proof has no exact history snapshot")


def context_for(
    scope: dict, checks: list[dict], seed_code: str, best_code: str
) -> dict:
    """A compact restart pointer, reconstructed solely from the admitted prefix."""
    return {
        "version": scope.get("version", 1),
        "scope_sha256": fingerprint(scope),
        "history_available_checks": len(checks),
        "history_best_check_id": best_check_id(checks, seed_code, best_code),
        "seed_check_id": 0,
        "checks_sha256": fingerprint(checks),
        "policy": (
            "Exact proof history persists across fresh contexts in this same budget. "
            "Use python tools.py history find --text 'exact code' to retrieve changes "
            "from either side, including experiments on currently unchanged code. "
            "Each check must declare --base-check ID or --base-unknown. Scores belong "
            "to full proofs; combining historical fragments needs a fresh check."
        ),
    }


def add_context(messages: list[dict], context: dict) -> None:
    """Append only the configured pointer to the ordinary structured task payload."""
    prefix = "Optimize this declaration using the supplied tools.\n"
    if not messages[1]["content"].startswith(prefix):
        raise ValueError("Proof history requires the standard task payload")
    payload = json.loads(messages[1]["content"][len(prefix) :])
    payload["proof_history"] = context
    messages[1]["content"] = prefix + json.dumps(payload, ensure_ascii=False, indent=2)


def read_queries(folder: Path) -> list[dict]:
    path = folder / "history_queries.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def query_history(
    history: ProofHistory,
    scope: dict,
    folder: Path,
    queries: list[dict],
    checks: list[dict],
    request: dict,
    tool_request: dict | None,
) -> dict:
    """Commit the exact prefix and result before returning a successful lookup.

    The caller holds the session lock. An index failure leaves committed proof
    evidence intact and prevents an incomplete history response from escaping.
    """
    history.sync(checks)
    history.restore_queries(queries)
    number = len(queries) + 1
    response = history.query(request, query_id=number)
    record = {
        "number": number,
        "at": now(),
        "scope": scope,
        "check_count": len(checks),
        "checks_sha256": fingerprint(checks),
        "request": deepcopy(request),
        "response": deepcopy(response),
        "tool_request": deepcopy(tool_request),
    }
    try:
        write_jsonl(folder / "history_queries.jsonl", queries + [record])
    except Exception:
        # Query-created substring IDs must not outlive a failed journal commit:
        # subsequent hash-only lookups would otherwise be impossible to replay.
        history.invalidate()
        raise
    queries.append(record)
    return response
