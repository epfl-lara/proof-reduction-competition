"""Exact occurrence lookup and bidirectional descriptive transition joins."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from .diffs import describe_span, selected_range, slice_bytes, touches
from .model import fragment_id, integer, score_delta, score_view
from .paging import Page, size

if TYPE_CHECKING:
    from .store import ProofHistory


def event_at(store: ProofHistory, check: object, cutoff: int) -> dict:
    return store._events[integer(check, "check_id", 0, cutoff)]


def variants(event: dict) -> list[tuple[str, str, str]]:
    result = [("submitted", event["code"], event["snapshot_id"])]
    if "evaluated_code" in event:
        result.append(
            ("evaluated", event["evaluated_code"], event["evaluated_snapshot_id"])
        )
    return result


def fragment_text(
    store: ProofHistory, db: sqlite3.Connection, identity: object, cutoff: int
) -> str:
    if not isinstance(identity, str) or len(identity) != 64:
        raise ValueError("fragment_hash must be a 64-character identity")
    row = db.execute("SELECT code FROM fragments WHERE id=?", (identity,)).fetchone()
    if row is None:
        raise ValueError("Unknown fragment; supply its exact text or a check range")
    text = bytes(row[0]).decode("utf-8")
    if fragment_id(text) != identity:
        raise ValueError("History fragment integrity failure; rebuild the index")
    if not any(
        text in code
        for event in store._events[: cutoff + 1]
        for _, code, _ in variants(event)
    ):
        raise ValueError("Fragment is unavailable in the requested history prefix")
    return text


def event_view(store: ProofHistory, event: dict) -> dict:
    return {
        "check_id": event["check_id"],
        "snapshot_id": event["snapshot_id"],
        "base_check_id": event["base_check"],
        "base_provenance": event["base_provenance"],
        "duplicate": event["duplicate"],
        "accepted_as_best": event["accepted"],
        **score_view(event, store.versions),
    }


def occurrence_id(event: dict, role: str, start: int, end: int) -> str:
    identity = (
        event["snapshot_id"] if role == "submitted" else event["evaluated_snapshot_id"]
    )
    return f"occ:{identity}:{event['check_id']}:{role}:{start}:{end}"


def read_occurrence(
    store: ProofHistory, value: object, cutoff: int
) -> tuple[dict, str, str, int, int]:
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError("Invalid occurrence_id")
    parts = value.split(":")
    if (
        len(parts) != 6
        or parts[0] != "occ"
        or parts[3] not in {"submitted", "evaluated"}
    ):
        raise ValueError("Invalid occurrence_id")
    try:
        check, start, end = (int(parts[i]) for i in (2, 4, 5))
    except ValueError as exc:
        raise ValueError("Invalid occurrence_id ranges") from exc
    event = event_at(store, check, cutoff)
    role = parts[3]
    choices = {name: (code, identity) for name, code, identity in variants(event)}
    if role not in choices or choices[role][1] != parts[1]:
        raise ValueError("Occurrence snapshot mismatch")
    code = choices[role][0]
    slice_bytes(code, start, end)
    return event, role, code, start, end


def resolve_text(
    store: ProofHistory, db: sqlite3.Connection, request: dict, cutoff: int
) -> str:
    selectors = [
        key
        for key in ("text", "fragment_hash", "check_id", "occurrence_id")
        if key in request
    ]
    if len(selectors) != 1:
        raise ValueError(
            "Provide exactly one of text, fragment_hash, check_id or occurrence_id"
        )
    ranges = {"byte_start", "byte_end", "line_start", "line_end"} & request.keys()
    if ranges and "check_id" not in request:
        raise ValueError("Find ranges require a check_id selector")
    if "text" in request:
        text = request["text"]
    elif "fragment_hash" in request:
        text = fragment_text(store, db, request["fragment_hash"], cutoff)
    elif "occurrence_id" in request:
        _, _, code, start, end = read_occurrence(
            store, request["occurrence_id"], cutoff
        )
        text = slice_bytes(code, start, end)
    else:
        event = event_at(store, request["check_id"], cutoff)
        start, end = selected_range(event["code"], request)
        text = slice_bytes(event["code"], start, end)
    if not isinstance(text, str) or not text:
        raise ValueError("History find requires nonempty exact text")
    if len(text.encode("utf-8")) > 16 * 1024 * 1024:
        raise ValueError("History query text exceeds 16 MiB")
    fragment_id(text)
    return text


def occurrence_page(
    store: ProofHistory, text: str, request: dict, page: Page
) -> tuple[list[dict], list[int] | None]:
    preferred_check, preferred_start = request.get("check_id"), None
    preferred_role = "submitted"
    if "occurrence_id" in request:
        event, preferred_role, _, preferred_start, _ = read_occurrence(
            store, request["occurrence_id"], page.as_of
        )
        preferred_check = event["check_id"]
    elif preferred_check is not None:
        preferred_start, _ = selected_range(
            store._events[preferred_check]["code"], request
        )
    check_order = list(range(page.as_of + 1))
    if preferred_check is not None:
        check_order.remove(preferred_check)
        check_order.insert(0, preferred_check)
    sources = [
        (store._events[check], role, code, identity)
        for check in check_order
        for role, code, identity in variants(store._events[check])
    ]
    if preferred_check is not None:
        sources.sort(
            key=lambda source: not (
                source[0]["check_id"] == preferred_check and source[1] == preferred_role
            )
        )
    position = (
        page.position
        if page.page == "occurrences" and page.position is not None
        else [0, 0, 0]
    )
    if not isinstance(position, list) or len(position) != 3:
        raise ValueError("Invalid occurrence cursor position")
    first = integer(position[0], "cursor source", 0, len(sources) - 1)
    first_segment = integer(position[1], "cursor segment", 0, 2)
    offset = integer(position[2], "cursor byte", 0, 16 * 1024 * 1024)
    needle, results = text.encode("utf-8"), []
    for source_index in range(first, len(sources)):
        event, role, code, identity = sources[source_index]
        data = code.encode("utf-8")
        segments = [(0, len(data) + 1)]
        if (
            event["check_id"] == preferred_check
            and role == preferred_role
            and preferred_start is not None
        ):
            segments = [
                (preferred_start, preferred_start + 1),
                (0, preferred_start),
                (preferred_start + 1, len(data) + 1),
            ]
        for segment, (lower, upper) in enumerate(segments):
            if source_index == first and segment < first_segment:
                continue
            start = (
                max(lower, offset)
                if source_index == first and segment == first_segment
                else lower
            )
            while True:
                found = data.find(
                    needle, start, min(len(data), upper + len(needle) - 1)
                )
                if found < 0 or found >= upper:
                    break
                if len(results) >= page.limit:
                    return results, [source_index, segment, found]
                end = found + len(needle)
                results.append(
                    {
                        "occurrence_id": occurrence_id(event, role, found, end),
                        "_position": [source_index, segment, found],
                        "check_id": event["check_id"],
                        "representation": role,
                        "snapshot_id": identity,
                        **describe_span(code, found, end),
                        "context_before": data[max(0, found - 100) : found].decode(
                            "utf-8", errors="ignore"
                        ),
                        "context_after": data[end : end + 100].decode(
                            "utf-8", errors="ignore"
                        ),
                        "verification": score_view(event, store.versions)[
                            "verification"
                        ],
                    }
                )
                start = found + 1
    return results, None


def transition_view(store: ProofHistory, event: dict, change: dict) -> dict:
    base = store._events[event["base_check"]]
    return {
        "transition_id": f"transition:{base['check_id']}:{event['check_id']}:{change['hunk']}",
        "base_check_id": base["check_id"],
        "check_id": event["check_id"],
        "base_provenance": event["base_provenance"],
        "kind": change["kind"],
        "alignment": change["alignment"],
        "lineage": "not_inferred",
        "base_span": change["base_span"],
        "result_span": change["result_span"],
        "base_fragment": change["base_fragment"],
        "result_fragment": change["result_fragment"],
        "base_excerpt": change["base_text"][:100],
        "result_excerpt": change["result_text"][:100],
        "excerpts_truncated": len(change["base_text"]) > 100
        or len(change["result_text"]) > 100,
        "base_outcome": score_view(base, store.versions),
        "result_outcome": score_view(event, store.versions),
        "whole_proof_delta_pp": score_delta(base, event, store.versions),
        "local_contribution": "not_measured",
    }


def transition_page(
    store: ProofHistory, db: sqlite3.Connection, text: str, page: Page
) -> tuple[list[dict], list[int] | None]:
    position = (
        page.position
        if page.page == "transitions" and page.position is not None
        else [0, 0]
    )
    if not isinstance(position, list) or len(position) != 2:
        raise ValueError("Invalid transition cursor position")
    check = integer(position[0], "cursor check", 0, page.as_of)
    hunk = integer(position[1], "cursor hunk", 0, 2**31 - 1)
    needle, results = text.encode("utf-8"), []
    rows = db.execute(
        "SELECT result_check,hunk,body FROM transitions WHERE result_check<=? "
        "AND (result_check>? OR (result_check=? AND hunk>=?)) ORDER BY result_check,hunk",
        (page.as_of, check, check, hunk),
    )
    for row in rows:
        event = store._events[row["result_check"]]
        base = store._events[event["base_check"]]
        change = json.loads(row["body"])
        directions = []
        if touches(base["code"], needle, change["base_span"]):
            directions.append("outgoing")
        if touches(event["code"], needle, change["result_span"]):
            directions.append("incoming")
        if not directions:
            continue
        if len(results) >= page.limit:
            return results, [row["result_check"], row["hunk"]]
        results.append(
            {
                **transition_view(store, event, change),
                "directions": directions,
                "match_relation": "changed_line_context_overlap",
            }
        )
    return results, None


def find(
    store: ProofHistory, db: sqlite3.Connection, request: dict, page: Page
) -> dict:
    if page.page not in (None, "occurrences", "transitions"):
        raise ValueError("Cursor is not a find page")
    text = resolve_text(store, db, request, page.as_of)
    identity = store._fragment(db, text)
    occurrences, occurrence_next = (
        occurrence_page(store, text, request, page)
        if page.page != "transitions"
        else ([], None)
    )
    transitions, transition_next = (
        transition_page(store, db, text, page)
        if page.page != "occurrences"
        else ([], None)
    )
    response = page.response
    response.update(
        fragment_hash=identity,
        fragment_bytes=len(text.encode("utf-8")),
        occurrences=occurrences,
        transitions=transitions,
        unknown_base_check_count=sum(
            event["check_id"] > 0 and event["base_check"] is None
            for event in store._events[: page.as_of + 1]
        ),
        parentage_note="Unknown bases are retained; absent transitions do not prove no edit occurred.",
        occurrences_returned=0,
        transitions_returned=0,
    )

    def update_cursors() -> None:
        response["occurrences_returned"] = len(occurrences)
        response["transitions_returned"] = len(transitions)
        response["occurrence_cursor"] = (
            page.cursor("occurrences", occurrence_next)
            if occurrence_next is not None
            else None
        )
        response["transition_cursor"] = (
            page.cursor("transitions", transition_next)
            if transition_next is not None
            else None
        )
        response["truncated"] = (
            occurrence_next is not None or transition_next is not None
        )

    update_cursors()
    while size(response) > page.budget and (occurrences or transitions):
        # Preserve one item from each channel when possible. Continuations point
        # to the first omitted item, so no exact occurrence or hunk disappears.
        if len(occurrences) > len(transitions) or not transitions:
            removed = occurrences.pop()
            occurrence_next = removed["_position"]
        else:
            removed = transitions.pop()
            transition_next = [
                removed["check_id"],
                int(removed["transition_id"].rsplit(":", 1)[1]),
            ]
        update_cursors()
    if page.page == "transitions" and transition_next is not None and not transitions:
        raise ValueError("max_chars cannot fit one transition; increase it")
    if page.page == "occurrences" and occurrence_next is not None and not occurrences:
        raise ValueError("max_chars cannot fit one occurrence; increase it")
    for item in occurrences:
        item.pop("_position")
    response["occurrences_returned"] = len(occurrences)
    response["transitions_returned"] = len(transitions)
    return page.finish()
