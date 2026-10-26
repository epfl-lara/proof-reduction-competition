"""Typed public configuration for a model search batch."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Literal

from proof_eval.defaults import QWEN_TIME_RESTARTS, VERIFICATION_TIMEOUT_SECONDS
from proof_eval.optimization.bounded import ALL_METHODS, validate_methods
from proof_eval.paths import ROOT
from proof_eval.providers.registry import (
    DEFAULT_CONDITIONS,
    MODEL_WORKERS,
    PROVIDER_WORKERS,
    QWEN_MODELS,
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
    provider: Literal["codex", "lemex", "lemex-local", "claude", "agy"] = "codex"
    names: tuple[str, ...] = ()
    mode: str = DEFAULT_MODE
    workers: int | None = None
    problem_timeout_seconds: float | None = None
    verification_timeout_seconds: float = VERIFICATION_TIMEOUT_SECONDS
    budget_tracking: BudgetTracking = "auto"
    budget_usd_per_problem: float = 3.0
    max_budget_restarts: int | None = None
    max_transport_restarts: int = 2
    incumbents_from: Path | None = None
    carry_budgets_from: Path | None = None
    deterministic_checkpoint: Path | None = None
    starting_proofs: Path | None = None
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
    restart_history: bool = False
    proof_theory_cleanup: bool = False
    deterministic: bool = False
    deterministic_methods: tuple[str, ...] = ALL_METHODS
    deterministic_seconds: float = 300.0

    def __post_init__(self) -> None:
        if (
            type(self.verification_timeout_seconds) not in (int, float)
            or not isfinite(self.verification_timeout_seconds)
            or self.verification_timeout_seconds <= 0
        ):
            raise ValueError("verification_timeout_seconds must be positive and finite")
        if type(self.deterministic) is not bool:
            raise ValueError("deterministic must be a boolean")
        validate_methods(self.deterministic_methods, self.deterministic_seconds)
        if self.deterministic:
            raise ValueError(
                "Model jobs do not run deterministic cleanup; use the cohort pipeline "
                "before and after model search (including checkpoint experiments)"
            )
        if (
            self.starting_proofs is not None
            and self.deterministic_checkpoint is not None
        ):
            raise ValueError(
                "Choose starting_proofs or deterministic_checkpoint, not both"
            )
        if self.incumbents_from is not None or self.carry_budgets_from is not None:
            raise ValueError(
                "New runs start from original proofs; resume the existing frozen run instead"
            )
        if type(self.proof_theory_cleanup) is not bool:
            raise ValueError("proof_theory_cleanup must be a boolean")
        if type(self.restart_history) is not bool:
            raise ValueError("restart_history must be a boolean")
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
            workers = max(
                MODEL_WORKERS.get(model, PROVIDER_WORKERS[self.provider])
                for model, _ in self.conditions
            )
        except KeyError:
            raise ValueError("Unknown agent provider: " + self.provider) from None
        if self.workers is not None and (
            type(self.workers) is not int or self.workers < 1
        ):
            raise ValueError("Model workers must be a positive integer")
        object.__setattr__(self, "workers", self.workers or workers)
        if self.action not in ("run", "estimate", "prepare", "report"):
            raise ValueError("Unknown harness action")
        if not self.conditions or len(set(self.conditions)) != len(self.conditions):
            raise ValueError("Specify nonempty, unique model conditions")
        validate(self.provider, self.conditions)
        if self.max_budget_restarts is None:
            object.__setattr__(
                self,
                "max_budget_restarts",
                (
                    QWEN_TIME_RESTARTS
                    if all(model in QWEN_MODELS for model, _ in self.conditions)
                    else 20
                ),
            )
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
        if self.deterministic_checkpoint is not None:
            from .checkpoint import validate_checkpoint_policy

            validate_checkpoint_policy(
                {
                    "initial_pipeline_version": 1,
                    "budget_tracking": tracking,
                    "problem_timeout_seconds": timeout,
                    "initial_deterministic_methods": (
                        self.deterministic_methods if self.deterministic else ()
                    ),
                    "mode": self.mode,
                    "conditions": self.conditions,
                }
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
