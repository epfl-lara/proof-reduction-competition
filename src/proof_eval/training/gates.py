"""Transition gates, separate from model scores and rollout reward."""

from __future__ import annotations

import hashlib
from pathlib import Path

from proof_eval.evidence.immutable import canonical
from proof_eval.training.reward import UnscorableEpisode


def launch_plan_sha256(plan: dict) -> str:
    """Bind authorization to every plan field except its own authorization hash."""
    return hashlib.sha256(
        canonical({k: v for k, v in plan.items() if k != "launch_authorization_sha256"})
    ).hexdigest()


def require_launch_authorization(plan: dict, authorization: dict) -> None:
    if (
        authorization.get("status") != "authorized"
        or authorization.get("scope") != "train"
        or not authorization.get("human_instruction")
    ):
        raise RuntimeError("Explicit training authorization is required")
    if authorization.get("authorized_plan_sha256") != launch_plan_sha256(plan):
        raise RuntimeError("Immediate launch authorization belongs to another RL plan")


def assert_episode_reward_usable(info: dict) -> None:
    if info.get("reward_authority") != "host_ProofSession" or not info.get(
        "reward_receipt_sha256"
    ):
        raise UnscorableEpisode("No host-owned terminal episode reward")


def require_preparation_policy(records: list[dict], exclusions: list[str]) -> None:
    """Only declared, compiler-confirmed invalid originals may be excluded."""
    allowed = set(exclusions)
    if len(allowed) != len(exclusions):
        raise ValueError("Duplicate original exclusion")
    for record in records:
        if record["status"] == "prepared":
            continue
        outcomes = record.get("reference_outcomes", {})
        failed = [v for v in outcomes.values() if v.get("status") != "prepared"]
        if (
            record["task_id"] not in allowed
            or not failed
            or any(
                v.get("status") != "failed"
                or not any(
                    d.get("data") == "Target declaration depends on sorryAx"
                    for d in v.get("diagnostics", [])
                )
                for v in failed
            )
        ):
            raise RuntimeError(
                "Unresolved original preparation failure: " + record["task_id"]
            )


def assert_no_unknown_dispatch(folder: Path) -> None:
    for name in (
        "submission-intent.json",
        "launch-committed.json",
        "submission-unknown.json",
    ):
        if (folder / name).exists():
            raise RuntimeError(
                f"Inspect exact saved {name}; do not submit another training job"
            )
