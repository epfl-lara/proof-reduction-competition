"""Scope/prefix-bound query cursors and serialized response budgets."""

from __future__ import annotations

import base64
import json
from typing import Any

from proof_eval.evidence.io import fingerprint

from .model import integer


def size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, allow_nan=False))


class Page:
    def __init__(self, store, request: dict, query_id: int | None) -> None:
        self.store = store
        self.limit = integer(request.get("limit", 5), "limit", 1, 20)
        self.budget = integer(request.get("max_chars", 6000), "max_chars", 2000, 12000)
        self.signature = fingerprint(
            {
                key: value
                for key, value in request.items()
                if key not in {"cursor", "page", "max_chars", "limit", "as_of", "op"}
            }
        )
        self.page = request.get("page")
        if self.page not in (
            None,
            "occurrences",
            "transitions",
            "show",
            "snapshot",
            "diff",
            "overview",
            "matches",
            "errors",
        ):
            raise ValueError("Unknown history page type")
        self.position = None
        cursor = request.get("cursor")
        self.as_of = integer(
            request.get("as_of", store.indexed_through_check),
            "as_of",
            0,
            store.indexed_through_check,
        )
        if cursor is not None:
            if not isinstance(cursor, str) or len(cursor) > 4096:
                raise ValueError("Invalid history cursor")
            try:
                decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
            except (ValueError, UnicodeError) as exc:
                raise ValueError("Invalid history cursor") from exc
            if not isinstance(decoded, dict) or set(decoded) != {
                "schema",
                "scope",
                "query",
                "as_of",
                "prefix",
                "page",
                "position",
            }:
                raise ValueError("Invalid history cursor fields")
            cutoff = integer(
                decoded["as_of"], "cursor as_of", 0, store.indexed_through_check
            )
            if (
                type(decoded["schema"]) is not int
                or decoded["schema"] != 1
                or decoded["scope"] != store.scope_sha256
                or decoded["query"] != self.signature
                or decoded["prefix"] != store._prefixes[cutoff]
                or ("as_of" in request and self.as_of != cutoff)
                or (self.page is not None and self.page != decoded["page"])
            ):
                raise ValueError(
                    "History cursor does not match this query/scope/prefix"
                )
            self.as_of = cutoff
            self.page = decoded["page"]
            self.position = decoded["position"]
        self.response = {
            "kind": "proof_history",
            "action": request["action"],
            "indexed_through_check": store.indexed_through_check,
            "as_of": self.as_of,
            "truncated": False,
        }
        if query_id is not None:
            self.response["history_query_id"] = integer(
                query_id, "query_id", 1, 2**63 - 1
            )

    def cursor(self, page: str, position: Any) -> str:
        payload = {
            "schema": 1,
            "scope": self.store.scope_sha256,
            "query": self.signature,
            "as_of": self.as_of,
            "prefix": self.store._prefixes[self.as_of],
            "page": page,
            "position": position,
        }
        return base64.urlsafe_b64encode(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).decode()

    def finish(self) -> dict:
        if size(self.response) > self.budget:
            raise ValueError("max_chars is too small for history metadata; increase it")
        return self.response


def bounded_text(page: Page, text: str, *, field: str = "code", start: int = 0) -> dict:
    """Return exact text chunks using UTF-8 byte boundaries and JSON size."""
    data = text.encode("utf-8")
    integer(start, "byte_start", 0, len(data))
    try:
        remaining = data[start:].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("byte_start must lie on a UTF-8 boundary") from exc
    response = page.response
    response.update(byte_start=start, total_bytes=len(data))

    def candidate(count: int) -> dict:
        piece = remaining[:count]
        end = start + len(piece.encode("utf-8"))
        last = end == len(data)
        return {
            field: (
                base64.b64encode(piece.encode("utf-8")).decode()
                if field == "code_base64"
                else piece
            ),
            "byte_end": end,
            "next_byte_start": None if last else end,
            "next_cursor": None if last else page.cursor(response["action"], end),
            "truncated": not last,
        }

    low, high, fitting = 0, min(len(remaining), page.budget), None
    while low <= high:
        count = (low + high) // 2
        part = candidate(count)
        if size({**response, **part}) <= page.budget:
            fitting, low = part, count + 1
        else:
            high = count - 1
    if fitting is None or (remaining and fitting["byte_end"] == start):
        raise ValueError("max_chars cannot fit a history text chunk")
    response.update(fitting)
    return page.finish()
