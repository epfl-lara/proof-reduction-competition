"""Host-orchestrated tree search for one theorem, durable and replayable.

Each policy decision, with its request messages, is saved to `tree.json`
before the request starts; the ledger range and recorded cost of each
expansion are saved when it ends. A resumed cell reuses saved decisions and
messages byte for byte. Expansion `i` uses folder `attempt_{i:02d}`; the root
expansion's request equals the cell's canonical input messages.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from proof_eval.evidence.io import read, write_json
from proof_eval.paths import ROOT
from proof_eval.protocol import extract_declaration

from ..prompts import messages
from ..restarts import session_cost
from ..session import ProofSession
from .expansion import ExpansionSession
from .policy import Decision, Expansion, Node, TreeSearch, TreeView

EXPANSION_NOTE = (
    "Tree-search expansion. Start from the incumbent declaration above, which "
    "is one checked proof in a host-managed search tree. Focus on the strategy "
    "card below. You may make at most {checks} checks in this call; then call "
    "finish and return your best declaration."
)


def node_code(session: ProofSession, node: int) -> tuple[str, dict]:
    """Code and evaluation of a tree node (0 is the seed)."""
    if node == 0:
        return session.seed_code, session.seed_evaluation
    record = session.checks[node - 1]
    return record["code"], record["evaluation"]


def tree_view(log: list[dict], session: ProofSession) -> TreeView:
    """Rebuild the tree from completed log entries and the host ledger."""
    nodes = [Node(0, None, None, session.seed_evaluation["scores"]["combined_pct"])]
    expansions = []
    for index, entry in enumerate(log):
        if entry["action"] != "expand" or "last_check" not in entry:
            continue
        children = []
        for number in range(entry["first_check"] + 1, entry["last_check"] + 1):
            record = session.checks[number - 1]
            score = (
                record["evaluation"]["scores"]["combined_pct"]
                if record["all_versions_passed"]
                else None
            )
            nodes.append(Node(number, entry["parent"], index, score))
            children.append(number)
        expansions.append(
            Expansion(
                index,
                entry["parent"],
                entry["card"],
                entry["cost_usd"],
                entry["status"],
                tuple(children),
            )
        )
    return TreeView(tuple(nodes), tuple(expansions))


def expansion_messages(
    pack: dict, session: ProofSession, decision: Decision, max_checks: int
):
    code, evaluation = node_code(session, decision.parent)
    request = messages(pack, seed=(code, evaluation))
    if decision.card is None:
        return request
    cards = {c["id"]: c for c in read_cards()}
    note = {
        "note": EXPANSION_NOTE.format(checks=max_checks),
        "focus_strategy_card": cards[decision.card],
    }
    request[1]["content"] += "\n" + json.dumps(note, ensure_ascii=False, indent=2)
    return request


def read_cards() -> list[dict]:
    return read(ROOT / "prompts/strategy_bank.json")["cards"]


def run_tree(
    folder: Path,
    pack: dict,
    config: dict,
    model: str,
    effort: str,
    session: ProofSession,
    generate: Callable[[Path, list[dict], ExpansionSession], dict],
) -> tuple[list[dict], list[dict]]:
    """Run or resume the tree search; return generations and the decision log."""
    settings = TreeSearch.from_record(config["tree"])
    path = folder / "tree.json"
    log = read(path) if path.exists() else []
    generations = []
    for index in range(settings.policy.max_expansions + 1):
        if index < len(log):
            entry = log[index]
        else:
            decision = settings.policy.choose(tree_view(log, session))
            entry = {
                "action": decision.action,
                "reason": decision.reason,
                "parent": decision.parent,
                "card": decision.card,
                "messages": (
                    expansion_messages(pack, session, decision, settings.max_checks)
                    if decision.action == "expand"
                    else None
                ),
            }
            log.append(entry)
            write_json(path, log)
        if entry["action"] != "expand":
            break
        attempt = folder / f"attempt_{index:02d}"
        if "first_check" not in entry:
            entry["first_check"] = len(session.checks)
            write_json(path, log)
        if not (attempt / "generation.json").exists():
            session.finished = None
            (session.folder / "finished.json").unlink(missing_ok=True)
        parent_code, _ = node_code(session, entry["parent"])
        view = ExpansionSession(session, parent_code, settings.max_checks)
        generation = generate(attempt, entry["messages"], view)
        generations.append(generation)
        if generation["status"] == "received" and "last_check" not in entry:
            try:
                final = extract_declaration(
                    generation["content"], generation["finish_reason"]
                )
            except ValueError:
                final = generation["content"]
            session.check(final, origin="final_harness")
        if "last_check" not in entry:
            entry.update(
                last_check=len(session.checks),
                status=generation["status"],
                cost_usd=session_cost(config, model, effort, generation),
            )
            write_json(path, log)
    return generations, log
