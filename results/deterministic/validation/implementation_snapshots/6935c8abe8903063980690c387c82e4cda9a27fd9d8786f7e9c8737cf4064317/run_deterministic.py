"""Run one model-free optimization stage with durable, per-problem evidence.

Prepare references with process_benchmark.py first. No model calls, reference
measurements, environment setup, or submissions happen in this script.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import time

from proof_eval import Evaluator
from proof_eval.api import EvaluationNotReady
from proof_eval.optimizer import (
    analyze, apply_edits, deletion_edits, primary_upper_bound,
    score_improves, simp_probes, suggestion_edit,
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(path)


def compact(result):
    """Keep component scores and diagnostics; baseline export holds full pins."""
    out = {key: result[key] for key in ("status", "scores", "candidate", "primary_version")}
    out["per_version"] = {
        v: {key: d.get(key) for key in ("status", "passed", "heartbeats", "heartbeat_reduction_pct",
                                         "cached", "environment_fingerprint", "elapsed_seconds", "diagnostics")}
        for v, d in result["per_version"].items()
    }
    return out


def proposals(evaluator, row, code, method):
    analysis = analyze(evaluator, row, code)
    if method == "lint":
        return deletion_edits(code, analysis), 1
    probes = simp_probes(code, analysis)
    if not probes:
        return [], 1
    instrumented = apply_edits(code, probes)
    suggestions = analyze(evaluator, row, instrumented)
    edits = []
    shift = 0
    for probe in probes:
        shifted = type(probe)(probe.start + shift, probe.end + shift, probe.replacement, probe.reason)
        edit = suggestion_edit(instrumented, shifted, suggestions)
        if edit is not None:
            edits.append(type(edit)(probe.start, probe.end, edit.replacement, edit.reason))
        shift += len(probe.replacement) - (probe.end - probe.start)
    return edits, 2


def optimize(evaluator, row, initial, method, max_rounds, max_trials, min_gain, emit):
    started = time.monotonic()
    before = evaluator.evaluate(row["name"], initial)
    code, best = initial, before
    attempts = accepted = analysis_calls = 0
    stop_reason = "round_limit"
    rounds = 0
    if before["status"] != "passed" or before["scores"]["combined_pct"] is None:
        stop_reason = "initial_evaluation_incomplete_or_failed"
    else:
        for round_index in range(max_rounds):
            rounds += 1
            try:
                edits, calls = proposals(evaluator, row, code, method)
                analysis_calls += calls
            except EvaluationNotReady as exc:
                emit({"kind": "analysis_error", "round": round_index, "message": str(exc)})
                stop_reason = "analysis_unavailable"
                break
            edits = [e for e in edits if e.apply(code) != code]
            emit({"kind": "proposal_set", "round": round_index, "count": len(edits), "edits": [e.record() for e in edits]})
            if not edits:
                stop_reason = "no_proposals"
                break
            # Test a joint change first. If it fails or regresses, test individual
            # alternatives on this exact same incumbent, largest spans first.
            groups = [edits]
            if len(edits) > 1:
                groups.extend([[e] for e in sorted(edits, key=lambda e: (-(e.end - e.start), e.start))])
            winner = None
            for group_index, group in enumerate(groups):
                if attempts >= max_trials:
                    stop_reason = "trial_limit"
                    break
                proposal = apply_edits(code, group)
                if proposal == code:
                    continue
                attempts += 1
                primary = evaluator.evaluate(row["name"], proposal, versions="primary")
                bound = primary_upper_bound(primary)
                possible = (primary["status"] not in {"invalid", "failed"} and bound is not None
                            and bound > best["scores"]["combined_pct"] + min_gain)
                full = evaluator.evaluate(row["name"], proposal) if possible else primary
                improves = possible and score_improves(best, full, min_gain)
                event = {"kind": "candidate", "round": round_index, "trial": attempts,
                         "parent_sha256": hashlib.sha256(code.encode()).hexdigest(),
                         "proof": proposal, "edits": [e.record() for e in group],
                         "primary_upper_bound": bound, "all_versions_requested": possible,
                         "improves_incumbent": improves, "evaluation": compact(full)}
                emit(event)
                if improves and (winner is None or full["scores"]["combined_pct"] > winner[1]["scores"]["combined_pct"]):
                    winner = proposal, full, group, attempts
                    # Joint application succeeded; rediscover on the changed code.
                    # Single alternatives are a fallback, not a complete-menu pool.
                    if group_index == 0:
                        break
            if winner is None:
                if stop_reason != "trial_limit":
                    stop_reason = "no_improving_proposal"
                break
            code, best, group, trial = winner
            accepted += len(group)
            emit({"kind": "accepted", "round": round_index, "trial": trial,
                  "score": best["scores"]["combined_pct"], "edits": [e.record() for e in group]})
            if attempts >= max_trials:
                stop_reason = "trial_limit"
                break
    return {"name": row["name"], "source": row["source"], "proof": code,
            "changed": code != initial, "initial": compact(before), "final": compact(best),
            "attempts": attempts, "accepted_edits": accepted, "analysis_requests": analysis_calls,
            "rounds": rounds, "stop_reason": stop_reason,
            "elapsed_seconds": round(time.monotonic() - started, 3)}


def aggregate(records, count):
    fields = ("length_reduction_pct", "heartbeat_reduction_pct", "compatibility_pct", "combined_pct")
    complete = [r for r in records if r["final"]["status"] in {"passed", "failed", "invalid"}
                and r["final"]["scores"]["combined_pct"] is not None]
    def mean(where, field):
        return sum(r[where]["scores"][field] for r in complete) / len(complete) if complete else None
    before = {f: mean("initial", f) for f in fields}
    after = {f: mean("final", f) for f in fields}
    all_complete = len(complete) == count
    return {"benchmark_problems": count, "recorded_problems": len(records), "fully_scored_problems": len(complete),
            "changed_problems": sum(r["changed"] for r in records),
            "attempts": sum(r["attempts"] for r in records),
            "measured_subset_initial_mean": before, "measured_subset_final_mean": after,
            "measured_subset_delta_pp": {f: after[f] - before[f] if complete else None for f in fields},
            "full_benchmark_combined_pct": after["combined_pct"] if all_complete else None,
            "full_benchmark_delta_pp": after["combined_pct"] - before["combined_pct"] if all_complete else None,
            "unscored_names": [r["name"] for r in records if r not in complete]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=("lint", "simp"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path, help="Previous stage candidates.jsonl; otherwise original proofs")
    parser.add_argument("--dataset", default="data/benchmark_data_warmup.jsonl")
    parser.add_argument("--environments", default="environments.local.json")
    parser.add_argument("--cache", default=".proof-eval")
    parser.add_argument("--name", action="append")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--max-trials", type=int, default=32)
    parser.add_argument("--min-gain", type=float, default=0.05, help="Minimum combined-score improvement, percentage points")
    args = parser.parse_args()
    if args.workers < 1 or args.max_rounds < 1 or args.max_trials < 1 or not 0 <= args.min_gain < 100:
        parser.error("Positive round/trial budgets and a finite margin in [0,100) are required")
    evaluator = Evaluator(args.dataset, args.environments, args.cache)
    names = args.name or evaluator.dataset.names
    initial = {name: evaluator.dataset.get(name)["src"] for name in evaluator.dataset.names}
    if args.input:
        supplied = [json.loads(line) for line in args.input.read_text().splitlines() if line.strip()]
        if {r["name"] for r in supplied} != set(evaluator.dataset.names) or len(supplied) != len(initial):
            parser.error("Previous stage must contain exactly one proof per benchmark problem")
        initial.update({r["name"]: r["proof"] for r in supplied})
    args.output.mkdir(parents=True, exist_ok=True)
    lock = (args.output / ".run.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error("Another process owns this output directory")
    contexts = {}
    for name in names:
        row = evaluator.dataset.get(name)
        contexts[name] = {}
        for entry in row["version_info"]:
            version = next(iter(entry))
            try:
                contexts[name][version] = evaluator._context(row, version)[2]
            except EvaluationNotReady as exc:
                contexts[name][version] = {"unavailable": str(exc)}
    config = {"method": args.method, "max_rounds": args.max_rounds, "max_trials": args.max_trials,
              "min_gain_pp": args.min_gain, "names": names, "workers": args.workers,
              "contexts": contexts, "dataset_sha256": digest(args.dataset),
              "input_sha256": digest(args.input) if args.input else None,
              "environment_config_sha256": digest(args.environments),
              "code_sha256": {p: digest(p) for p in ("src/run_deterministic.py", "src/proof_eval/optimizer.py", "src/proof_eval/lean_backend.py")}}
    config_path = args.output / "config.json"
    if config_path.exists() and json.loads(config_path.read_text()) != config:
        parser.error("Output directory belongs to a different configuration; choose a new folder")
    write_json(config_path, config)
    write_json(args.output / "run.json", {"started_at": datetime.now(timezone.utc).isoformat(), "status": "running"})
    def work(name):
        row = evaluator.dataset.get(name)
        key = hashlib.sha256(name.encode()).hexdigest()[:16]
        path = args.output / f"problem_{key}.json"
        if path.exists():
            result = json.loads(path.read_text())
        else:
            with (args.output / f"trials_{key}.jsonl").open("a") as log:
                def emit(event):
                    log.write(json.dumps({"name": name, **event}, ensure_ascii=False, allow_nan=False) + "\n")
                    log.flush()
                result = optimize(evaluator, row, initial[name], args.method, args.max_rounds, args.max_trials, args.min_gain, emit)
            write_json(path, result)
        print(json.dumps({"name": name, "changed": result["changed"], "scores": result["final"]["scores"], "stop": result["stop_reason"]}), flush=True)
        return result
    records = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(work, names):
            records.append(result)
            initial[result["name"]] = result["proof"]
            # Preserve every row and its original fallback, even in partial runs.
            temporary = args.output / "candidates.tmp"
            temporary.write_text("".join(json.dumps({"name": n, "proof": initial[n]}, ensure_ascii=False) + "\n" for n in evaluator.dataset.names))
            temporary.replace(args.output / "candidates.jsonl")
            write_json(args.output / "summary.json", aggregate(records, len(evaluator.dataset.names)))
    write_json(args.output / "run.json", {"finished_at": datetime.now(timezone.utc).isoformat(), "status": "finished"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
