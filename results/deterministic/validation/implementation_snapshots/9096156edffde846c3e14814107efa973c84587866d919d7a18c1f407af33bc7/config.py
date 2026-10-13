"""Typed public configuration for a model search batch."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from proof_eval.paths import ROOT
from proof_eval.providers.registry import (
    DEFAULT_CONDITIONS,
    PROVIDER_WORKERS,
    validate,
)

from .configuration import (
    BASE,
    DEFAULT_MODE,
    DEFAULT_OUTPUT,
    RUN_MODES,
)
from .semantic import SemanticSearchConfig
from .tracking import BudgetTracking, resolve_budgets, validate_budgets
from .usage_policy import UsagePolicy, resolve_usage_policy


@dataclass(frozen=True)
class RunConfig:
    output: Path = DEFAULT_OUTPUT
    conditions: tuple[tuple[str, str], ...] | None = None
    provider: Literal["codex", "lemex", "claude", "agy"] = "codex"
    names: tuple[str, ...] = ()
    mode: str = DEFAULT_MODE
    workers: int | None = None
    problem_timeout_seconds: float | None = None
    budget_tracking: BudgetTracking = "auto"
    budget_usd_per_problem: float = 3.0
    max_budget_restarts: int = 20
    max_transport_restarts: int = 2
    incumbents_from: Path | None = None
    carry_budgets_from: Path | None = None
    base: Path = BASE
    dataset: Path = ROOT / "data/benchmark_data_warmup.jsonl"
    environments: Path = ROOT / "environments.local.json"
    cache: Path = ROOT / ".proof-eval"
    references: Path = (
        ROOT / "results/deterministic/00_reference_baseline/reference_values.jsonl"
    )
    action: Literal["run", "estimate", "prepare", "report"] = "run"
    semantic_search: SemanticSearchConfig | bool | None = True
    web_search: bool = True
    usage_policy: UsagePolicy | None = None

    def __post_init__(self) -> None:
        if type(self.web_search) is not bool:
            raise ValueError("web_search must be a boolean")
        if (
            self.semantic_search is not None
            and type(self.semantic_search) is not bool
            and not isinstance(self.semantic_search, SemanticSearchConfig)
        ):
            raise ValueError(
                "semantic_search must be a boolean, asset configuration or None"
            )
        if self.conditions is None:
            try:
                object.__setattr__(
                    self, "conditions", DEFAULT_CONDITIONS[self.provider]
                )
            except KeyError:
                raise ValueError("Unknown agent provider: " + self.provider) from None
        if self.mode not in RUN_MODES:
            raise ValueError("Unsupported or retired search mode: " + self.mode)
        try:
            workers = PROVIDER_WORKERS[self.provider]
        except KeyError:
            raise ValueError("Unknown agent provider: " + self.provider) from None
        if self.workers is not None and (
            type(self.workers) is not int or self.workers != workers
        ):
            raise ValueError(f"{self.provider} batches use exactly {workers} workers")
        object.__setattr__(self, "workers", workers)
        if self.action not in ("run", "estimate", "prepare", "report"):
            raise ValueError("Unknown harness action")
        if not self.conditions or len(set(self.conditions)) != len(self.conditions):
            raise ValueError("Specify nonempty, unique model conditions")
        validate(self.provider, self.conditions)
        tracking, timeout = resolve_budgets(
            self.budget_tracking, self.problem_timeout_seconds, self.conditions
        )
        object.__setattr__(self, "budget_tracking", tracking)
        object.__setattr__(self, "problem_timeout_seconds", timeout)
        object.__setattr__(
            self,
            "usage_policy",
            resolve_usage_policy(self.usage_policy, self.provider, tracking),
        )
        validate_budgets(
            self.budget_tracking,
            self.budget_usd_per_problem,
            self.max_budget_restarts,
            self.problem_timeout_seconds,
            self.conditions,
        )
        if (
            type(self.max_transport_restarts) is not int
            or not 0 <= self.max_transport_restarts <= 20
        ):
            raise ValueError(
                "max_transport_restarts must be an integer between 0 and 20"
            )
        if len(set(self.names)) != len(self.names):
            raise ValueError("Duplicate theorem selection")
        if self.carry_budgets_from is not None and self.incumbents_from is not None:
            raise ValueError(
                "Budget carryover already reuses prior verified incumbents"
            )
