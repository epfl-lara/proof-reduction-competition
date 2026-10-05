"""Bounded observations of the supplied proof, for one-shot model context.

This module never searches for replacements, calls a model, prepares a reference,
or changes the scoring backend. It observes the original tactic state at selected
syntax-backed sites. Optional allocation counts execute the original tactic once;
they are contextual diagnostics, not the arena's whole-proof measurement.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import time
import uuid
from collections import defaultdict

from proof_eval.optimization.syntax import analyze
from proof_eval.optimization.tactics import candidate_sites
from proof_eval.verification.api import EvaluationNotReady
from proof_eval.verification.backend import MEASUREMENT_WRAPPER, _run, _source

OBSERVER = r"""
open Lean Elab Tactic in
private meta def proofContextGoals : TacticM (Array String × Nat) := do
  let goals ← getGoals
  let mut texts := #[]
  for g in goals.take __MAX_GOALS__ do
    texts := texts.push (← g.withContext do pure (← Meta.ppGoal g).pretty)
  pure (texts, goals.length)
open Lean Elab Tactic in
elab "proof_context_goals " site:num : tactic => do
  let (goals, count) ← proofContextGoals
  logInfo m!"PROOF_CONTEXT:{(Json.mkObj [("site", toJson site.getNat),
    ("before_goals", toJson goals), ("goal_count", toJson count)]).compress}"
open Lean Elab Tactic in
elab "proof_context_cost " site:num " in " tac:tactic : tactic => do
  let (goals, count) ← proofContextGoals
  let start ← IO.getNumHeartbeats
  evalTactic tac
  let finish ← IO.getNumHeartbeats
  logInfo m!"PROOF_CONTEXT:{(Json.mkObj [("site", toJson site.getNat),
    ("before_goals", toJson goals), ("goal_count", toJson count),
    ("tactic_allocations", toJson (finish - start))]).compress}"
