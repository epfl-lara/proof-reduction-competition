"""Tree data model and deterministic exploration policies.

A node is a checked proof: the seed is node 0 and every later node is a
host-ledger check number. An expansion is one short agent call that starts
from a parent node with an optional strategy-card focus; every check it makes
becomes a child of that parent. A policy sees only this tree and recorded
costs, so the same policy can drive a live search or be replayed over history.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

CARDS = (
    "reuse_abstraction",
    "induct_on_evidence",
    "factor_local_identity",
    "explicit_witnesses",
    "change_representation",
)


@dataclass(frozen=True)
class Node:
    id: int
    parent: int | None
    expansion: int | None
    score: float | None  # Combined score when every version passed, else None.


@dataclass(frozen=True)
class Expansion:
    id: int
    parent: int
    card: str | None
    cost_usd: float | None
    status: str
    children: tuple[int, ...]


@dataclass(frozen=True)
class TreeView:
    nodes: tuple[Node, ...]
    expansions: tuple[Expansion, ...] = ()

    def valid(self) -> list[Node]:
        return [node for node in self.nodes if node.score is not None]

    def best(self) -> Node:
        """Highest valid score; the earliest node wins ties."""
        return max(self.valid(), key=lambda node: (node.score, -node.id))

    def best_after(self, count: int) -> float:
        """Best score using only the first `count` expansions."""
        allowed = {None} | {e.id for e in self.expansions[:count]}
        return max(n.score for n in self.valid() if n.expansion in allowed)


@dataclass(frozen=True)
class Decision:
    action: Literal["expand", "stop"]
    reason: str
    parent: int | None = None
    card: str | None = None


@dataclass(frozen=True)
class FrontierPolicy:
    """Expand a frontier node with a strategy card until a stopping rule fires.

    The root expansion always starts from the seed with the canonical prompt
    (no card). Later expansions choose the parent by `parent_rule` and the card
    by `card_rule`. Stops: expansion limit, an unreceived previous expansion,
    unknown usage, projected budget (spent plus largest expansion so far), or
    `flat_stop` consecutive expansions that did not raise the best score.
    """

    max_expansions: int = 5
    parent_rule: Literal["best", "unexpanded"] = "best"
    card_rule: Literal["rotate", "greedy"] = "rotate"
    cards: tuple[str, ...] = CARDS
    flat_stop: int = 3
    budget_usd: float = 1.0
    margin_pp: float = field(default=0.05)

    def __post_init__(self):
        if self.max_expansions < 1 or self.flat_stop < 1 or not self.cards:
            raise ValueError("Tree policy needs positive limits and at least one card")
        if self.parent_rule not in ("best", "unexpanded"):
            raise ValueError("Unknown parent rule")
        if self.card_rule not in ("rotate", "greedy"):
            raise ValueError("Unknown card rule")
        if not self.budget_usd > 0:
            raise ValueError("Tree budget must be positive")

    def record(self) -> dict:
        return {**asdict(self), "cards": list(self.cards)}

    @classmethod
    def from_record(cls, record: dict) -> FrontierPolicy:
        return cls(**{**record, "cards": tuple(record["cards"])})

    def choose(self, view: TreeView) -> Decision:
        expansions = view.expansions
        if not expansions:
            return Decision("expand", "root", parent=0)
        if len(expansions) >= self.max_expansions:
            return Decision("stop", "expansion_limit")
        if expansions[-1].status != "received":
            return Decision("stop", "previous_expansion_not_received")
        costs = [e.cost_usd for e in expansions]
        if any(cost is None for cost in costs):
            return Decision("stop", "unknown_usage")
        if sum(costs) + max(costs) > self.budget_usd + 1e-12:
            return Decision("stop", "projected_budget_exceeded")
        if self._flat_run(view) >= self.flat_stop:
            return Decision("stop", "plateau")
        return Decision("expand", "frontier", self._parent(view), self._card(view))

    def _flat_run(self, view: TreeView) -> int:
        run = 0
        for count in range(len(view.expansions), 0, -1):
            if view.best_after(count) > view.best_after(count - 1) + self.margin_pp:
                break
            run += 1
        return run

    def _parent(self, view: TreeView) -> int:
        if self.parent_rule == "unexpanded":
            expanded = {e.parent for e in view.expansions}
            fresh = [n for n in view.valid() if n.id not in expanded]
            if fresh:
                return max(fresh, key=lambda n: (n.score, -n.id)).id
        return view.best().id

    def _card(self, view: TreeView) -> str:
        carded = [e for e in view.expansions if e.card is not None]
        if self.card_rule == "rotate":
            return self.cards[len(carded) % len(self.cards)]
        tried = {e.card for e in carded}
        for card in self.cards:
            if card not in tried:
                return card
        scores = {n.id: n.score for n in view.nodes}

        def gain(card):
            values = [
                max(
                    [scores[c] for c in e.children if scores[c] is not None],
                    default=float("-inf"),
                )
                - scores[e.parent]
                for e in carded
                if e.card == card
            ]
            return sum(values) / len(values)

        return max(self.cards, key=lambda card: (gain(card), -self.cards.index(card)))


@dataclass(frozen=True)
class TreeSearch:
    """Frozen tree-search settings: the live policy and per-expansion checks."""

    policy: FrontierPolicy = FrontierPolicy()
    max_checks: int = 6

    def __post_init__(self):
        if type(self.max_checks) is not int or self.max_checks < 1:
            raise ValueError("Each expansion needs at least one check")

    def record(self) -> dict:
        return {"policy": self.policy.record(), "max_checks": self.max_checks}

    @classmethod
    def from_record(cls, record: dict) -> TreeSearch:
        return cls(FrontierPolicy.from_record(record["policy"]), record["max_checks"])
