"""Opt-in restarted sessions: spend unused per-problem budget from the best proof.

After a session returns its final answer, a fresh agent session may start from
the host's best proof. A restart is allowed only while the best combined score
is below a threshold, every earlier session reports complete usage, and the
recorded cost plus the largest earlier session's cost stays within the
per-problem budget. That projection is a conservative estimate, not a hard
limit: the first session itself is unbounded, as in the frozen configuration.

A restart never resamples a failed or indeterminate request; it follows only a
received final answer. Each decision and restart prompt is saved before the
request is sent, so a resumed cell repeats exactly the same bytes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from proof_eval.evidence.io import read, write_json
from proof_eval.protocol import extract_declaration
from proof_eval.providers.costs import CostConfig, generations_cost

from .prompts import messages
from .session import ProofSession

RESTART_NOTE = (
    "Restart context. An earlier agent session already optimized this theorem; "
    "its best checked proof is now the incumbent above and remains saved. The "
    "earlier stopping reasons below say what was tried. Look for a different "
    "approach rather than repeating those attempts."
)


@dataclass(frozen=True)
class RestartPolicy:
    """Bounds for restarted sessions; `sessions` counts the first session too."""

    sessions: int = 3
    below_pct: float = 90.0
    budget_usd: float = 3.0

    def __post_init__(self):
        if type(self.sessions) is not int or self.sessions < 2:
            raise ValueError("Restarts need at least two sessions in total")
        if not 0 < self.below_pct <= 100:
            raise ValueError("Restart threshold must be a combined score in (0, 100]")
        if not self.budget_usd > 0:
            raise ValueError("Restart budget must be positive")

    def record(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "rule": "restart after a received final answer while best < below_pct, "
            "usage is complete, and spent + largest session cost <= budget_usd",
        }


def decide(
    policy: RestartPolicy,
    costs: list[float | None],
    best_pct: float,
    last_status: str,
) -> tuple[bool, str]:
    """Whether to start another session, and the recorded reason."""
    if len(costs) >= policy.sessions:
        return False, "session_limit"
    if last_status != "received":
        return False, "previous_session_not_received"
    if best_pct >= policy.below_pct:
        return False, "score_threshold_reached"
    if not costs or any(cost is None for cost in costs):
        return False, "unknown_usage"
    if sum(costs) + max(costs) > policy.budget_usd + 1e-12:
        return False, "projected_budget_exceeded"
    return True, "restart"


def session_cost(config: dict, model: str, effort: str, generation: dict):
    """Recorded API-equivalent cost of one session, or None when unknown."""
    cost = generations_cost(
        CostConfig(model, effort, **config["cost_assumptions"]),
        [generation],
        budget_usd=config["budget_usd_per_problem"],
    )
    return cost.get("total_usd")


def restart_messages(pack: dict, session: ProofSession, reasons: list[str]):
    """The canonical task messages seeded with the host's best proof."""
    request = messages(pack, seed=(session.best_code, session.best_evaluation))
    note = {"note": RESTART_NOTE, "earlier_stopping_reasons": reasons}
    request[1]["content"] += "\n" + json.dumps(note, ensure_ascii=False, indent=2)
    return request


def run_restarts(
    folder: Path,
    pack: dict,
    config: dict,
    model: str,
    effort: str,
    session: ProofSession,
    generations: list[dict],
    generate: Callable[[Path, list[dict]], dict],
) -> list[dict]:
    """Run restarted sessions, appending their generations; return decisions.

    `generate(attempt_folder, messages)` performs one durable agent request.
    """
    fields = ("sessions", "below_pct", "budget_usd")
    policy = RestartPolicy(**{k: config["restart"][k] for k in fields})
    path = folder / "restarts.json"
    log = read(path) if path.exists() else []
    reasons = (
        log[0]["earlier_stopping_reasons"][:1]
        if log
        else [_stop_reason(session, generations)]
    )
    for index in range(policy.sessions):
        if index < len(log):
            entry = log[index]
        else:
            costs = [session_cost(config, model, effort, g) for g in generations]
            best = session.best_evaluation["scores"]["combined_pct"]
            allowed, reason = decide(policy, costs, best, generations[-1]["status"])
            entry = {
                "session": len(generations) + 1,
                "decision": "restart" if allowed else "stop",
                "reason": reason,
                "recorded_costs_usd": costs,
                "best_combined_pct": best,
                "earlier_stopping_reasons": list(reasons),
                "messages": (
                    restart_messages(pack, session, reasons) if allowed else None
                ),
            }
            log.append(entry)
            write_json(path, log)
        if entry["decision"] != "restart":
            break
        attempt = folder / f"attempt_{len(generations):02d}"
        if not (attempt / "generation.json").exists():
            # A live restart needs an open session; resumed ones keep their record.
            session.finished = None
            (session.folder / "finished.json").unlink(missing_ok=True)
        generation = generate(attempt, entry["messages"])
        generations.append(generation)
        if generation["status"] == "received":
            try:
                final = extract_declaration(
                    generation["content"], generation["finish_reason"]
                )
            except ValueError:
                final = generation["content"]
            session.check(final, origin="final_harness")
        if "stopping_reason" not in entry:
            entry["stopping_reason"] = _stop_reason(session, generations)
            write_json(path, log)
        reasons.append(entry["stopping_reason"])
    return log


def _stop_reason(session: ProofSession, generations: list[dict]) -> str:
    if session.finished:
        return session.finished["reason"]
    return "no explicit stopping reason; status " + generations[-1]["status"]
