"""Bounded, model-free tactic discovery in the original Lean goal states.

Discovery is not scoring. A temporary Lean elaborator saves the complete tactic
state, tries every menu entry on the same main goal, restores the state, and
continues the original proof. Only materialized edits leave this module; the
caller must recompile the complete declaration with the ordinary evaluator.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
import re
import subprocess
import time
import uuid

from .api import EvaluationNotReady
from .lean_backend import MEASUREMENT_WRAPPER, _run, _source
from .optimizer import Edit, analyze


CHEAP_MENU = (
    "rfl", "assumption", "trivial", "contradiction", "omega", "ring", "abel",
    "norm_num", "norm_cast", "positivity", "linarith", "nlinarith", "tauto",
    "decide", "simp", "simp_all", "dsimp", "aesop", "grind",
)
SEARCH_MENU = ("exact?", "aesop?", "grind?")
MENUS = {"tactic_menu": CHEAP_MENU, "library_search": SEARCH_MENU}

# Parse menu tactics at runtime: a project without Mathlib can still use the
# core subset. Unsupported syntax is an explicit outcome, not an analysis error.
PROBE_TEMPLATE = r'''
open Lean Elab Tactic in
elab "proof_search_probe " site:num : tactic => do
  let saved ← Tactic.saveState
  let mut results : Array Json := #[]
  for name in __MENU__ do
    saved.restore true
    Core.resetMessageLog
    let mut status := "failed"
    let mut detail := ""
    let mut suggestions : Array String := #[]
    let start ← IO.getNumHeartbeats
    match Parser.runParserCategory (← getEnv) `tactic name with
    | .error e => status := "unavailable"; detail := e
    | .ok stx =>
      let outcome ← tryCatchRuntimeEx (do
        let g ← getMainGoal
        setGoals [g]
        withOptions (fun o => o.set `maxHeartbeats (__HEARTBEATS__ : Nat)) <|
            withTheReader Core.Context (fun ctx => { ctx with maxHeartbeats := __HEARTBEATS__ * 1000 }) <|
              withCurrHeartbeats do
                withoutRecover <| evalTactic stx
        let goalProof ← instantiateMVars (mkMVar g)
        let goals ← getUnsolvedGoals
        let outcomeStatus :=
          if goalProof.hasSorry then "rejected_sorry"
          else if goalProof.hasExprMVar then "unsolved"
          else if goals.isEmpty then "solved" else "unsolved"
        let mut outcomeSuggestions : Array String := #[]
        for msg in (← Core.getMessageLog).toList do
          outcomeSuggestions := outcomeSuggestions.push (← msg.data.toString)
        pure (outcomeStatus, "", outcomeSuggestions))
        (fun e => do pure ("failed", ← e.toMessageData.toString, (#[] : Array String)))
      status := outcome.1
      detail := outcome.2.1
      suggestions := outcome.2.2
    let finish ← IO.getNumHeartbeats
    results := results.push <| Json.mkObj [
      ("tactic", toJson name), ("status", toJson status),
      ("detail", toJson detail), ("suggestions", toJson suggestions),
      ("discovery_heartbeat_allocations", toJson (finish - start))]
  saved.restore true
  logInfo m!"PROOF_SEARCH:{(Json.mkObj [("site", toJson site.getNat), ("results", toJson results)]).compress}"
'''


@dataclass(frozen=True)
class Site:
    start: int
    end: int
    kind: str
    probe_at: int
    syntax_kind: str

    def replacement(self, tactic):
        return "by " + tactic if self.kind == "by_block" else tactic

    def record(self):
        return asdict(self)


def candidate_sites(code, analysis):
    """Enumerate syntax-backed by-blocks and single-line tactic leaves.

    An interleaved ordering exposes both block contraction and replacement of
    expensive closing tactics under small budgets. Offsets refer to the exact
    incumbent. A site is only a proposal: a leaf need not close its goal, and a
    block need not be replaceable by the chosen menu.
    """
    nodes = analysis["nodes"]
    by_blocks, leaves = {}, {}
    expensive = ("nlinarith", "linarith", "omega", "simp", "ring", "norm_num", "aesop", "grind")
    leaf_prefix = re.compile(r"(?:exact|assumption|rfl|trivial|contradiction|omega|ring(?:_nf)?|abel|"
                             r"norm_num|norm_cast|positivity|n?linarith|tauto|decide|grind|aesop|"
                             r"simp(?:_all)?|dsimp)(?:[!?])?(?![\w'])")
    for node in nodes:
        start, end = node["start"], node["end"]
        original = code[start:end]
        path = tuple(node["path"])
        if node["kind"] == "Lean.Parser.Term.byTactic":
            sequences = [n for n in nodes if n["kind"] == "Lean.Parser.Tactic.tacticSeq"
                         and tuple(n["path"][:len(path)]) == path]
            if not sequences:
                continue
            first = min(sequences, key=lambda n: len(n["path"]))["start"]
            by_blocks[(start, end)] = Site(start, end, "by_block", first, node["kind"])
        elif ("Tactic" in node["kind"] or node["kind"].startswith("tactic")) and "\n" not in original:
            if not leaf_prefix.match(original) or "<;>" in original or ";" in original:
                continue
            # Match a complete tactic node, not a nested lemma/term argument.
            if any(n["start"] == start and n["end"] == end
                   and len(n["path"]) < len(path) and "Tactic" in n["kind"] for n in nodes):
                continue
            leaves[(start, end)] = Site(start, end, "tactic", start, node["kind"])
    blocks = sorted(by_blocks.values(), key=lambda s: (s.end - s.start > 2000, -(s.end - s.start), s.start))
    single = sorted(leaves.values(), key=lambda s: (
        not code[s.start:s.end].startswith(expensive), -(s.end - s.start), s.start))
    # Interleave rather than allowing a long theorem's nested blocks or its many
    # arithmetic leaves to consume the entire discovery budget.
    out = []
    for i in range(max(len(blocks), len(single))):
        if i < len(blocks):
            out.append(blocks[i])
        if i < len(single):
            out.append(single[i])
    return out


def instrument(code, sites):
    """Insert probes without shifting the indentation of existing tactics."""
    insertions = defaultdict(list)
    for index, site in enumerate(sites):
        if site.kind == "by_block":
            # A new line at the original first tactic's column preserves Lean's
            # layout rules, including an originally single-line `by` proof.
            column = site.probe_at - (code.rfind("\n", 0, site.probe_at) + 1)
            insertions[site.probe_at].append((0, f"proof_search_probe {index}\n" + " " * column))
        else:
            insertions[site.start].append((1, f"(proof_search_probe {index}; "))
            insertions[site.end].append((-1, ")"))
    for position in sorted(insertions, reverse=True):
        text = "".join(value for _, value in sorted(insertions[position], key=lambda p: p[0]))
        code = code[:position] + text + code[position:]
    return code


def materialized_suggestions(messages):
    """Accept one complete 'Try this' edit; never return a search tactic.

    Aesop can print a multiline sequence. Preserve its internal indentation and
    enclose it in `first | ...` so it is one tactic at an inline replacement site.
    Ambiguous 'Try these' output is intentionally skipped, as are diagnostics
    containing placeholders or another query tactic.
    """
    out = []
    for message in messages:
        if not message.startswith("Try this:"):
            continue
        suggestion = message.removeprefix("Try this:").strip()
        suggestion = re.sub(r"^\[apply\]\s*", "", suggestion)
        if (not suggestion or "[apply]" in suggestion or "⊢" in suggestion
                or re.search(r"\b(?:sorry|admit)\b|\b(?:exact|apply|simp_all|simp|dsimp|aesop|grind|rw|simpa)\?", suggestion)):
            continue
        if "\n" in suggestion:
            # Each original continuation line is relative to the first printed
            # tactic. Dedent uniformly before nesting under the branch.
            lines = suggestion.splitlines()
            nonempty = [len(s) - len(s.lstrip()) for s in lines[1:] if s.strip()]
            indent = min(nonempty, default=0)
            lines = [lines[0]] + [s[indent:] if s.strip() else "" for s in lines[1:]]
            suggestion = "first |\n" + "\n".join("  " + s for s in lines)
        if suggestion not in out:
            out.append(suggestion)
    return out


def checked_outcome(outcome):
    """Classify recovery holes and cooperative timeouts before exporting edits."""
    outcome = dict(outcome)
    if outcome["status"] == "failed" and "maximum number of heartbeats" in outcome["detail"]:
        outcome["status"] = "heartbeat_limit"
    # Some grind? versions put their recovery sorry in an auxiliary declaration,
    # beyond Expr.hasSorry's direct traversal. Their warning/suggestion exposes
    # it. Final declaration verification still checks transitive axioms.
    if outcome["status"] == "solved" and any(
            re.search(r"\b(?:sorry|admit)\b", message) for message in outcome.get("suggestions", [])):
        outcome["status"] = "rejected_sorry"
    return outcome


def _format_replacement(site, tactic, code):
    replacement = site.replacement(tactic)
    if "\n" in replacement:
        # Continuation lines must remain beneath the replacement's initial
        # column when the discovered tactic is nested in a declaration.
        column = site.start - (code.rfind("\n", 0, site.start) + 1)
        if site.kind == "by_block":
            column += len("by ")
        replacement = replacement.replace("\n", "\n" + " " * column)
    return replacement


def discover(evaluator, row, code, method="tactic_menu", *, max_sites=12,
             site_offset=0, max_heartbeats=5000, timeout=120):
    """Return per-site alternative Edit groups and every discovery outcome.

    ``max_heartbeats`` is a per-entry discovery bound in Lean's public heartbeat
    units. ``timeout`` bounds the whole temporary process independently of the
    scoring evaluator's timeout/fingerprint. These options never enter an edit.
    ``site_offset`` supports successive bounded sweeps of the stable site order.
    Failed/partial discovery produces diagnostics and no unverified fallback.
    """
    if method not in MENUS:
        raise ValueError(f"Unknown tactic discovery method: {method}")
    if max_sites < 1 or site_offset < 0 or max_heartbeats < 1 or timeout <= 0:
        raise ValueError("Discovery budgets must be positive and site_offset nonnegative")
    analysis = analyze(evaluator, row, code)
    available = candidate_sites(code, analysis)
    sites = available[site_offset:site_offset + max_sites]
    if not sites:
        return {"groups": [], "diagnostics": [{"kind": "site_coverage", "available": len(available),
                 "selected": 0, "site_offset": site_offset}], "analysis_requests": 1, "status": "ok"}
    version = next(iter(row["version_info"][0]))
    project, _, context_key = evaluator._context(row, version)
    menu = MENUS[method]
    support = PROBE_TEMPLATE.replace("__MENU__", "#[" + ", ".join(json.dumps(x) for x in menu) + "]")
    support = support.replace("__HEARTBEATS__", str(max_heartbeats))
    options = {"method": method, "max_sites": max_sites, "site_offset": site_offset,
               "max_heartbeats": max_heartbeats, "timeout": timeout}
    # Include this whole module: changes to site selection, instrumentation, or
    # suggestion parsing must not silently reuse an old discovery result.
    from pathlib import Path
    implementation = Path(__file__).read_text()
    key = hashlib.sha256((context_key + code + implementation + json.dumps(options, sort_keys=True)).encode()).hexdigest()
    cached = evaluator.store.read("tactic_discovery", key)
    if cached is not None:
        return {**cached, "groups": [[Edit(**e) for e in group] for group in cached["groups"]], "cached": True}
    source, _ = _source(row, code, project, uuid.uuid4().hex)
    prefix = source.split("\n#proof_eval_measure ", 1)[0]
    prefix = prefix.replace(MEASUREMENT_WRAPPER, MEASUREMENT_WRAPPER + support, 1)
    instrumented = instrument(code, sites)
    source = prefix + "\nset_option Elab.async false in\nset_option maxHeartbeats 0 in\n" + instrumented + "\n"
    path = project / f"_ProofEval_{uuid.uuid4().hex}.lean"
    path.write_text(source)
    started = time.monotonic()
    diagnostics = [{"kind": "site_coverage", "available": len(available), "selected": len(sites),
                    "site_offset": site_offset, "sites": [s.record() for s in sites], **options}]
    timed_out = False
    try:
        proc = _run([evaluator.backend.lake, "env", "lean", "--json", path.name], project, timeout)
        stdout = proc.stdout
        returncode = proc.returncode
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        returncode, stderr = None, "Discovery process timed out"
    finally:
        path.unlink(missing_ok=True)
    groups = [[] for _ in sites]
    seen_sites = set()
    for line in stdout.splitlines():
        try:
            message = json.loads(line)
        except ValueError:
            continue
        data = message.get("data", "")
        if not data.startswith("PROOF_SEARCH:"):
            if message.get("severity") == "error":
                diagnostics.append({"kind": "discovery_error", "message": data})
            continue
        record = json.loads(data.removeprefix("PROOF_SEARCH:"))
        index = record["site"]
        if not isinstance(index, int) or not 0 <= index < len(sites):
            raise EvaluationNotReady("Discovery returned an unknown site")
        seen_sites.add(index)
        site = sites[index]
        for outcome in record["results"]:
            outcome = checked_outcome(outcome)
            diagnostics.append({"kind": "tactic_outcome", "site": index, **outcome})
            if outcome["status"] != "solved":
                continue
            alternatives = ([outcome["tactic"]] if method == "tactic_menu"
                            else materialized_suggestions(outcome["suggestions"]))
            for tactic in alternatives:
                replacement = _format_replacement(site, tactic, code)
                if replacement == code[site.start:site.end]:
                    continue
                edit = Edit(site.start, site.end, replacement, method)
                if all(e.replacement != replacement for e in groups[index]):
                    groups[index].append(edit)
    for index in range(len(sites)):
        if index not in seen_sites:
            for tactic in menu:
                diagnostics.append({"kind": "tactic_outcome", "site": index, "tactic": tactic,
                                    "status": "not_observed", "detail": "Discovery did not report this site"})
    diagnostics.append({"kind": "discovery_process", "returncode": returncode, "timed_out": timed_out,
                        "stderr": stderr[:1000], "elapsed_seconds": round(time.monotonic() - started, 3)})
    # If instrumentation prevented the original declaration from compiling,
    # no probe result is evidence of a usable site. The caller receives the
    # exact diagnostics and can try a different bounded site slice.
    if returncode != 0:
        groups = [[] for _ in sites]
    status = "discovery_timeout" if timed_out else "ok" if returncode == 0 else "discovery_failed"
    result = {"groups": [[e.record() for e in g] for g in groups if g],
              "diagnostics": diagnostics, "analysis_requests": 2, "cached": False, "status": status}
    if not timed_out:
        evaluator.store.write("tactic_discovery", key, result)
    return {**result, "groups": [[Edit(**e) for e in g] for g in result["groups"]]}
