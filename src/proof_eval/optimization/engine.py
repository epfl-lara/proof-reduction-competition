"""Bounded deterministic searches sharing the arena objective and verifier.

This module never prepares references or edits project sources. Proposal methods
are separate ablations; all accepted states are fully scored declarations.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from proof_eval.optimization.syntax import (
    Edit,
    analyze,
    apply_edits,
    nonoverlapping,
    primary_upper_bound,
    score_improves,
)
from proof_eval.verification.api import EvaluationNotReady

METHOD_MODULES = {
    "wrappers": "structural",
    "facts": "structural",
    "reuse": "structural",
    "menu": "tactic_search",
    "search": "tactic_search",
    "simp_min": "lemma_minimization",
    "arith_min": "lemma_minimization",
    "rw_min": "lemma_minimization",
    "proof_theory": "proof_theory",
    "golf": "token_golf",
    "collapse": "proof_theory",
    "delete": "proof_theory",
    "consolidate": "proof_theory",
    "relax": "proof_theory",
    "lint": "optimizer",
    "simp": "optimizer",
}


LEAN_FREE_METHODS = frozenset(
    {"proof_theory", "golf", "collapse", "delete", "consolidate", "relax"}
)


@dataclass(frozen=True)
class Budget:
    rounds: int = 6
    trials: int = 64
    sites: int = 6
    min_gain: float = 0.05


def compact(result):
    out = {
        key: result[key] for key in ("status", "scores", "candidate", "primary_version")
    }
    out["per_version"] = {}
    for version, data in result["per_version"].items():
        item = {
            key: data.get(key)
            for key in (
                "status",
                "passed",
                "heartbeats",
                "heartbeat_reduction_pct",
                "cached",
                "environment_fingerprint",
                "elapsed_seconds",
            )
        }
        # Full logs remain in the evaluator cache. Retain errors and the exact
        # suggestions needed to audit decisions without repeating unrelated
        # source-file style warnings in every result.
        item["diagnostics"] = [
            m
            for m in data.get("diagnostics", [])
            if m.get("severity") == "error" or m.get("data", "").startswith("Try this:")
        ]
        out["per_version"][version] = item
    return out


def discovery(evaluator, row, code, method, budget, *, site_offset=0):
    """Return candidate edit groups, a selection policy, and discovery evidence."""
    if method in {"menu", "search"}:
        from proof_eval.optimization.tactics import discover

        discovery_method = {"menu": "tactic_menu", "search": "library_search"}[method]
        result = discover(
            evaluator,
            row,
            code,
            method=discovery_method,
            max_sites=budget.sites,
            site_offset=site_offset,
        )
        # The probe's inner lists are alternatives at one site, each one Edit.
        groups = [[edit] for site in result["groups"] for edit in site]
        return groups, "best_pool", result
    if method in {"lint", "simp"}:
        # This function owns its analysis (and, for simp, the suggestion probe).
        # Calling analyze before it would duplicate the request and undercount
        # discovery work even if the second request happened to be cached.
        from .syntax import proposals

        edits, calls = proposals(evaluator, row, code, method)
        groups = [nonoverlapping(edits)] + [[e] for e in edits] if edits else []
        return (
            groups,
            "joint_then_first",
            {"analysis_requests": calls, "diagnostics": []},
        )
    if method in LEAN_FREE_METHODS:
        # Lean-free proposals; every candidate is still compiled and scored.
        from proof_eval.optimization.proof_theory.methods import discover

        groups, policy = discover(method, row, code)
        return groups, policy, {"analysis_requests": 0, "diagnostics": []}
    if method not in METHOD_MODULES:
        raise ValueError(f"Unknown optimization method: {method}")
    analysis = analyze(evaluator, row, code)
    if method in {"wrappers", "facts", "reuse"}:
        import proof_eval.optimization.structural as structural

        function = {
            "wrappers": structural.wrappers,
            "facts": structural.local_fact_deletions,
            "reuse": structural.fact_reuse,
        }[method]
        edits = function(code, analysis)
        groups = [[e] for e in edits]
        if method in {"wrappers", "facts"} and len(edits) > 1:
            groups.insert(0, nonoverlapping(edits))
        policy = (
            "joint_then_first"
            if method in {"wrappers", "facts"}
            else "first_improvement"
        )
        return groups, policy, {"analysis_requests": 1, "diagnostics": []}
    if method in {"simp_min", "arith_min", "rw_min"}:
        from proof_eval.optimization.minimization import minimization_groups

        family = {"simp_min": "simp", "arith_min": "arithmetic", "rw_min": "rewrite"}[
            method
        ]
        return (
            minimization_groups(code, analysis, families=(family,)),
            "first_improvement",
            {"analysis_requests": 1, "diagnostics": []},
        )
    raise ValueError(f"No discovery implementation for method: {method}")


def _sha(code):
    return hashlib.sha256(code.encode()).hexdigest()


def _next_site_offset(method, evidence, offset, budget):
    """Continue a stable syntax-site sweep only when discovery reports more."""
    if method not in {"menu", "search"}:
        return None
    coverage = next(
        (
            item
            for item in evidence.get("diagnostics", [])
            if item.get("kind") == "site_coverage"
        ),
        None,
    )
    if coverage is not None and offset + budget.sites < coverage["available"]:
        return offset + budget.sites
    return None


def optimize(evaluator, row, initial, method, budget, emit, save, state=None):
    """Resume at a pending candidate, preserving trial caps and accepted states.

    A round's spans always refer to one fixed incumbent. Checkpoint pending
    alternatives and their best result before applying an accepted change.
    """
    started = time.monotonic()
    if state is None:
        before = compact(evaluator.evaluate(row["name"], initial))
        state = {
            "name": row["name"],
            "source": row["source"],
            "method": method,
            "initial": before,
            "best": before,
            "proof": initial,
            "initial_sha256": _sha(initial),
            "rounds": 0,
            "attempts": 0,
            "accepted_edits": 0,
            "accepted_transitions": 0,
            "analysis_requests": 0,
            "lean_candidate_checks": 0,
            "cache_hits": 0,
            "seen": [],
            "plan": None,
            "elapsed_seconds": 0.0,
            "stop_reason": None,
        }
        save(state)
    if (
        state["initial_sha256"] != _sha(initial)
        or state["method"] != method
        or state["name"] != row["name"]
        or state["source"] != row["source"]
    ):
        raise ValueError("Checkpoint belongs to a different input or method")
    state.setdefault("site_offset", 0)
    if (
        state["best"]["status"] != "passed"
        or state["best"]["scores"]["combined_pct"] is None
    ):
        state["stop_reason"] = "initial_evaluation_incomplete_or_failed"
    while state["stop_reason"] is None:
        if state["plan"] is None:
            if state["attempts"] >= budget.trials:
                state["stop_reason"] = "trial_limit"
                break
            if state["rounds"] >= budget.rounds:
                state["stop_reason"] = "round_limit"
                break
            try:
                groups, policy, evidence = discovery(
                    evaluator,
                    row,
                    state["proof"],
                    method,
                    budget,
                    site_offset=state["site_offset"],
                )
            except EvaluationNotReady as exc:
                emit(
                    {
                        "kind": "discovery_error",
                        "round": state["rounds"],
                        "message": str(exc),
                    }
                )
                state["stop_reason"] = "discovery_unavailable"
                break
            state["analysis_requests"] += evidence.get("analysis_requests", 0)
            next_offset = _next_site_offset(
                method, evidence, state["site_offset"], budget
            )
            normalized, round_seen = [], set()
            for group in groups:
                group = nonoverlapping(group)
                code = apply_edits(state["proof"], group)
                key = _sha(code)
                if (
                    code != state["proof"]
                    and key not in round_seen
                    and key not in state["seen"]
                ):
                    normalized.append([e.record() for e in group])
                    round_seen.add(key)
            emit(
                {
                    "kind": "proposal_set",
                    "round": state["rounds"],
                    "policy": policy,
                    "parent_sha256": _sha(state["proof"]),
                    "candidates": len(normalized),
                    "discovery": {k: v for k, v in evidence.items() if k != "groups"},
                }
            )
            state["rounds"] += 1
            if evidence.get("status") in {"discovery_failed", "discovery_timeout"}:
                state["stop_reason"] = "discovery_unavailable"
                break
            if not normalized:
                if next_offset is not None:
                    emit(
                        {
                            "kind": "site_batch_completed",
                            "round": state["rounds"] - 1,
                            "site_offset": state["site_offset"],
                            "next_site_offset": next_offset,
                            "outcome": "no_new_proposals",
                        }
                    )
                    state["site_offset"] = next_offset
                    save(state)
                    continue
                state["stop_reason"] = "no_new_proposals"
                break
            state["plan"] = {
                "groups": normalized,
                "cursor": 0,
                "winner": None,
                "policy": policy,
                "next_site_offset": next_offset,
            }
            save(state)
        plan = state["plan"]
        # A checkpoint can be saved after finding the first improvement but
        # before accepting it below. On resume, accept that exact winner rather
        # than accidentally evaluating a second alternative on the old parent.
        first_winner = plan["winner"] is not None and plan["policy"] in {
            "joint_then_first",
            "first_improvement",
        }
        while (
            not first_winner
            and plan["cursor"] < len(plan["groups"])
            and state["attempts"] < budget.trials
        ):
            group = [Edit(**e) for e in plan["groups"][plan["cursor"]]]
            proposal = apply_edits(state["proof"], group)
            state["attempts"] += 1
            primary = evaluator.evaluate(row["name"], proposal, versions="primary")
            bound = primary_upper_bound(primary)
            possible = (
                primary["status"] not in {"invalid", "failed"}
                and bound is not None
                and bound > state["best"]["scores"]["combined_pct"] + budget.min_gain
            )
            full = evaluator.evaluate(row["name"], proposal) if possible else primary
            for result in ([primary, full] if possible else [primary]):
                for item in result["per_version"].values():
                    if item.get("cached"):
                        state["cache_hits"] += 1
                    elif item.get("status") in {"passed", "failed", "timeout"}:
                        state["lean_candidate_checks"] += 1
            better = possible and score_improves(state["best"], full, budget.min_gain)
            full = compact(full)
            emit(
                {
                    "kind": "candidate",
                    "round": state["rounds"] - 1,
                    "trial": state["attempts"],
                    "parent_sha256": _sha(state["proof"]),
                    "proof": proposal,
                    "edits": [e.record() for e in group],
                    "evaluation": full,
                    "primary_upper_bound": bound,
                    "all_versions_requested": possible,
                    "improves_incumbent": better,
                }
            )
            if better and (
                plan["winner"] is None
                or full["scores"]["combined_pct"]
                > plan["winner"]["result"]["scores"]["combined_pct"]
            ):
                plan["winner"] = {
                    "proof": proposal,
                    "result": full,
                    "edits": [e.record() for e in group],
                    "trial": state["attempts"],
                }
            plan["cursor"] += 1
            state["seen"].append(_sha(proposal))
            save(state)
            if better and plan["policy"] in {"joint_then_first", "first_improvement"}:
                break
        winner = plan["winner"]
        if winner is not None:
            state["proof"], state["best"] = winner["proof"], winner["result"]
            state["site_offset"] = 0  # Accepted text has a new syntax-site order.
            state["accepted_edits"] += len(winner["edits"])
            state["accepted_transitions"] += 1
            emit(
                {
                    "kind": "accepted",
                    "round": state["rounds"] - 1,
                    "trial": winner["trial"],
                    "score": state["best"]["scores"]["combined_pct"],
                    "edits": winner["edits"],
                }
            )
        elif (
            state["attempts"] < budget.trials
            and plan.get("next_site_offset") is not None
        ):
            emit(
                {
                    "kind": "site_batch_completed",
                    "round": state["rounds"] - 1,
                    "site_offset": state["site_offset"],
                    "next_site_offset": plan["next_site_offset"],
                    "outcome": "no_improving_proposal",
                }
            )
            state["site_offset"] = plan["next_site_offset"]
        else:
            state["stop_reason"] = (
                "trial_limit"
                if state["attempts"] >= budget.trials
                else "no_improving_proposal"
            )
        state["plan"] = None
        save(state)
    state["elapsed_seconds"] += time.monotonic() - started
    save(state)
    out = {
        k: v
        for k, v in state.items()
        if k not in {"seen", "plan", "best", "initial_sha256"}
    }
    out.update(
        final=state["best"],
        changed=_sha(state["proof"]) != _sha(initial),
        elapsed_seconds=round(state["elapsed_seconds"], 3),
    )
    return out
