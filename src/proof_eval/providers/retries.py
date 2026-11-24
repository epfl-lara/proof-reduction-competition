"""Bounded native retries and classification of terminal transport failures."""

from __future__ import annotations

import re

from proof_eval.evidence.io import fingerprint

REQUEST_MAX_RETRIES = 4
STREAM_MAX_RETRIES = 5
RECOVERY_BACKOFF_SECONDS = 2.0


OWNED_CLIENT_EOF = (
    "In-process app-server event stream closed before the active turn completed"
)


def owned_client_eof(events: list[dict]) -> bool:
    """Recognize an active native turn that ended without a terminal event.

    This is only an event-shape test. It authorizes no retry without separate
    host evidence that the owned process and every descendant have stopped.
    """
    return (
        any(e.get("type") == "turn.started" for e in events)
        and not any(e.get("type") in {"turn.completed", "turn.failed"} for e in events)
        and all(
            reconnect_notice(e) or e.get("message") == OWNED_CLIENT_EOF
            for e in events
            if e.get("type") == "error"
        )
    )


def _confirmed_owned_client_eof(generation: dict) -> bool:
    marker = generation.get("owned_client_eof")
    ownership = generation.get("process_ownership")
    if not isinstance(marker, dict) or not isinstance(ownership, dict):
        return False
    cleanup = ownership.get("cleanup", {})
    identities = [ownership.get("supervisor", {}), ownership.get("native", {})]
    if not isinstance(cleanup, dict) or not all(
        isinstance(p, dict) for p in identities
    ):
        return False
    return (
        generation.get("provider") == "lemex-local"
        and generation.get("completed_turns") == 0
        and generation.get("supervisor_returncode") == 0
        and marker.get("schema_version") == 1
        and marker.get("reason") == "active_native_event_stream_eof"
        and marker.get("tool_service_drained") is True
        and marker.get("ownership_sha256") == fingerprint(ownership)
        and ownership.get("schema_version") == 1
        and ownership.get("native_exited") is True
        and type(ownership.get("native_returncode")) is int
        and cleanup.get("complete") is True
        and cleanup.get("remaining_pids") == []
        and all(
            type(p.get("pid")) is int
            and p["pid"] > 0
            and isinstance(p.get("start_ticks"), str)
            and p["start_ticks"].isdigit()
            for p in identities
        )
        and identities[0]["pid"] != identities[1]["pid"]
        and not any(
            e.get("type") == "turn.failed"
            or (
                e.get("type") == "error"
                and not reconnect_notice(e)
                and e.get("message") != OWNED_CLIENT_EOF
            )
            for e in generation.get("events_errors", [])
        )
    )


def retryable_transport_failure(generation: dict) -> bool:
    """Only a terminal, observed transient failure can admit a fresh session.

    Missing output, credentials, model errors and a started request without a
    terminal record remain indeterminate or permanent failures.
    """
    if generation.get("status") != "transport_error":
        return False
    if generation.get("external_supervisor_signal") or generation.get(
        "process_ownership", {}
    ).get("supervisor_signals"):
        return False
    if _confirmed_owned_client_eof(generation):
        return True
    errors = generation.get("events_errors", [])
    if not errors or not any(e.get("type") == "turn.failed" for e in errors):
        return False
    messages = []
    for event in errors:
        if reconnect_notice(event):
            continue
        value = event.get("message", event.get("error", ""))
        messages.append(value.get("message", "") if isinstance(value, dict) else value)
    return bool(messages) and all(
        isinstance(message, str)
        and (
            re.search(r"unexpected status (?:408|429|500|502|503|504)\b", message)
            or any(
                text in message
                for text in (
                    "Transport error: network error:",
                    "idle timeout waiting for SSE",
                    "stream closed before response.completed",
                    "websocket closed by server before response.completed",
                )
            )
            or (
                generation.get("response_usage_schema_version") in (1, 2)
                and (
                    message.startswith(
                        "stream disconnected before completion: An error occurred while processing your request."
                    )
                    or message
                    in (
                        "Selected model is at capacity. Please try a different model.",
                        "We’re currently experiencing high demand, which may cause temporary errors.",
                    )
                )
            )
        )
        for message in messages
    )


def reconnect_notice(event: dict) -> bool:
    """The native client emits recoverable reconnects as top-level errors."""
    return event.get("type") == "error" and bool(
        re.match(
            r"^Reconnecting\.\.\. (?:\d+/\d+|waiting for network)\b",
            event.get("message", ""),
        )
    )


def recovery_count(generations: list[dict]) -> int:
    """Count fresh sessions actually admitted after failed terminal requests."""
    return sum(retryable_transport_failure(g) for g in generations[:-1])
