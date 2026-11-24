"""Deterministic schedules over verified proof states, independent of transport."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Callable

from .cleanup import BUDGET, METHODS, PROOF_THEORY_METHODS
from .engine import Budget

GAIN_ORDER = (
    "simp",
    "menu",
    "facts",
    "search",
    "proof_theory",
    "collapse",
    "wrappers",
    "arith_min",
    "lint",
    "delete",
    "golf",
    "reuse",
    "relax",
    "simp_min",
    "rw_min",
    "consolidate",
)


@dataclass(frozen=True)
class SearchPlan:
    """Finite research work bounds; there is deliberately no overall wall cap."""

    methods: tuple[str, ...] = GAIN_ORDER
    strategy: str = "repeat"
    budget: Budget = BUDGET
    sweeps: int = 8
    width: int = 3
    depth: int = 4

    def __post_init__(self) -> None:
        if (
            not self.methods
            or len(set(self.methods)) != len(self.methods)
            or set(self.methods) - set(METHODS + PROOF_THEORY_METHODS)
            or self.strategy not in {"sweep", "repeat", "beam"}
            or any(
                type(n) is not int or n < 1
                for n in (
                    self.sweeps,
                    self.width,
                    self.depth,
                    self.budget.rounds,
                    self.budget.trials,
                    self.budget.sites,
                )
            )
            or type(self.budget.min_gain) not in (int, float)
            or not math.isfinite(self.budget.min_gain)
            or not 0 <= self.budget.min_gain < 100
        ):
            raise ValueError("Invalid deterministic search plan")

    def record(self) -> dict:
        return {**asdict(self), "methods": list(self.methods)}

    @classmethod
    def from_record(cls, value: dict) -> SearchPlan:
        return cls(
            **{
                **value,
                "methods": tuple(value["methods"]),
                "budget": Budget(**value["budget"]),
            }
        )


def one_sweep_plan(min_gain: float = BUDGET.min_gain) -> SearchPlan:
    """Fixed cleanup schedule with the run's recorded selection margin."""
    return SearchPlan(strategy="sweep", budget=replace(BUDGET, min_gain=min_gain))


def plans() -> dict[str, SearchPlan]:
    """Globally fixed orders and settings; no per-theorem tuning or model calls."""
    return {
        "one_sweep": one_sweep_plan(),
        "repeat_gain_order": SearchPlan(),
        "repeat_reverse_order": SearchPlan(methods=tuple(reversed(GAIN_ORDER))),
        "repeat_deeper": SearchPlan(budget=Budget(rounds=12, trials=128, sites=12)),
        "beam_three": SearchPlan(strategy="beam"),
    }


def traverse(
    initial: str,
    plan: SearchPlan,
    expand: Callable[[str, str], dict],
    value: Callable[[str], float],
) -> dict:
    """Visit method/order alternatives in a stable order, keeping branch diversity.

    Expand returns a method's best state and all its useful verified children.
    Beam selection occurs only after every method on every frontier state finishes.
    A no-change sweep is a local stop under bounded operators, never optimality.
    """
    if plan.strategy != "beam":
        current = initial
        for sweep in range(1 if plan.strategy == "sweep" else plan.sweeps):
            before = current
            for method in plan.methods:
                current = expand(current, method)["best"]
            if current == before:
                return {"stop": "no_change_sweep", "sweeps": sweep + 1}
        return {
            "stop": "one_sweep" if plan.strategy == "sweep" else "sweep_limit",
            "sweeps": sweep + 1,
        }
    frontier, expanded = [initial], set()
    for depth in range(plan.depth):
        children = set()
        for parent in frontier:
            expanded.add(parent)
            for method in plan.methods:
                children.update(expand(parent, method)["children"])
        frontier = sorted(children - expanded, key=lambda key: (-value(key), key))[
            : plan.width
        ]
        if not frontier:
            return {"stop": "frontier_exhausted", "depth": depth + 1}
    return {"stop": "depth_limit", "depth": plan.depth, "frontier": frontier}
