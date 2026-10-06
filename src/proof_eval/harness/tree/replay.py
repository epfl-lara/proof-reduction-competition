"""Replay ("dream") exploration policies over recorded search trees at no cost.

A recorded tree is an exact simulator of the branches that were actually run:
replaying a policy reuses each recorded expansion's children, scores and cost.
A policy can only be evaluated where history went. When it asks for a
(parent, card) expansion that was never recorded, the replay stops and is
flagged `off_history`; its partial result is not a valid estimate.

Scores are raw search scores before final cleanup, identical for every policy
replayed over the same history. Nothing here calls a model or compiles Lean.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from types import SimpleNamespace

from proof_eval.evidence.io import read

from .policy import FrontierPolicy, TreeView
from .search import tree_view


@dataclass(frozen=True)
class ReplayOutcome:
    name: str
    score: float
    cost_usd: float | None
    expansions: int
    stop: str
    off_history: bool


def load_history(cell: Path) -> tuple[str, TreeView]:
    """The recorded tree of one completed tree-search cell."""
    cell = Path(cell)
    inputs = read(cell / "input.json")
    ledger = cell / "evidence" / "checks.jsonl"
    checks = [json.loads(line) for line in ledger.read_text().splitlines()]
    session = SimpleNamespace(seed_evaluation=inputs["seed_evaluation"], checks=checks)
    return inputs["name"], tree_view(read(cell / "tree.json"), session)


def load_run(output: Path) -> dict[str, TreeView]:
    """Every recorded tree under a run's `cells/` directory, by theorem name."""
    histories = {}
    for path in sorted(Path(output).glob("cells/*/tree.json")):
        name, view = load_history(path.parent)
        histories[name] = view
    return histories


def replay(policy: FrontierPolicy, name: str, history: TreeView) -> ReplayOutcome:
    nodes = {node.id: node for node in history.nodes}
    seen_nodes, seen, used = [nodes[0]], [], set()

    def outcome(stop, off_history=False):
        view = TreeView(tuple(seen_nodes), tuple(seen))
        costs = [e.cost_usd for e in seen]
        return ReplayOutcome(
            name,
            view.best().score,
            None if any(c is None for c in costs) else sum(costs),
            len(seen),
            stop,
            off_history,
        )

    for _ in range(len(history.expansions) + 1):
        decision = policy.choose(TreeView(tuple(seen_nodes), tuple(seen)))
        if decision.action == "stop":
            return outcome(decision.reason)
        match = next(
            (
                e
                for e in history.expansions
                if e.id not in used
                and e.parent == decision.parent
                and e.card == decision.card
            ),
            None,
        )
        if match is None:
            return outcome("off_history", True)
        used.add(match.id)
        index = len(seen)
        seen.append(replace(match, id=index))
        seen_nodes.extend(replace(nodes[c], expansion=index) for c in match.children)
    return outcome("history_exhausted")


def policy_pool(base: FrontierPolicy) -> list[FrontierPolicy]:
    """Candidate policies that keep the deployed card order and budget."""
    pool = []
    for limit, flat, parent, card in itertools.product(
        range(1, base.max_expansions + 1),
        range(1, base.flat_stop + 1),
        ("best", "unexpanded"),
        ("rotate", "greedy"),
    ):
        pool.append(
            replace(
                base,
                max_expansions=limit,
                flat_stop=flat,
                parent_rule=parent,
                card_rule=card,
            )
        )
    return pool


def evaluate(policies: list[FrontierPolicy], histories: dict[str, TreeView]):
    """Mean score and cost of each policy; off-history replays are counted."""
    rows = []
    for policy in policies:
        outcomes = [replay(policy, n, h) for n, h in sorted(histories.items())]
        costs = [o.cost_usd for o in outcomes]
        rows.append(
            {
                "policy": policy.record(),
                "mean_score": sum(o.score for o in outcomes) / len(outcomes),
                "mean_cost_usd": (None if None in costs else sum(costs) / len(costs)),
                "max_cost_usd": None if None in costs else max(costs),
                "off_history": sum(o.off_history for o in outcomes),
                "outcomes": [asdict(o) for o in outcomes],
            }
        )
    return sorted(
        rows,
        key=lambda r: (
            r["off_history"],
            -r["mean_score"],
            r["mean_cost_usd"] if r["mean_cost_usd"] is not None else float("inf"),
        ),
    )


def dream(output: Path) -> dict:
    """Compare the deployed policy with every on-history candidate."""
    config = read(Path(output) / "config.json")
    deployed = FrontierPolicy.from_record(config["tree"]["policy"])
    histories = load_run(output)
    if not histories:
        raise ValueError("No recorded tree-search cells under " + str(output))
    rows = evaluate(policy_pool(deployed), histories)
    baseline = evaluate([deployed], histories)[0]
    return {
        "kind": "tree_policy_replay",
        "problems": len(histories),
        "deployed": {k: v for k, v in baseline.items() if k != "outcomes"},
        "best_on_history": [
            {k: v for k, v in row.items() if k != "outcomes"}
            for row in rows
            if not row["off_history"]
        ][:10],
        "scope": "Replay of recorded expansions only; no model calls or Lean "
        "measurements. Scores are before final cleanup.",
    }
