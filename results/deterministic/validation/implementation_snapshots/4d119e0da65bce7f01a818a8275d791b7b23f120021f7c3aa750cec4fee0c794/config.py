"""Typed public configuration for a model search batch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from proof_eval.paths import ROOT
from proof_eval.providers.registry import DEFAULT_CONDITIONS, validate

from .configuration import (
    BASE,
    DEFAULT_MODE,
    DEFAULT_OUTPUT,
    RUN_MODES,
)


@dataclass(frozen=True)
class RunConfig:
    output: Path = DEFAULT_OUTPUT
    conditions: tuple[tuple[str, str], ...] | None = None
    provider: Literal["codex", "lemex", "claude"] = "codex"
    names: tuple[str, ...] = ()
    mode: str = DEFAULT_MODE
    workers: int = 5
    base: Path = BASE
    dataset: Path = ROOT / "data/benchmark_data_warmup.jsonl"
    environments: Path = ROOT / "environments.local.json"
    cache: Path = ROOT / ".proof-eval"
    references: Path = (
        ROOT / "results/deterministic/00_reference_baseline/reference_values.jsonl"
    )
    action: Literal["run", "estimate", "prepare", "report"] = "run"
    pilot: bool = False

    def __post_init__(self):
        if self.conditions is None:
            try:
                object.__setattr__(
                    self, "conditions", DEFAULT_CONDITIONS[self.provider]
                )
            except KeyError:
                raise ValueError("Unknown agent provider: " + self.provider) from None
        if self.mode not in RUN_MODES:
            raise ValueError("Unsupported or retired search mode: " + self.mode)
        if type(self.workers) is not int or self.workers < 1:
            raise ValueError("workers must be a positive integer")
        if self.action not in ("run", "estimate", "prepare", "report"):
            raise ValueError("Unknown harness action")
        if not self.conditions or len(set(self.conditions)) != len(self.conditions):
            raise ValueError("Specify nonempty, unique model conditions")
        validate(self.provider, self.conditions)
        if self.provider == "lemex" and self.workers > 5:
            raise ValueError("Lemex permits at most five simultaneous gateway sessions")
        if len(set(self.names)) != len(self.names):
            raise ValueError("Duplicate theorem selection")
