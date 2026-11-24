"""Compact, prefix-bounded browsing of distinct proofs and textual edits."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from typing import TYPE_CHECKING

from .diagnostics import failure_preview
from .diffs import touches
from .lookup import resolve_text, variants
from .model import integer, score_delta, score_view
from .paging import Page, size

if TYPE_CHECKING:
    from .store import ProofHistory


def _card(store: ProofHistory, event: dict) -> dict:
    score = score_view(event, store.versions)
    card = {
        "check_id": event["check_id"],
        "base_check_id": event["base_check"],
        "verification": score["verification"],
        "total_score": score["total_score"],
        "source_tokens": score["source_tokens"],
        "primary_heartbeats": score["primary_heartbeats"],
        "accepted_as_best": event["accepted"],
    }
    failure = failure_preview(event, store.versions)
    if failure is not None and score["verification"] != "valid":
        card["failure"] = failure
    return card


def _category(card: dict) -> str:
    if card["verification"] != "valid":
        return card["verification"]
    if "whole_proof_delta_pp" in card:
        delta = card["whole_proof_delta_pp"]
        return "improved" if delta is not None and delta > 0 else "other_valid"
    return (
        "improved"
        if card.get("ever_accepted_as_best", card["accepted_as_best"])
        else "other_valid"
    )


def _balanced(cards: list[dict]) -> list[dict]:
    """Show useful valid alternatives alongside recent failures, deterministically."""
    buckets = defaultdict(list)
    for card in cards:
        buckets[_category(card)].append(card)
    for key, bucket in buckets.items():
        bucket.sort(
            key=lambda card: (
                (
                    -(card["total_score"] or 0)
                    if key in {"improved", "other_valid"}
                    else 0
                ),
                -card["check_id"],
            )
        )
    result = []
    for index in range(max(map(len, buckets.values()), default=0)):
        for key in ("improved", "invalid", "other_valid", "incomplete"):
            if index < len(buckets[key]):
                result.append(buckets[key][index])
    return result


def _snapshots(store: ProofHistory, events: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for event in events:
        # Exact submitted bytes and verification classes stay distinct. This
        # groups repeated checks for display, never merges their evidence.
        groups[
            (event["snapshot_id"], score_view(event, store.versions)["verification"])
        ].append(event)
    cards = []
    for group in groups.values():
        event = group[-1]
        card = _card(store, event)
        card["ever_accepted_as_best"] = any(item["accepted"] for item in group)
        card.update(
            check_count=len(group),
            first_check_id=group[0]["check_id"],
            latest_check_id=event["check_id"],
        )
        cards.append(card)
    return _balanced(cards)


def _finish_page(page: Page, cards: list[dict], channel: str) -> dict:
    if page.page not in (None, channel):
        raise ValueError("Cursor is not a " + channel + " page")
    start = (
        0
        if page.position is None
        else integer(page.position, "cursor position", 0, len(cards))
    )
    response = page.response
    response.update(items=[], total_items=len(cards), next_cursor=None)
    index = start

    def advance() -> None:
        response["truncated"] = index < len(cards)
        response["next_cursor"] = (
            page.cursor(channel, index) if index < len(cards) else None
        )

    for card in cards[start : start + page.limit]:
        response["items"].append(card)
        index += 1
        advance()
        if size(response) > page.budget:
            response["items"].pop()
            index -= 1
            break
    advance()
    if index == start and index < len(cards):
        raise ValueError("max_chars cannot fit one history item; increase it")
    return page.finish()


def overview(store: ProofHistory, page: Page) -> dict:
    events = store._events[: page.as_of + 1]
    page.response.update(
        view="compact",
        grouping="exact_submitted_snapshot_and_verification",
        ordering="interleaved_best_valid_recent_invalid_other_valid_incomplete",
        check_count=page.as_of,
        detail="history show CHECK; history diff BASE CHECK; history errors CHECK",
    )
    return _finish_page(page, _snapshots(store, events), "overview")


def find_compact(
    store: ProofHistory, db: sqlite3.Connection, request: dict, page: Page
) -> dict:
    text = resolve_text(store, db, request, page.as_of)
    identity = store._fragment(db, text)
    events = store._events[: page.as_of + 1]
    matching = [
        event for event in events if any(text in code for _, code, _ in variants(event))
    ]
    groups: dict[tuple, list[tuple[dict, dict, list[str]]]] = defaultdict(list)
    needle = text.encode("utf-8")
    rows = db.execute(
        "SELECT result_check,body FROM transitions WHERE result_check<=? ORDER BY result_check,hunk",
        (page.as_of,),
    )
    for row in rows:
        event = events[row["result_check"]]
        base = events[event["base_check"]]
        change = json.loads(row["body"])
        directions = []
        if touches(base["code"], needle, change["base_span"]):
            directions.append("outgoing")
        if touches(event["code"], needle, change["result_span"]):
            directions.append("incoming")
        if directions:
            card = _card(store, event)
            card["whole_proof_delta_pp"] = score_delta(base, event, store.versions)
            key = (change["base_fragment"], change["result_fragment"], _category(card))
            groups[key].append((event, change, directions))
    cards = []
    for group in groups.values():
        event, change, directions = group[-1]
        base = events[event["base_check"]]
        card = _card(store, event)
        card.update(
            transition_id=f"transition:{base['check_id']}:{event['check_id']}:{change['hunk']}",
            base_provenance=event["base_provenance"],
            alignment=change["alignment"],
            base_excerpt=change["base_text"][:120],
            result_excerpt=change["result_text"][:120],
            excerpts_truncated=len(change["base_text"]) > 120
            or len(change["result_text"]) > 120,
            directions=directions,
            base_score=score_view(base, store.versions)["total_score"],
            whole_proof_delta_pp=score_delta(base, event, store.versions),
            check_count=len({item[0]["check_id"] for item in group}),
            context_count=len(
                {
                    (
                        events[item[0]["base_check"]]["snapshot_id"],
                        item[0]["snapshot_id"],
                    )
                    for item in group
                }
            ),
            hunk_count=len(group),
        )
        cards.append(card)
    snapshots = _snapshots(store, matching)
    page.response.update(
        view="compact",
        fragment_hash=identity,
        matching_check_count=len(matching),
        matching_check_ids=[card["check_id"] for card in snapshots[:3]],
        matching_checks_preview_truncated=len(snapshots) > 3,
        item_kind="textual_edit" if cards else "snapshot",
        grouping=(
            "exact_edit_text_and_outcome_class"
            if cards
            else "exact_submitted_snapshot_and_verification"
        ),
        score_scope="representative_whole_proof_only",
        local_contribution="not_measured",
        context_note="Grouped text may have different goal states; inspect the representative full proof before reuse.",
        unknown_base_check_count=sum(
            event["check_id"] > 0 and event["base_check"] is None for event in events
        ),
        detail="history diff BASE CHECK; history errors CHECK; find --view raw for every occurrence and transition",
    )
    return _finish_page(page, _balanced(cards) if cards else snapshots, "matches")
