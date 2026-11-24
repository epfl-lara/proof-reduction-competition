"""Bounded views of saved verifier diagnostics, without another Lean check."""

from __future__ import annotations

import json
from collections.abc import Sequence


def diagnostic_payload(event: dict, versions: Sequence[str]) -> dict:
    evaluation = event["evaluation"]
    checks = evaluation.get("per_version", {})
    checks = checks if isinstance(checks, dict) else {}
    return {
        "evaluation_status": evaluation.get("status"),
        "evaluation_diagnostics": evaluation.get("diagnostics", []),
        "versions": {
            version: {
                "status": checks.get(version, {}).get("status", "not_recorded"),
                "diagnostics": checks.get(version, {}).get("diagnostics", []),
            }
            for version in versions
            if isinstance(checks.get(version, {}), dict)
        },
    }


def failure_preview(event: dict, versions: Sequence[str]) -> dict | None:
    """One actual diagnostic; incomplete checks never become semantic failures."""
    payload = diagnostic_payload(event, versions)
    failures = [
        (version, value)
        for version, value in payload["versions"].items()
        if value["status"] != "passed"
    ]
    failures.sort(key=lambda item: item[1]["status"] != "failed")
    if not failures and not payload["evaluation_diagnostics"]:
        return None
    version, value = (
        failures[0]
        if failures
        else (
            None,
            {
                "status": payload["evaluation_status"],
                "diagnostics": payload["evaluation_diagnostics"],
            },
        )
    )
    diagnostics = value["diagnostics"] or payload["evaluation_diagnostics"]
    if isinstance(diagnostics, list):
        errors = [
            item
            for item in diagnostics
            if isinstance(item, dict) and item.get("severity") == "error"
        ]
        diagnostic = next(iter(errors or diagnostics), "No diagnostic was recorded")
    else:
        diagnostic = diagnostics
    message = (
        diagnostic.get("data", diagnostic.get("message", diagnostic))
        if isinstance(diagnostic, dict)
        else diagnostic
    )
    if not isinstance(message, str):
        message = json.dumps(message, ensure_ascii=False)
    return {
        "version": version,
        "status": value["status"],
        "message": message[:240],
        "message_truncated": len(message) > 240,
    }
