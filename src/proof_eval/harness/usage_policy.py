"""Resolve the explicitly pinned policy for incomplete native cost telemetry."""

from __future__ import annotations

from typing import Literal

UsagePolicy = Literal["strict", "best_effort"]


def resolve_usage_policy(
    policy: UsagePolicy | None, provider: str, tracking: str | None
) -> UsagePolicy:
    """New Codex cost runs estimate missing usage; historical configs stay strict."""
    if policy is None:
        return "best_effort" if provider == "codex" and tracking == "cost" else "strict"
    if policy not in ("strict", "best_effort"):
        raise ValueError("usage_policy must be 'strict' or 'best_effort'")
    if policy == "best_effort" and (provider != "codex" or tracking != "cost"):
        raise ValueError("Best-effort usage estimates require Codex cost tracking")
    return policy
