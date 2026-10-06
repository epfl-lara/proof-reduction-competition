"""Bounded native retries and classification of terminal transport failures."""

from __future__ import annotations

import re

REQUEST_MAX_RETRIES = 4
STREAM_MAX_RETRIES = 5
RECOVERY_BACKOFF_SECONDS = 2.0


def retryable_transport_failure(generation: dict) -> bool:
    """Only a terminal, observed transient failure can admit a fresh session.

    Missing output, credentials, model errors and a started request without a
    terminal record remain indeterminate or permanent failures.
    """
    if generation.get("status") != "transport_error":
        return False
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
