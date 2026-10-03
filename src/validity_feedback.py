"""Bounded correctness-only feedback for a separate proof-debugging experiment.

This module reads saved verifier responses. It neither invokes Lean nor calls a
model. Only diagnostic text and version-level validity are exposed; evaluator
scores, measurements, references, timings, and successful-check logs are ignored.
"""
from __future__ import annotations

import json
import re


_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_MEASUREMENT_MARKER = re.compile(
    r"PROOF_(?:EVAL|CONTEXT)(?:_[A-Za-z0-9]+)?|(?:missing|no|absent).*heartbeat.*marker|"
    r"heartbeat.*marker.*(?:missing|absent)|#\s*count_heartbeats", re.I,
)
_METRIC_LINE = re.compile(
    r"\b(?:heartbeat(?:s|_raw)?|tactic_allocations|allocations?|elapsed(?:_seconds)?|"
    r"wall[-_ ]?time|timing|reference_denominators|incumbent_scores|combined_pct|"
    r"(?:length|heartbeat)_reduction_pct|compatibility_pct|proof_length|"
    r"(?:candidate|reference|combined|performance|token)\s+(?:score|cost|count|length)|"
    r"(?:prompt|completion|total)[_ ]tokens|\d+(?:\.\d+)?\s*(?:milliseconds?|seconds?)\b)", re.I,
)
_SORRY_WRAPPER = re.compile(r"target declaration depends on sorryAx", re.I)
_INVALID_MESSAGES = {
    "generation_truncated": "The response ended before a complete declaration was returned. Recover a complete declaration.",
    "empty_final_content": "No final declaration was returned.",
    "ambiguous_code_fences_or_surrounding_text": "Return exactly one complete declaration, with no surrounding prose or alternative proofs.",
    "query_tactic_in_final_output": "Replace query tactics with a concrete proof; the final declaration must not contain query tactics.",
}


def _required_versions(required_versions):
    if isinstance(required_versions, str):
        raise ValueError("required_versions must be a sequence of version names")
    versions = list(required_versions)
    if (not versions or any(not isinstance(v, str) or not v for v in versions)
            or len(set(versions)) != len(versions)):
        raise ValueError("Provide unique nonempty required version names")
    return versions


def all_versions_passed(evaluation, required_versions):
    """Require actual successful compiler checks for exactly the supplied cohort.

    No combined score or aggregate evaluator status is used: an unavailable
    measurement denominator does not invalidate a completed correctness check.
    """
    versions = _required_versions(required_versions)
    checks = evaluation.get("per_version", {})
    return isinstance(checks, dict) and set(checks) == set(versions) and all(
        isinstance(checks[v], dict) and checks[v].get("status") == "passed"
        and checks[v].get("passed") is True for v in versions
    )


def _sanitize_message(text):
    text = _ANSI.sub("", text)
    safe = []
    for line in text.splitlines():
        if _MEASUREMENT_MARKER.search(line) or _METRIC_LINE.search(line):
            continue
        safe.append(line)
    return "\n".join(safe).strip()


