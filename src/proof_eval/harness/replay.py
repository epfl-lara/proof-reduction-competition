"""Pure prefix-observed stopping policies and recorded-support splice replay."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, median
from typing import Literal, Protocol, Sequence

from .discovery_tree import ProblemTree

Decision = Literal["continue", "end_attempt"]


@dataclass(frozen=True)
class RevealedView:
    elapsed_problem_seconds: float
    elapsed_attempt_seconds: float
    since_improvement_seconds: float
    best_raw_pct: float
    attempt_index: int
    known_cumulative_cost_usd: float | None
    attempt_ended: bool = False


class StoppingPolicy(Protocol):
    name: str
    reset_gain_pp: float

    def decide(self, view: RevealedView) -> Decision: ...


@dataclass(frozen=True)
class Identity:
    name: str = "identity"
    reset_gain_pp: float = 0

    def decide(self, view: RevealedView) -> Decision:
        return "continue"


@dataclass(frozen=True)
class Stagnation:
    minutes: float
    reset_gain_pp: float = 0

    @property
    def name(self) -> str:
        suffix = f"_delta_{self.reset_gain_pp:g}" if self.reset_gain_pp else ""
        return f"stagnation_{self.minutes:g}m{suffix}"

    def decide(self, view: RevealedView) -> Decision:
        return (
            "end_attempt"
            if view.since_improvement_seconds >= self.minutes * 60
            else "continue"
        )


@dataclass(frozen=True)
class AttemptCap:
    count: float
    reset_gain_pp: float = 0

    @property
    def name(self) -> str:
        return f"attempt_cap_{self.count:g}"

    def decide(self, view: RevealedView) -> Decision:
        return "end_attempt" if view.attempt_index >= self.count else "continue"


@dataclass(frozen=True)
class AttemptReplay:
    number: int
    started_elapsed: float
    ended_elapsed: float
    revealed_check_numbers: tuple[int, ...]
    gain_pp: float
    cost_estimate_usd: float | None


@dataclass(frozen=True)
class ReplayOutcome:
    name: str
    condition: tuple[str, str]
    run: str
    policy: str
    raw_combined_pct: float
    recorded_raw_pct: float
    loss_pp: float
    on_support: bool
    support_reason: str | None
    elapsed_seconds: float
    freed_seconds: float
    unspent_seconds: float | None
    estimated_cost_usd: float | None
    estimated_cost_savings_usd: float | None
    attempts: tuple[AttemptReplay, ...]
    anytime: tuple[tuple[float, float], ...]


def splice(tree: ProblemTree, policy: StoppingPolicy) -> ReplayOutcome:
    """Reuse only recorded attempt prefixes with a matching proof parent."""
    score = tree.seed_combined_pct
    incumbent = tree.seed_sha256
    timeline = [(0.0, score)]
    shift, elapsed, total_cost = 0.0, 0.0, 0.0
    observed_cost: float | None = 0.0
    support, reason = True, None
    replayed = []
    limit = tree.deadline if tree.deadline is not None else math.inf
    for attempt in tree.attempts:
        if isinstance(policy, AttemptCap) and attempt.number >= policy.count:
            break
        start = attempt.started - shift
        if start >= limit:
            elapsed = max(elapsed, limit - tree.problem_start)
            break
        if attempt.incumbent_sha256 != incumbent:
            support, reason = False, "next_parent_sha_mismatch"
            break
        end = min(attempt.ended - shift, limit)
        clock = start
        initial_score = score
        numbers: list[int] = []
        stopped_at = end
        revealed = 0
        for check in attempt.checks:
            at = check.at - shift
            if at > end:
                break
            revealed += 1
            numbers.append(check.number)
            if check.accepted:
                gain = check.combined_pct - score
                score, incumbent = check.combined_pct, check.code_sha256
                timeline.append((at - tree.problem_start, score))
                if gain >= policy.reset_gain_pp:
                    clock = at
            view = RevealedView(
                at - tree.problem_start,
                at - start,
                at - clock,
                score,
                attempt.number,
                observed_cost,
            )
            if policy.decide(view) == "end_attempt":
                stopped_at = at
                break
        if stopped_at == end:
            policy.decide(
                RevealedView(
                    end - tree.problem_start,
                    end - start,
                    end - clock,
                    score,
                    attempt.number,
                    observed_cost,
                    True,
                )
            )
        elapsed = stopped_at - tree.problem_start
        duration = max(0.0, stopped_at - start)
        full_duration = attempt.ended - attempt.started
        fraction = duration / full_duration if full_duration else 1.0
        cost = attempt.cost_usd * fraction if attempt.cost_usd is not None else None
        total_cost = (
            total_cost + cost if total_cost is not None and cost is not None else None
        )
        observed_cost = (
            observed_cost + attempt.cost_usd
            if observed_cost is not None
            and attempt.cost_usd is not None
            and abs(fraction - 1.0) <= 1e-9
            else None
        )
        replayed.append(
            AttemptReplay(
                attempt.number,
                start - tree.problem_start,
                elapsed,
                tuple(numbers),
                score - initial_score,
                cost,
            )
        )
        if any(c.accepted for c in attempt.checks[revealed:]):
            support, reason = False, "accepted_check_cut"
            break
        shift += attempt.ended - shift - stopped_at
        if stopped_at >= limit:
            break
    recorded_score = tree.recorded_raw_pct
    if recorded_score is None:
        recorded_score = tree.seed_combined_pct
        for attempt in tree.attempts:
            for check in attempt.checks:
                if check.accepted:
                    recorded_score = check.combined_pct
    original_elapsed = tree.attempts[-1].ended - tree.problem_start
    original_cost = (
        sum(a.cost_usd for a in tree.attempts)
        if all(a.cost_usd is not None for a in tree.attempts)
        else None
    )
    return ReplayOutcome(
        tree.name,
        tree.condition,
        tree.run,
        policy.name,
        score,
        recorded_score,
        recorded_score - score,
        support,
        reason,
        elapsed,
        max(0.0, original_elapsed - elapsed),
        (
            max(0.0, tree.deadline - tree.problem_start - elapsed)
            if tree.deadline
            else None
        ),
        total_cost,
        (
            original_cost - total_cost
            if original_cost is not None and total_cost is not None
            else None
        ),
        tuple(replayed),
        tuple(timeline),
    )


def policy_grid(protocol: dict) -> tuple[StoppingPolicy, ...]:
    return (
        Identity(),
        *(Stagnation(x) for x in protocol["grid_minutes"]),
        *(
            Stagnation(x, d)
            for d in protocol["reset_gain_pp"]
            for x in protocol["grid_minutes"]
        ),
        *(AttemptCap(k) for k in protocol["attempt_caps"]),
    )


def restart_yield(trees: Sequence[ProblemTree]) -> float | None:
    yields = []
    for tree in trees:
        score = tree.seed_combined_pct
        for attempt in tree.attempts:
            before = score
            for check in attempt.checks:
                if check.accepted:
                    score = check.combined_pct
            minutes = (attempt.ended - attempt.started) / 60
            if attempt.number >= 1 and minutes > 0:
                yields.append((score - before) / minutes)
    return median(yields) if yields else None


def summarize(
    outcomes: Sequence[ReplayOutcome], yield_pp_per_minute: float | None = None
) -> dict:
    if not outcomes:
        raise ValueError("Cannot summarize an empty cohort")
    freed = mean(o.freed_seconds / 60 for o in outcomes)
    known_costs = [
        o.estimated_cost_savings_usd
        for o in outcomes
        if o.estimated_cost_savings_usd is not None
    ]
    return {
        "problems": len(outcomes),
        "mean_raw_combined_pct": mean(o.raw_combined_pct for o in outcomes),
        "mean_loss_pp": mean(o.loss_pp for o in outcomes),
        "mean_delta_pp": mean(-o.loss_pp for o in outcomes),
        "on_support_problems": sum(o.on_support for o in outcomes),
        "wins": sum(o.loss_pp < -1e-9 for o in outcomes),
        "ties": sum(abs(o.loss_pp) <= 1e-9 for o in outcomes),
        "losses": sum(o.loss_pp > 1e-9 for o in outcomes),
        "mean_freed_minutes": freed,
        "median_freed_minutes": median(o.freed_seconds / 60 for o in outcomes),
        "mean_unspent_seconds": (
            mean(o.unspent_seconds for o in outcomes)
            if all(o.unspent_seconds is not None for o in outcomes)
            else None
        ),
        "reinvestment_model_estimate_pp": (
            freed * yield_pp_per_minute if yield_pp_per_minute is not None else None
        ),
        "median_restart_yield_pp_per_minute": yield_pp_per_minute,
        "known_cost_savings_problems": len(known_costs),
        "known_subset_mean_cost_savings_estimate_usd": (
            mean(known_costs) if known_costs else None
        ),
        "cost_estimator": "linear_in_time_no_guaranteed_bias",
    }


def eligible(
    summary: dict, controls: Sequence[dict], protocol: dict, *, lopo: bool = False
) -> bool:
    gate = protocol["gate"]
    count = summary["problems"]
    expected = gate["expected_problems"] - int(lopo)
    support_min = (
        math.ceil(gate["minimum_on_support"] / gate["expected_problems"] * count)
        if lopo
        else gate["minimum_on_support"]
    )
    value = summary["reinvestment_model_estimate_pp"]
    return (
        count == expected
        and summary["on_support_problems"] >= support_min
        and summary["mean_loss_pp"] <= gate["maximum_mean_loss_pp"] + 1e-12
        and summary["mean_freed_minutes"] >= gate["minimum_mean_freed_minutes"]
        and value is not None
        and value >= gate["minimum_reinvestment_ratio"] * summary["mean_loss_pp"]
        and len(controls) == len(protocol["robustness_runs"])
        and all(
            s["problems"] == expected
            and s["mean_loss_pp"] <= gate["maximum_robustness_loss_pp"] + 1e-12
            for s in controls
        )
    )
