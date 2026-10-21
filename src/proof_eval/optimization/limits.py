"""Identify bounded discovery timeouts from saved terminal evidence, never errors."""

from __future__ import annotations

import json
from pathlib import Path

from proof_eval.evidence.io import digest, read


def discovery_limit_evidence(folder: Path) -> list[dict]:
    """Return evidence only when all unfinished methods have recorded timeouts."""
    job_path = folder / "job/result.json"
    if not job_path.exists():
        return []
    job = read(job_path)
    if job.get("status") != "incomplete_discovery" or not job.get("incomplete_methods"):
        return []
    evidence = []
    for stage_path in sorted((folder / "job/stages").glob("*/result.json")):
        stage = read(stage_path)
        if stage["method"] not in job["incomplete_methods"]:
            continue
        trials_path = stage_path.parent / "trials.jsonl"
        events = [json.loads(line) for line in trials_path.read_text().splitlines()]
        if stage.get("stop_reason") != "discovery_unavailable" or not events:
            return []
        last = events[-1]
        discovery = last.get("discovery", {})
        timed_out = any(
            d.get("kind") == "discovery_process" and d.get("timed_out") is True
            for d in discovery.get("diagnostics", [])
        )
        if (
            last.get("kind") != "proposal_set"
            or discovery.get("status") != "discovery_timeout"
            or not timed_out
        ):
            return []
        evidence.append(
            {
                "method": stage["method"],
                "reason": "discovery_timeout",
                "stage": str(stage_path.relative_to(folder)),
                "stage_sha256": digest(stage_path),
                "trials": str(trials_path.relative_to(folder)),
                "trials_sha256": digest(trials_path),
            }
        )
    if {e["method"] for e in evidence} != set(job["incomplete_methods"]):
        return []
    return evidence


def audit_discovery_limit(folder: Path, phase: dict) -> None:
    """A controlled discovery stop requires terminal timeout evidence for every gap."""
    if not phase["spec"].get("discovery_limit_policy"):
        return
    expected = discovery_limit_evidence(folder)
    if phase.get("discovery_limit_evidence") != expected:
        raise ValueError("Discovery timeout evidence changed")
    if (phase["status"] == "discovery_limit" and not expected) or (
        expected
        and phase["status"] not in ("discovery_limit", "time_limit", "problem_deadline")
    ):
        raise ValueError("Discovery timeout was confused with an unbounded failure")