def _truncate_message(text, limit):
    if len(text) <= limit:
        return text
    marker = "\n… [truncated]\n"
    target_at = text.rfind("⊢")
    if limit <= len(marker):
        return (text[target_at:] if target_at >= 0 else text)[:limit]
    if target_at >= 0:
        target = text[target_at:]
        target_budget = min(len(target), max(limit // 2, limit - 300))
        prefix_budget = max(0, limit - len(marker) - target_budget)
        return text[:min(prefix_budget, target_at)] + marker + target[:target_budget]
    return text[:limit - len(marker)] + marker


def _errors(diagnostics, *, invalid=False):
    messages = []
    for diagnostic in diagnostics:
        if isinstance(diagnostic, str):
            text = diagnostic
        elif isinstance(diagnostic, dict) and diagnostic.get("severity") == "error":
            text = diagnostic.get("data")
            if not isinstance(text, str) or not text.strip():
                text = diagnostic.get("message", "")
        else:
            continue
        if not isinstance(text, str):
            continue
        if invalid:
            text = _INVALID_MESSAGES.get(text, text)
            if "exceeds" in text.lower() and "size limit" in text.lower():
                text = "The submitted declaration exceeds the accepted input size."
        text = _sanitize_message(text)
        if text and text not in messages:
            messages.append(text)
    real_errors = [message for message in messages if not _SORRY_WRAPPER.search(message)]
    return real_errors or messages


def build_validity_feedback(evaluation, required_versions, *, max_total_chars=12000,
                            max_message_chars=2000, max_messages_per_version=4):
    """Return bounded, version-labeled errors without any performance feedback.

    ``max_total_chars`` bounds the JSON serialization with ``ensure_ascii=False``.
    Long errors retain the final goal target when present. Timeout/unavailable
    outcomes have generic explanations rather than numeric runtime diagnostics.
    Unknown or missing checks remain unavailable, never successful or invalid.
    """
    versions = _required_versions(required_versions)
    for label, value in (("max_total_chars", max_total_chars),
                         ("max_message_chars", max_message_chars),
                         ("max_messages_per_version", max_messages_per_version)):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{label} must be a positive integer")
    checks = evaluation.get("per_version", {})
    checks = checks if isinstance(checks, dict) else {}
    primary = checks.get(versions[0], {})
    primary = primary if isinstance(primary, dict) else {}
    valid = all_versions_passed(evaluation, versions)
    invalid = evaluation.get("status") == "invalid"
    feedback = {
        "kind": "lean_correctness_feedback", "status": "valid" if valid else "incomplete",
        "primary_version": versions[0],
        "primary_passed": primary.get("status") == "passed" and primary.get("passed") is True,
        "all_versions_passed": valid, "required_versions": versions,
        "errors": [], "versions": [], "truncated": False,
    }
    pending = []
    if invalid:
        feedback["status"] = "invalid"
        feedback["all_versions_passed"] = False
        pending.append((feedback["errors"], _errors(evaluation.get("diagnostics", []), invalid=True)
                        or ["The candidate did not satisfy the declaration input requirements."]))
    for version in versions:
        item = checks.get(version, {})
        item = item if isinstance(item, dict) else {}
        raw_status = item.get("status")
        passed = raw_status == "passed" and item.get("passed") is True
        status = "passed" if passed else raw_status if raw_status in ("failed", "timeout", "unavailable") else "unavailable"
        if invalid and version not in checks:
            status = "not_checked"
        out = {"version": version, "status": status, "passed": passed, "errors": []}
        feedback["versions"].append(out)
        if status == "failed":
            messages = _errors(item.get("diagnostics", [])) or ["Lean rejected this declaration; no further compiler error was recorded."]
        elif status == "timeout":
            messages = ["Verification stopped before completion. Correctness for this version is unresolved."]
        elif status == "unavailable":
            messages = ["The verifier is unavailable for this version. This is not evidence that the proof is incorrect."]
        else:
            messages = []
        pending.append((out["errors"], messages))
    if not valid and not invalid:
        statuses = {v["status"] for v in feedback["versions"]}
        feedback["status"] = next((s for s in ("failed", "timeout", "unavailable") if s in statuses), "incomplete")

    def size():
        return len(json.dumps(feedback, ensure_ascii=False))

    if size() > max_total_chars:
        raise ValueError("max_total_chars is too small for the required-version validity metadata")
    for destination, messages in pending:
        if len(messages) > max_messages_per_version:
            feedback["truncated"] = True
        for message in messages[:max_messages_per_version]:
            clipped = _truncate_message(message, max_message_chars)
            if clipped != message:
                feedback["truncated"] = True
            destination.append(clipped)
            if size() <= max_total_chars:
                continue
            feedback["truncated"] = True
            destination.pop()
            # JSON escaping costs differ from Python character counts. Find a
            # bound using the serialized payload rather than assuming equality.
            low, high, fitting = 1, min(len(message), max_message_chars), None
            while low <= high:
                limit = (low + high) // 2
                candidate = _truncate_message(message, limit)
                destination.append(candidate)
                fits = size() <= max_total_chars
                destination.pop()
                if fits:
                    fitting, low = candidate, limit + 1
                else:
                    high = limit - 1
            if fitting is not None:
                destination.append(fitting)
    return feedback
