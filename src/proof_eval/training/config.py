"""Explicit filesystem roots for frozen, authorized training releases."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from proof_eval.evidence.io import read


@dataclass(frozen=True)
class TrainingRelease:
    root: Path
    plan_path: Path

    def plan(self) -> dict:
        if self.plan_path != self.root / "plan.json":
            raise ValueError(
                "Execution requires the plan.json inside the frozen release"
            )
        value = read(self.plan_path)
        for key in ("root", "home", "source_environments", "harness_home"):
            if not Path(value[key]).is_absolute():
                raise ValueError(
                    "Training paths must be explicit absolute paths: " + key
                )
        if value.get("context_tokens", 0) <= 0 or value.get("episode_seconds", 0) <= 0:
            raise ValueError("Positive context and episode budgets are required")
        if not 1 <= value.get("reference_preparation_workers", 4) <= 32:
            raise ValueError("Reference preparation workers must be between 1 and 32")
        for key in ("reference_timeout_retries", "original_timeout_retries"):
            if type(value.get(key, 0)) is not int or value.get(key, 0) not in (0, 1):
                raise ValueError(
                    "At most one recorded timeout retry is allowed: " + key
                )
        return value
