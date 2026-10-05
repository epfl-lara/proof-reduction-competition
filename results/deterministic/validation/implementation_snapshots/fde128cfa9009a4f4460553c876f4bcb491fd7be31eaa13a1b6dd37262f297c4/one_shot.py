"""Fixed one-shot prompts and conservative extraction, separate from evaluation."""
from __future__ import annotations

import hashlib
import json
import re


ARMS = ("plain", "cards", "goals", "cards_goals", "cards_goals_costs")
FIELDS = ("length_reduction_pct", "heartbeat_reduction_pct", "compatibility_pct", "combined_pct")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def select_cards(bank, code, count=4):
    """Frozen lexical selection uses only the common incumbent, never model output."""
    def matches(trigger):
        trigger = trigger.strip()
        if not trigger:
            return False
        pattern = (r"(?<!\w)" if re.match(r"\w", trigger[0]) else "") + re.escape(trigger)
        pattern += r"(?!\w)" if re.match(r"\w", trigger[-1]) else ""
        return bool(re.search(pattern, code))
    scored = [(sum(matches(trigger) for trigger in card["triggers"]), card) for card in bank["cards"]]
    ranked = sorted(scored, key=lambda pair: (-pair[0], pair[1]["id"]))
    return [card for score, card in ranked[:count] if score > 0]


def context_for_prompt(context, costs=False):
    """Goal arms receive identical annotations; strip measurements for goal-only."""
    result = {k: v for k, v in context.items() if k in {
        "status", "proof_sha256", "primary_version", "version", "sites", "scope", "notes",
        "available_sites", "selected_sites"}}
    def strip(value):
        if isinstance(value, dict):
            return {k: strip(v) for k, v in value.items()
                    if costs or not any(word in k.lower() for word in ("heartbeat", "allocation", "cost", "elapsed", "timing"))}
        if isinstance(value, list):
            return [strip(v) for v in value]
        return value
    return strip(result)


def build_messages(system, row, code, incumbent, source_context, arm, bank, context=None):
    if arm not in ARMS:
        raise ValueError(f"Unknown arm: {arm}")
    primary = incumbent["primary_version"]
    reference = incumbent["per_version"][primary]["reference"]
    payload = {
        "name": row["name"], "source": row["source"], "required_versions": row["version_info"],
        "exact_statement": row["statement"],
        "reference_denominators": {"tokens": row["proof_length"], "primary_heartbeats": reference["heartbeats"]},
        "incumbent_scores": incumbent["scores"],
        "preceding_source_excerpt": source_context,
        "source_excerpt_note": "Read-only context preceding the declaration; may start mid-definition. It is not part of the requested output.",
        "incumbent_declaration": code,
    }
    if "cards" in arm:
        payload["strategy_cards"] = [{k: card[k] for k in ("id", "title", "preconditions", "action", "failure_modes")}
                                     for card in select_cards(bank, code)]
    if "goals" in arm:
        if context is None or context.get("status") != "ok":
            raise ValueError("Goal context unavailable; do not silently turn a goal arm into plain")
        payload["incumbent_goal_annotations"] = context_for_prompt(context, costs=arm.endswith("costs"))
    return [{"role": "system", "content": system},
            {"role": "user", "content": "Optimize this declaration.\n" + json.dumps(payload, ensure_ascii=False, indent=2)}]


def extract_declaration(content, finish_reason):
    """No theorem synthesis, reasoning fallback, multiple-choice selection or repair."""
    if finish_reason == "length":
        raise ValueError("generation_truncated")
    text = content.strip()
    if not text:
        raise ValueError("empty_final_content")
    if text.startswith("```"):
        match = re.fullmatch(r"```(?:lean|lean4)?\s*\n(.*?)\n```", text, flags=re.S)
        if not match or "```" in match.group(1):
            raise ValueError("ambiguous_code_fences_or_surrounding_text")
        text = match.group(1).strip()
    if "```" in text:
        raise ValueError("ambiguous_code_fences_or_surrounding_text")
    if re.search(r"\b(?:exact|apply|simp|simp_all|dsimp|aesop|grind)\?", text):
        raise ValueError("query_tactic_in_final_output")
    return text


def zero_evaluation(reason):
    return {"status": "invalid", "scores": dict.fromkeys(FIELDS, 0.0), "per_version": {}, "diagnostics": [reason]}


def summarize(records, expected, baseline):
    complete = [r for r in records if r.get("evaluation", {}).get("scores", {}).get("combined_pct") is not None]
    finished = len(records) == expected
    fully_scored = finished and len(complete) == expected
    def mean(key, field):
        return sum(r[key]["scores"][field] for r in records) / expected if finished else None
    return {
        "expected_problems": expected, "recorded_problems": len(records), "scored_outputs": len(complete),
        "raw_mean": {f: mean("evaluation", f) if fully_scored else None for f in FIELDS},
        "selected_mean": {f: mean("selected_evaluation", f) for f in FIELDS},
        "incumbent_mean": baseline,
        "selected_gain_pp": mean("selected_evaluation", "combined_pct") - baseline["combined_pct"] if finished else None,
        "improved_problems": sum(r.get("accepted", False) for r in records),
        "all_versions_passed_outputs": sum(r.get("all_versions_passed", False) for r in records),
        "primary_passed_outputs": sum(r.get("evaluation", {}).get("per_version", {}).get(
            r.get("evaluation", {}).get("primary_version"), {}).get("passed") is True for r in records),
        "invalid_or_failed_outputs": sum(r.get("evaluation", {}).get("status") in {"invalid", "failed"} for r in records),
        "unavailable_outputs": len(records) - len(complete),
        "truncated_outputs": sum(r.get("generation", {}).get("finish_reason") == "length" for r in records),
        "prompt_tokens": sum(r.get("generation", {}).get("usage", {}).get("prompt_tokens", 0) for r in records),
        "completion_tokens": sum(r.get("generation", {}).get("usage", {}).get("completion_tokens", 0) for r in records),
        "request_elapsed_seconds_sum": sum(r.get("generation", {}).get("elapsed_seconds", 0) for r in records),
    }
