"""Proof output contract and measurement-free goal context serialization."""

from __future__ import annotations

import hashlib
import re

from proof_eval.evidence.io import fingerprint as fingerprint
from proof_eval.verification.metrics import validate_candidate

FIELDS = (
    "length_reduction_pct",
    "heartbeat_reduction_pct",
    "compatibility_pct",
    "combined_pct",
)


def context_for_prompt(context: dict, costs: bool = False) -> dict:
    """Goal arms receive identical annotations; strip measurements for goal-only."""
    result = {
        k: v
        for k, v in context.items()
        if k
        in {
            "status",
            "proof_sha256",
            "primary_version",
            "version",
            "sites",
            "scope",
            "notes",
            "available_sites",
            "selected_sites",
        }
    }

    def strip(value):
        if isinstance(value, dict):
            return {
                k: strip(v)
                for k, v in value.items()
                if costs
                or not any(
                    word in k.lower()
                    for word in ("heartbeat", "allocation", "cost", "elapsed", "timing")
                )
            }
        if isinstance(value, list):
            return [strip(v) for v in value]
        return value

    return strip(result)


def extract_declaration(content: str, finish_reason: str) -> str:
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


def code_identity(row: dict, code: str) -> str:
    try:
        code = validate_candidate(row, code)[0]
    except ValueError:
        pass
    return hashlib.sha256(code.encode()).hexdigest()