"""


def _sha(value):
    return hashlib.sha256(
        value.encode() if isinstance(value, str) else value
    ).hexdigest()


def _truncate_goal(text, limit):
    """Preserve the target when long local hypotheses consume the text budget."""
    if len(text) <= limit:
        return text
    marker = "\n… [truncated]\n"
    if limit <= len(marker) + 10:
        return text[:limit]
    split = text.rfind("⊢")
    if split < 0:
        return text[: limit - len(marker)] + marker
    target = text[split:]
    target_budget = min(len(target), max(limit // 2, limit - 300))
    context_budget = max(0, limit - len(marker) - target_budget)
    return text[: min(split, context_budget)] + marker + target[:target_budget]


def implementation_hash():
    """Pin the observer, site selection, source builder, and coordinate logic."""
    from proof_eval.paths import PACKAGE

    return _sha(
        b"".join(
            (PACKAGE / name).read_bytes()
            for name in (
                "verification/context.py",
                "optimization/tactics.py",
                "optimization/syntax.py",
                "verification/backend.py",
            )
        )
    )


def _instrument(code, sites, measure_costs):
    """Keep original coordinates and recompute columns after each insertion.

    Avoid interpreting nested instrumentation as the cost of the original tactic:
    a leaf containing another selected observation is intentionally not measured.
    """
    measured = {
        i
        for i, site in enumerate(sites)
        if measure_costs
        and site.kind == "tactic"
        and not any(
            i != j and site.start < other.probe_at < site.end
            for j, other in enumerate(sites)
        )
    }
    insertions = defaultdict(list)
    for i, site in enumerate(sites):
        if site.kind == "by_block":
            insertions[site.probe_at].append((0, i))
        else:
            prefix = (
                f"(proof_context_cost {i} in "
                if i in measured
                else f"(proof_context_goals {i}; "
            )
            insertions[site.start].append((1, prefix))
            insertions[site.end].append((-1, ")"))
    out, cursor, column = [], 0, 0

    def append(text):
        nonlocal column
        out.append(text)
        column = len(text.rsplit("\n", 1)[-1]) if "\n" in text else column + len(text)

    for position in sorted(insertions):
        append(code[cursor:position])
        for priority, value in sorted(insertions[position], key=lambda item: item[0]):
            if priority == 0:
                append(f"proof_context_goals {value}\n" + " " * column)
            else:
                append(value)
        cursor = position
    append(code[cursor:])
    return "".join(out), measured


def _parse_observations(
    stdout, sites, code, *, measured, max_goal_chars, max_snippet_chars, max_invocations
):
    events = defaultdict(list)
    counts = defaultdict(int)
    diagnostics = []
    for line in stdout.splitlines():
        try:
            message = json.loads(line)
        except ValueError:
            continue
        data = message.get("data", "")
        if data.startswith("PROOF_CONTEXT:"):
            event = json.loads(data.removeprefix("PROOF_CONTEXT:"))
            index = event.get("site")
            if type(index) is not int or not 0 <= index < len(sites):
                raise EvaluationNotReady("Context observer returned an unknown site")
            goals = event.get("before_goals")
            goal_count = event.get("goal_count")
            if (
                not isinstance(goals, list)
                or not all(isinstance(goal, str) for goal in goals)
                or type(goal_count) is not int
                or goal_count < len(goals)
            ):
                raise EvaluationNotReady("Context observer returned invalid goals")
            raw = event.get("tactic_allocations")
            if raw is not None and (
                index not in measured or type(raw) is not int or raw < 0
            ):
                raise EvaluationNotReady(
                    "Context observer returned invalid allocation count"
                )
            counts[index] += 1
            if len(events[index]) < max_invocations:
                events[index].append(
                    {
                        "before_goals": [
                            _truncate_goal(goal, max_goal_chars) for goal in goals
                        ],
                        "goal_count": goal_count,
                        "goals_truncated": goal_count > len(goals)
                        or any(len(g) > max_goal_chars for g in goals),
                        "tactic_allocations": raw,
                        "tactic_heartbeats": raw / 1000 if raw is not None else None,
                    }
                )
        elif message.get("severity") == "error" and len(diagnostics) < 5:
            diagnostics.append(str(data)[:1000])
    out = []
    for index, site in enumerate(sites):
        snippet = code[site.start : site.end]
        first = (
            events[index][0]
            if events[index]
            else {
                "before_goals": None,
                "goal_count": None,
                "goals_truncated": False,
                "tactic_allocations": None,
                "tactic_heartbeats": None,
            }
        )
        out.append(
            {
                "site": index,
                **site.record(),
                "snippet": snippet[:max_snippet_chars],
                "snippet_truncated": len(snippet) > max_snippet_chars,
                "status": "observed" if events[index] else "not_observed",
                **first,
                "invocation_count": counts[index],
                "invocations": events[index],
                "invocations_truncated": counts[index] > len(events[index]),
                "cost_status": (
                    "measured_original_tactic"
                    if first["tactic_allocations"] is not None
                    else "not_measured"
                ),
            }
        )
    return out, diagnostics


def build_context(
    evaluator,
    row,
    code,
    max_sites=6,
    *,
    measure_costs=False,
    max_goal_chars=1500,
    max_snippet_chars=400,
    max_goals=3,
    max_invocations=2,
    timeout=None,
):
    """Return bounded JSON observations tied to the exact proof and environment.

    ``before_goals`` is the state before the supplied tactic, not an alternative
    tactic or the result of proof search. Character offsets index ``code``.
    Costs count allocation heartbeats around ``evalTactic`` of that exact leaf,
    with goal formatting outside the counted interval. They may include wrapper
    overhead and are not additive, calibrated tactic prices, or arena scores.

    The separate ``model_context`` cache includes proof/environment/implementation
    identities and every observation budget. Failed observations are explicit and
    are not cached; no reference record is read, written, or remeasured here.
    """
    budgets = (max_sites, max_goal_chars, max_snippet_chars, max_goals, max_invocations)
    if any(type(value) is not int or value < 1 for value in budgets):
        raise ValueError("Context budgets must be positive integers")
    if not isinstance(measure_costs, bool):
        raise ValueError("measure_costs must be boolean")
    timeout = evaluator.timeout if timeout is None else float(timeout)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Context timeout must be positive and finite")
    version = next(iter(row["version_info"][0]))
    options = dict(
        max_sites=max_sites,
        measure_costs=measure_costs,
        max_goal_chars=max_goal_chars,
        max_snippet_chars=max_snippet_chars,
        max_goals=max_goals,
        max_invocations=max_invocations,
        timeout=timeout,
    )
    base = {
        "schema": 1,
        "name": row["name"],
        "primary_version": version,
        "proof_sha256": _sha(code),
        "implementation_sha256": implementation_hash(),
        "options": options,
        "cached": False,
        "sites": [],
        "cost_semantics": "Original tactic allocation delta / 1000 at this state; instrumented diagnostic only, not a portable tactic price or a whole-proof score.",
    }
    started = time.monotonic()
    try:
        project, fingerprint, context_key = evaluator._context(row, version)
        key = _sha(json.dumps({"context_key": context_key, **base}, sort_keys=True))
        base.update(
            context_key=context_key, environment_fingerprint=fingerprint, cache_key=key
        )
        with evaluator.store.locked("model_context", key):
            cached = evaluator.store.read("model_context", key)
            if cached is not None:
                return {**cached, "cached": True}
            analysis = analyze(evaluator, row, code)
            available = candidate_sites(code, analysis)
            sites = available[:max_sites]
            base.update(available_sites=len(available), selected_sites=len(sites))
            if not sites:
                result = {
                    **base,
                    "status": "ok",
                    "diagnostics": [],
                    "elapsed_seconds": time.monotonic() - started,
                }
                evaluator.store.write("model_context", key, result)
                return result
            instrumented, measured = _instrument(code, sites, measure_costs)
            source, _ = _source(row, code, project, uuid.uuid4().hex)
            prefix = source.split("\n#proof_eval_measure ", 1)[0]
            support = OBSERVER.replace("__MAX_GOALS__", str(max_goals))
            prefix = prefix.replace(
                MEASUREMENT_WRAPPER, MEASUREMENT_WRAPPER + support, 1
            )
            source = (
                prefix
                + "\nset_option Elab.async false in\nset_option maxHeartbeats 0 in\n"
                + instrumented
                + "\n"
            )
            path = project / f"_ProofEval_{uuid.uuid4().hex}.lean"
            path.write_text(source)
            try:
                proc = _run(
                    [evaluator.backend.lake, "env", "lean", "--json", path.name],
                    project,
                    timeout,
                )
            finally:
                path.unlink(missing_ok=True)
            observed, diagnostics = _parse_observations(
                proc.stdout,
                sites,
                code,
                measured=measured,
                max_goal_chars=max_goal_chars,
                max_snippet_chars=max_snippet_chars,
                max_invocations=max_invocations,
            )
            _, after_fingerprint, after_key = evaluator._context(row, version)
            if (fingerprint, context_key) != (after_fingerprint, after_key):
                raise EvaluationNotReady("Project changed during context observation")
            status = "ok" if proc.returncode == 0 else "unavailable"
            if status != "ok":
                # Partially elaborated instrumentation cannot establish valid
                # original-state observations. Keep failure explicit.
                observed = [
                    {
                        **item,
                        "status": "unavailable",
                        "before_goals": None,
                        "goal_count": None,
                        "tactic_allocations": None,
                        "tactic_heartbeats": None,
                        "cost_status": "not_measured",
                        "invocations": [],
                    }
                    for item in observed
                ]
            result = {
                **base,
                "status": status,
                "sites": observed,
                "diagnostics": diagnostics,
                "returncode": proc.returncode,
                "stderr": proc.stderr[:1000],
                "elapsed_seconds": time.monotonic() - started,
            }
            if status == "ok":
                evaluator.store.write("model_context", key, result)
            return result
    except (
        EvaluationNotReady,
        subprocess.TimeoutExpired,
        OSError,
        ValueError,
        TypeError,
        KeyError,
    ) as exc:
        return {
            **base,
            "status": "unavailable",
            "diagnostics": [str(exc)[:1000]],
            "elapsed_seconds": time.monotonic() - started,
        }
