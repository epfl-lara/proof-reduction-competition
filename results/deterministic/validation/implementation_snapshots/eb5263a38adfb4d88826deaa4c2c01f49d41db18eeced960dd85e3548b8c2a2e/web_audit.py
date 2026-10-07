"""Offline checks of optional host-owned web retrieval evidence."""

import json
from pathlib import Path

from proof_eval.evidence.audit import _require
from proof_eval.evidence.io import digest, fingerprint


def audit_web(folder: Path, config: dict | None, *, deadline_expired: bool) -> dict:
    """Verify frozen settings and fetched bytes without accessing the network."""
    path = folder / "web_requests.jsonl"
    counts = {"requests": 0, "retrieved": 0, "errors": 0, "interrupted": 0}
    if not path.exists():
        return counts
    _require(config is not None, "Web requests exist in a condition without web tools")
    for number, record in enumerate(map(json.loads, path.read_text().splitlines()), 1):
        _require(record["number"] == number, "Web request sequence changed")
        _require(
            record["config_sha256"] == fingerprint(config),
            "Web request configuration changed",
        )
        _require(
            record["request"]["op"] in ("web_search", "web_open"),
            "Unknown recorded web operation",
        )
        counts["requests"] += 1
        if record["status"] == "started":
            _require(
                deadline_expired and "response" not in record,
                "Unfinished web request without a deadline stop",
            )
            counts["interrupted"] += 1
            continue
        _require(record["status"] == "completed", "Unknown web request status")
        response = record["response"]
        _require(
            response["kind"] in (record["request"]["op"], "tool_error"),
            "Web response operation changed",
        )
        if record.get("body_path") is not None:
            _require(
                record["body_path"] == f"web_responses/{number:04d}.body",
                "Web response body path changed",
            )
            _require(
                digest(folder / record["body_path"]) == record["body_sha256"],
                "Saved web response bytes changed",
            )
        if response["kind"] == "tool_error":
            counts["errors"] += 1
            continue
        source = response["source"]
        _require(
            source["body_path"] == record.get("body_path")
            and source["body_sha256"] == record.get("body_sha256"),
            "Web response provenance changed",
        )
        _require(
            source["http_status"] == 200
            and source["bytes"] == (folder / record["body_path"]).stat().st_size
            and source["bytes"] <= config["max_response_bytes"],
            "Web retrieval size or status changed",
        )
        _require(response["provider"] == config["provider"], "Web provider changed")
        if response["kind"] == "web_search":
            _require(
                response["query"] == record["request"]["query"]
                and response["count"] == len(response["matches"])
                and response["count"] <= record["request"].get("limit", 5),
                "Web search result bounds changed",
            )
        else:
            _require(
                source["requested_url"] == record["request"]["url"]
                and len(response["text"]) <= config["max_text_chars"],
                "Web page result bounds changed",
            )
        counts["retrieved"] += 1
    return counts
