"""Explicit remaining-cohort selection after a known terminal pre-update batch."""

from __future__ import annotations

from pathlib import Path

from proof_eval.evidence.immutable import read, sha


def consumed_tasks(plan: dict) -> tuple[str, ...]:
    specs = plan.get("previous_policy_attempts")
    if not specs:
        return ()
    if isinstance(specs, dict):
        specs = [specs]
    consumed = set()
    for spec in specs:
        path = Path(spec["archive_result"])
        if sha(path) != spec["archive_result_sha256"]:
            raise ValueError("Previous policy-attempt archive changed")
        saved = read(path)
        if (
            saved["learned_checkpoint_directories"]
            or saved["home_optimizer_receipts"]
            or saved["home_checkpoint_receipts"]
        ):
            raise ValueError(
                "A learned run needs exact checkpoint/optimizer continuation"
            )
        rows = saved.get("policy_rollouts", saved.get("r11_rollouts", []))
        actual = {r["task_id"] for r in rows}
        if actual != set(spec["excluded_task_ids"]) or not actual:
            raise ValueError(
                "Consumed-task exclusion does not match saved rollout starts"
            )
        if not any(r["model_turns"] for r in rows):
            raise ValueError("No actual prior policy output is bound to this exclusion")
        consumed.update(actual)
    return tuple(sorted(consumed))
