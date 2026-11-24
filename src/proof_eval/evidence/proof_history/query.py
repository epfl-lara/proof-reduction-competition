"""Bounded read-only history operations; no verifier or model dependencies."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from proof_eval.evidence.io import sha

from .browse import find_compact, overview
from .diagnostics import diagnostic_payload, failure_preview
from .diffs import describe_span, hunks, selected_range, slice_bytes
from .model import integer, score_delta
from .paging import Page, bounded_text, size

if TYPE_CHECKING:
    from .store import ProofHistory


from .lookup import event_at, event_view, find, fragment_text, read_occurrence, variants


def show(
    store: ProofHistory, db: sqlite3.Connection, request: dict, page: Page
) -> dict:
    if page.page not in (None, "show"):
        raise ValueError("Cursor is not a show page")
    selectors = [
        key for key in ("check_id", "occurrence_id", "fragment_hash") if key in request
    ]
    if len(selectors) != 1:
        raise ValueError("Show requires a check_id, occurrence_id or fragment_hash")
    if "fragment_hash" in request:
        code = fragment_text(store, db, request["fragment_hash"], page.as_of)
        page.response["fragment_hash"] = request["fragment_hash"]
    elif "occurrence_id" in request:
        event, role, full, start, end = read_occurrence(
            store, request["occurrence_id"], page.as_of
        )
        code = slice_bytes(full, start, end)
        page.response.update(
            event_view(store, event),
            representation=role,
            occurrence_id=request["occurrence_id"],
            occurrence_span=describe_span(full, start, end),
        )
        if role == "evaluated":
            page.response["snapshot_id"] = event["evaluated_snapshot_id"]
    else:
        event = event_at(store, request["check_id"], page.as_of)
        code = event["code"]
        page.response.update(event_view(store, event))
    if store.scope.get("version", 1) >= 2:
        page.response["total_lines"] = len(code.splitlines())
        if (
            "fragment_hash" not in request
            and page.response.get("verification") != "valid"
        ):
            failure = failure_preview(event, store.versions)
            if failure is not None:
                page.response["failure"] = failure
                page.response["diagnostics_hint"] = (
                    f"history errors {event['check_id']}"
                )
        if type(request.get("line_end")) is int and request["line_end"] > len(
            code.splitlines()
        ):
            page.response["requested_line_end"] = request["line_end"]
            page.response["range_clamped"] = True
            request = {**request, "line_end": len(code.splitlines())}
    start, end = selected_range(code, request)
    if page.position is not None:
        start = integer(page.position, "show cursor", start, end)
    code = slice_bytes(code, 0, end)
    return bounded_text(page, code, start=start)


def snapshot(store: ProofHistory, request: dict, page: Page) -> dict:
    if page.page not in (None, "snapshot"):
        raise ValueError("Cursor is not a snapshot page")
    event = event_at(store, request.get("check_id"), page.as_of)
    code = event["code"]
    page.response.update(
        check_id=event["check_id"],
        snapshot_id=event["snapshot_id"],
        content_sha256=sha(code),
    )
    start = request.get("byte_start", 0) if page.position is None else page.position
    return bounded_text(page, code, field="code_base64", start=start)


def diff(
    store: ProofHistory, db: sqlite3.Connection, request: dict, page: Page
) -> dict:
    before = event_at(
        store, request.get("base_check_id", request.get("from_check")), page.as_of
    )
    after = event_at(
        store, request.get("check_id", request.get("to_check")), page.as_of
    )
    historical = after["base_check"] == before["check_id"]
    changes = hunks(before["code"], after["code"])
    page.response.update(
        relation="historical_transition" if historical else "comparison",
        base_provenance=after["base_provenance"] if historical else "not_asserted",
        base=event_view(store, before),
        result=event_view(store, after),
        whole_proof_delta_pp=score_delta(before, after, store.versions),
        local_contribution="not_measured",
        total_hunks=len(changes),
        hunks=[],
    )
    if page.page not in (None, "diff"):
        raise ValueError("Cursor is not a diff page")
    start = (
        0
        if page.position is None
        else integer(page.position, "diff cursor", 0, len(changes))
    )
    next_index = start
    for change in changes[start : start + page.limit]:
        for side in ("base", "result"):
            store._fragment(db, change[f"{side}_text"])
        item = {
            key: value
            for key, value in change.items()
            if key not in {"base_text", "result_text"}
        }
        item.update(
            base_excerpt=change["base_text"][:160],
            result_excerpt=change["result_text"][:160],
            excerpts_truncated=len(change["base_text"]) > 160
            or len(change["result_text"]) > 160,
        )
        page.response["hunks"].append(item)
        next_index += 1
        page.response["next_cursor"] = (
            page.cursor("diff", next_index) if next_index < len(changes) else None
        )
        if size(page.response) > page.budget:
            page.response["hunks"].pop()
            next_index -= 1
            break
    page.response["next_cursor"] = (
        page.cursor("diff", next_index) if next_index < len(changes) else None
    )
    page.response["truncated"] = next_index < len(changes)
    if changes and not page.response["hunks"] and page.response["truncated"]:
        raise ValueError("max_chars cannot fit one diff hunk; increase it")
    return page.finish()


def query(
    store: ProofHistory,
    db: sqlite3.Connection,
    request: dict,
    *,
    query_id: int | None = None,
) -> dict:
    allowed = {
        "op",
        "action",
        "text",
        "fragment_hash",
        "check_id",
        "occurrence_id",
        "transition_id",
        "byte_start",
        "byte_end",
        "line_start",
        "line_end",
        "base_check_id",
        "from_check",
        "to_check",
        "as_of",
        "cursor",
        "page",
        "limit",
        "max_chars",
        "view",
    }
    if set(request) - allowed:
        raise ValueError(
            "Unsupported history request fields: "
            + ", ".join(sorted(set(request) - allowed))
        )
    if request.get("op", "history") != "history":
        raise ValueError("History op must be history")
    action = request.get("action")
    version = store.scope.get("version", 1)
    actions = {"find", "show", "snapshot", "diff", "expand", "status"}
    if version >= 2:
        actions |= {"overview", "errors"}
    if action not in actions:
        raise ValueError("Unknown history action")
    common = {"op", "action", "as_of", "max_chars", "limit", "cursor", "page"}
    ranges = {"byte_start", "byte_end", "line_start", "line_end"}
    action_fields = {
        "find": {"text", "fragment_hash", "check_id", "occurrence_id"} | ranges,
        "expand": {"fragment_hash", "transition_id"},
        "show": {"check_id", "occurrence_id", "fragment_hash"} | ranges,
        "diff": {"base_check_id", "from_check", "check_id", "to_check"},
        "snapshot": {"check_id", "byte_start"},
        "status": set(),
        "overview": set(),
        "errors": {"check_id", "byte_start"},
    }
    if version >= 2:
        action_fields["find"].add("view")
        action_fields["expand"].add("view")
    if set(request) - common - action_fields[action]:
        raise ValueError("Unsupported fields for history " + action)
    if action == "diff" and (
        {"base_check_id", "from_check"} <= request.keys()
        or {"check_id", "to_check"} <= request.keys()
    ):
        raise ValueError("Choose one name for each diff check selector")
    if action == "expand" and {"fragment_hash", "transition_id"} <= request.keys():
        raise ValueError("Choose one expand selector")
    page = Page(store, request, query_id)
    if "view" in request and request["view"] not in {"raw", "compact"}:
        raise ValueError("History view must be raw or compact")
    if action == "overview":
        return overview(store, page)
    if action == "errors":
        if page.page not in (None, "errors"):
            raise ValueError("Cursor is not an errors page")
        event = event_at(store, request.get("check_id"), page.as_of)
        page.response.update(
            check_id=event["check_id"],
            format="json",
            source="saved_verifier_diagnostics",
        )
        payload = json.dumps(
            diagnostic_payload(event, store.versions), ensure_ascii=False
        )
        start = request.get("byte_start", 0) if page.position is None else page.position
        return bounded_text(page, payload, field="diagnostics_json", start=start)
    if action == "status":
        if set(request) - {"op", "action", "as_of", "max_chars", "limit"}:
            raise ValueError("Unsupported history status fields")
        events = store._events[: page.as_of + 1]
        page.response.update(
            check_count=page.as_of,
            seed_check_id=0,
            snapshot_count=len(
                {identity for event in events for _, _, identity in variants(event)}
            ),
            known_base_check_count=sum(
                event["base_check"] is not None for event in events
            ),
            unknown_base_check_count=sum(
                event["check_id"] > 0 and event["base_check"] is None
                for event in events
            ),
        )
        return page.finish()
    if action == "snapshot":
        if set(request) - {
            "op",
            "action",
            "check_id",
            "byte_start",
            "as_of",
            "max_chars",
            "limit",
            "cursor",
            "page",
        }:
            raise ValueError("Unsupported snapshot fields")
        return snapshot(store, request, page)
    if action == "show":
        return show(store, db, request, page)
    if action == "diff":
        return diff(store, db, request, page)
    if action == "expand" and "transition_id" in request:
        value = request["transition_id"]
        if not isinstance(value, str) or len(value) > 100:
            raise ValueError("Invalid transition_id")
        parts = value.split(":")
        if len(parts) != 4 or parts[0] != "transition":
            raise ValueError("Invalid transition_id")
        try:
            base, result, hunk = map(int, parts[1:])
        except ValueError as exc:
            raise ValueError("Invalid transition_id") from exc
        event = event_at(store, result, page.as_of)
        if (
            event["base_check"] != base
            or not db.execute(
                "SELECT 1 FROM transitions WHERE result_check=? AND hunk=?",
                (result, hunk),
            ).fetchone()
        ):
            raise ValueError("Unknown historical transition")
        return diff(
            store, db, {**request, "base_check_id": base, "check_id": result}, page
        )
    if (
        version >= 2
        and request.get("view") != "raw"
        and page.page not in {"occurrences", "transitions"}
    ):
        return find_compact(store, db, request, page)
    return find(store, db, request, page)
