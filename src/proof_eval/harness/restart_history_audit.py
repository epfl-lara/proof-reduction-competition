"""Verify restart history against same-cell, earlier host evidence."""

from __future__ import annotations

from proof_eval.evidence.audit import _require
from proof_eval.evidence.io import fingerprint

from .restart_history import (
    MAX_EVENTS_PER_ATTEMPT,
    NOTE_KINDS,
    build_history,
    scope_for,
)


def audit_history_attempt(
    config: dict,
    result: dict,
    record: dict,
    payload: dict,
    checks: list[dict],
    number: int,
    previous_event_end: int,
    history_events: list[dict],
) -> int:
    """Reject future evidence, foreign scope, changed notes and invented summaries."""
    history_enabled = config.get("restart_history_version") is not None
    if history_enabled:
        event_start, event_end = (
            record["history_event_start"],
            record["history_event_end"],
        )
        scope = scope_for(config, result["name"], result["model"], result["effort"])
        _require(
            event_start == previous_event_end
            and event_start <= event_end <= len(history_events)
            and event_end - event_start <= MAX_EVENTS_PER_ATTEMPT,
            "Restart history event boundaries changed",
        )
        previous_event_end = event_end
        for index in range(event_start, event_end):
            event = history_events[index]
            _require(
                event["number"] == index
                and event["attempt"] == number
                and event["scope"] == scope
                and record["started_at"] <= event["at"] <= record["ended_at"],
                "Restart history crosses an attempt or condition boundary",
            )
            content = event["content"]
            if event["kind"] == "model_note":
                _require(
                    set(content) == {"kind", "text"}
                    and content["kind"] in NOTE_KINDS
                    and isinstance(content["text"], str)
                    and 0 < len(content["text"]) <= 600,
                    "Invalid unverified restart note",
                )
            else:
                _require(
                    event["kind"] == "source_observation"
                    and set(content) == {"request", "response"}
                    and content["request"].get("op")
                    in ("search", "read", "outline", "semantic_search"),
                    "Invalid restart source observation",
                )
        _require(
            record["history_events_before_sha256"]
            == fingerprint(history_events[:event_start])
            and record["history_events_after_sha256"]
            == fingerprint(history_events[:event_end]),
            "Restart history provenance changed",
        )
        expected_history = build_history(
            scope,
            checks[: record["check_start"]],
            history_events[:event_start],
            result["seed_proof"],
        )
        _require(
            payload.get("restart_history") == expected_history,
            "Restart history differs from prior host evidence",
        )
    else:
        _require(
            "restart_history" not in payload,
            "Unconfigured restart history in prompt",
        )
    return previous_event_end
