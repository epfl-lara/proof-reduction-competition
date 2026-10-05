"""One fixed deterministic cleanup after saved correctness-only model repair.

No model calls or reference preparation. Controls and all valid final proposals
share the same bounded optimizer and a proof-keyed cache. Full-check eligibility
is stricter than the frozen optimizer's competition score: every required Lean
version must pass. Raw evaluator evidence remains unmodified in policy events.
"""
from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path
import time

from proof_eval import Evaluator
from proof_eval.experiments import Budget, optimize
from proof_eval.metrics import validate_candidate
from proof_eval.one_shot import fingerprint
from run_deterministic import digest, write_json
from run_repair_matrix import check_references
from validity_feedback import all_versions_passed


ROOT = Path(__file__).resolve().parent.parent
# Same ordered portfolio as run_deterministic_batch.METHODS; importing that CLI
# would pull its unrelated reporting dependencies into this frozen runtime.
METHODS = ("lint", "simp", "wrappers", "facts", "reuse", "menu", "search",
           "simp_min", "arith_min", "rw_min")
BUDGET = Budget(rounds=3, trials=32, sites=6, min_gain=0.05)
EXTRA_CODE = ("src/run_combined_matrix.py", "src/run_repair_matrix.py",
              "src/run_validity_repair.py", "src/validity_feedback.py")
COUNTERS = ("attempts", "analysis_requests", "lean_candidate_checks", "cache_hits",
            "accepted_transitions", "elapsed_seconds")
COMPLETE_STOPS = {"no_new_proposals", "no_improving_proposal", "trial_limit", "round_limit"}
ACTIVE_STATUSES = {"running", "waiting_for_initial_results"}


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def sha(code):
    return hashlib.sha256(code.encode()).hexdigest()


def job_key(name, proof):
    return fingerprint({"name": name, "proof_sha256": sha(proof)})


def versions(row):
    return [version for item in row["version_info"] for version in item]


def score(evaluation):
    value = evaluation.get("scores", {}).get("combined_pct")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("A finite combined score is required for selection")
    return value


def require_valid(evaluation, row, proof=None):
    if not all_versions_passed(evaluation, versions(row)):
        raise ValueError("Proof did not pass the exact required version set: " + row["name"])
    if evaluation.get("status") != "passed":
        raise ValueError("Valid proof lacks a complete authoritative score: " + row["name"])
    score(evaluation)
    if proof is not None and evaluation.get("candidate", {}).get("code_sha256") != sha(validate_candidate(row, proof)[0]):
        raise ValueError("Evaluation/proof identity mismatch: " + row["name"])


def append_event(path, event):
    with path.open("a") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()


class AllVersionsEvaluator:
    """Eligibility adapter, never a mutation of the evaluator or its cache."""

    def __init__(self, evaluator, required, emit):
        self.evaluator, self.required, self.emit = evaluator, list(required), emit
        self.latest = {}

    def __getattr__(self, name):
        return getattr(self.evaluator, name)

    def evaluate(self, name, code, *, versions="all"):
        raw = self.evaluator.evaluate(name, code, versions=versions)
        if versions != "all":
            return raw
        eligible = raw.get("status") == "passed" and all_versions_passed(raw, self.required)
        exposed = deepcopy(raw)
        if raw.get("status") == "passed" and not eligible:
            exposed["status"] = "policy_compatibility_rejected"
        event = {"kind": "all_version_eligibility", "name": name, "proof_sha256": sha(code),
                 "required_versions": self.required, "eligible": eligible,
                 "optimizer_status": exposed.get("status"), "authoritative_status": raw.get("status"),
                 "reason": None if eligible else "exact_required_versions_not_all_passed_or_score_unavailable",
                 "evaluation": raw}
        self.latest[sha(code)] = event
        self.emit(event)
        return exposed


def cleanup_proof(*, evaluator, row, proof, folder, provenance, optimize_fn=optimize, guard=None):
    """Run/resume ten bounded methods once, retaining checkpoints and raw checks.

    ``provenance`` must identify the dataset, contexts, reference records and
    implementation. The matrix supplies a read-only guard before each method.
    Incomplete discovery is terminal evidence for this invocation, never a claim
    that the full portfolio found no improvement. Reusing a completed job makes
    no evaluator calls. A crashed method resumes its exact saved optimizer state.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    spec = {"schema_version": 1, "name": row["name"], "row_sha256": fingerprint(row),
            "input_proof_sha256": sha(proof), "methods": list(METHODS), "budget": asdict(BUDGET),
            "required_versions": versions(row), "provenance": provenance}
    with (folder / ".job.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        config = folder / "job_config.json"
        if config.exists() and read(config) != spec:
            raise ValueError("Cleanup job configuration changed")
        write_json(config, spec)
        if (folder / "result.json").exists():
            result = read(folder / "result.json")
            require_valid(result["evaluation"], row, result["proof"])
            if result["input_proof_sha256"] != sha(proof) or result["job_config_sha256"] != fingerprint(spec):
                raise ValueError("Completed cleanup identity changed")
            for relative, expected in result["stage_result_sha256"].items():
                if digest(folder / relative) != expected:
                    raise ValueError("Completed cleanup method evidence changed")
            return result
        if guard:
            guard()
        initial_path = folder / "initial_evaluation.json"
        initial = read(initial_path) if initial_path.exists() else evaluator.evaluate(row["name"], proof, versions="all")
        require_valid(initial, row, proof)
        if not initial_path.exists():
            write_json(initial_path, initial)
        (folder / "input.lean").write_text(proof)
        adapter = AllVersionsEvaluator(evaluator, versions(row), lambda event: append_event(folder / "policy_events.jsonl", event))
        code, stages = proof, []
        for index, method in enumerate(METHODS, 1):
            if guard:
                guard()
            stage = folder / "stages" / f"{index:02d}_{method}"
            stage.mkdir(parents=True, exist_ok=True)
            stage_config = {"method": method, "input_sha256": sha(code), "job_config_sha256": fingerprint(spec)}
            if (stage / "config.json").exists() and read(stage / "config.json") != stage_config:
                raise ValueError("Cleanup method input changed")
            write_json(stage / "config.json", stage_config)
            if (stage / "result.json").exists():
                result = read(stage / "result.json")
            else:
                checkpoint = stage / "checkpoint.json"
                def emit(event):
                    if event.get("kind") == "candidate" and event.get("all_versions_requested"):
                        policy = adapter.latest.get(sha(event["proof"]))
                        if policy is not None:
                            event = {**event, "eligibility_policy": {key: policy[key] for key in
                                ("eligible", "optimizer_status", "authoritative_status", "reason")},
                                "authoritative_evaluation": policy["evaluation"]}
                    append_event(stage / "trials.jsonl", event)
                result = optimize_fn(adapter, row, code, method, BUDGET, emit,
                                     lambda state: write_json(checkpoint, state),
                                     state=read(checkpoint) if checkpoint.exists() else None)
                require_valid(result["final"], row, result["proof"])
                write_json(stage / "result.json", result)
            require_valid(result["final"], row, result["proof"])
            require_valid(result["initial"], row, code)
            if result["method"] != method or result["name"] != row["name"] or result["source"] != row["source"]:
                raise ValueError("Cleanup method result identity changed")
            if score(result["final"]) < score(result["initial"]):
                raise ValueError("Cleanup method regressed its valid input")
            stages.append(result)
            code = result["proof"]
        if guard:
            guard()
        final = evaluator.evaluate(row["name"], code, versions="all")
        require_valid(final, row, code)
        incomplete = [stage["method"] for stage in stages if stage.get("stop_reason") not in COMPLETE_STOPS]
        result = {"name": row["name"], "source": row["source"], "input_proof": proof,
            "input_proof_sha256": sha(proof), "proof": code, "initial_evaluation": initial, "evaluation": final,
            "all_versions_valid": True, "status": "incomplete_discovery" if incomplete else "complete",
            "incomplete_methods": incomplete, "job_config_sha256": fingerprint(spec),
            "stage_result_sha256": {str(path.relative_to(folder)): digest(path) for path in sorted((folder / "stages").glob("*/result.json"))},
            "stages": stages, "counters": {key: sum(stage.get(key, 0) for stage in stages) for key in COUNTERS},
            "verification_accounting": "Optimizer counters exclude initial/final whole-proof validation; these checks use the existing evaluator cache.",
            "changed": code != proof}
        write_json(folder / "result.json", result)
        return result


def branch(proof, evaluation, key=None):
    result = {"proof": proof, "evaluation": evaluation}
    if key is not None:
        result["job_key"] = key
    return result


def cleanup_provenance(matrix, name):
    """The same proof-job pins are used by engineering pilots and the matrix."""
    return {"input_sha256": matrix["input_sha256"][name], "contexts": matrix["contexts"][name],
            "references_sha256": matrix["references_sha256"][name], "code_sha256": matrix["code_sha256"]}


def select_cell(*, cell, pack, repair, snapshot, control, proposal):
    """Exact maximum over eligible valid branches; never regress D1 or L."""
    d0 = branch(pack["proof"], pack["incumbent"])
    d1 = branch(control["proof"], control["evaluation"], job_key(pack["name"], pack["proof"]))
    previous = branch(repair["selected_proof"], repair["selected_evaluation"])
    raw = branch(repair["final_proof"], repair["final_evaluation"]) if repair["final_valid"] else None
    cleaned = branch(proposal["proof"], proposal["evaluation"], job_key(pack["name"], raw["proof"])) if proposal else None
    candidates = {"d1": d1, "l": previous, "d0": d0, "f": raw, "cleaned_f": cleaned}
    baseline = score(d0["evaluation"])
    eligible = []
    for label, value in candidates.items():
        if value is None:
            continue
        require_valid(value["evaluation"], pack["row"], value["proof"])
        if label in {"d0", "d1", "l"} or score(value["evaluation"]) > baseline + BUDGET.min_gain:
            eligible.append(label)
    selected = max(eligible, key=lambda label: score(candidates[label]["evaluation"]))
    chosen = candidates[selected]
    if score(chosen["evaluation"]) < max(score(d1["evaluation"]), score(previous["evaluation"])):
        raise AssertionError("Combined selection regressed an existing valid branch")
    distinct_rejected = (raw is not None and not repair["accepted"]
                         and raw["proof"].strip() != d0["proof"].strip())
    return {"name": pack["name"], "source": pack["row"]["source"], "arm": cell["logical"][1],
        "model": cell["logical"][2], "key": cell["key"], **snapshot,
        **candidates, "h": chosen, "selected_from": selected, "selected_proof": chosen["proof"],
        "selected_evaluation": chosen["evaluation"], "all_versions_valid": True,
        "control_job_key": d1["job_key"], "proposal_job_key": cleaned["job_key"] if cleaned else None,
        "stage03_accepted": repair["accepted"], "returned_incumbent": repair["returned_incumbent"],
        "complete_cleanup": control["status"] == "complete" and (proposal is None or proposal["status"] == "complete"),
        "rescued_vs_d0": bool(distinct_rejected and cleaned and score(cleaned["evaluation"]) > baseline + BUDGET.min_gain),
        "rescued_vs_d1": bool(distinct_rejected and cleaned and score(cleaned["evaluation"]) > baseline + BUDGET.min_gain
                              and score(cleaned["evaluation"]) > score(d1["evaluation"]))}


def prepare(args):
    if type(args.workers) is not int or not 1 <= args.workers <= 2:
        raise ValueError("Use one or two cleanup workers")
    if not isinstance(args.watch, bool):
        raise ValueError("watch must be a boolean")
    if isinstance(args.poll_seconds, bool) or not math.isfinite(args.poll_seconds) or not 0 < args.poll_seconds <= 60:
        raise ValueError("poll_seconds must be in (0,60]")
    repair_root, output = Path(args.input).resolve(), Path(args.output).resolve()
    prior = read(repair_root / "matrix_config.json")
    base = Path(prior["base_directory"]).resolve()
    for origin in (base, repair_root):
        if origin == output or origin in output.parents or output in origin.parents:
            raise ValueError("Output must be separate from both prior stages")
    config = read(base / "config.json")
    if digest(base / "config.json") != prior["base_config_sha256"]:
        raise ValueError("Frozen base config changed")
    if digest(base / "cell_index.json") != prior["base_index_sha256"] or digest(base / "input_hashes.json") != prior["base_input_hashes_sha256"]:
        raise ValueError("Frozen base index or inputs changed")
    if digest(args.dataset) != config["dataset_sha256"] or digest(args.environments) != config["environment_config_sha256"]:
        raise ValueError("Dataset or environment config changed")
    for path, expected in {**config["code_sha256"], **prior["code_sha256"]}.items():
        if digest(ROOT / path) != expected:
            raise ValueError("Frozen implementation changed: " + path)
    packs = {}
    for relative, expected in prior["input_files_sha256"].items():
        path = base / relative
        if digest(path) != expected:
            raise ValueError("Frozen input file changed: " + relative)
        pack = read(path)
        if pack["name"] in packs or fingerprint(pack) != prior["input_sha256"][pack["name"]]:
            raise ValueError("Duplicate or changed frozen input")
        require_valid(pack["incumbent"], pack["row"], pack["proof"])
        packs[pack["name"]] = pack
    index = read(base / "cell_index.json")
    expected = {(name, arm, model) for name in config["names"] for arm in config["arms"] for model in config["models"]}
    declared = {tuple(cell["logical"]): cell["key"] for cell in prior["cells"]}
    if (set(packs) != set(config["names"]) or set(declared) != expected
            or len(prior["cells"]) != len(expected) or len(set(declared.values())) != len(expected)
            or declared != {tuple(json.loads(logical)): key for logical, key in index.items()}):
        raise ValueError("Repair matrix is not the complete base cohort")
    code = {**config["code_sha256"], **prior["code_sha256"], **{path: digest(ROOT / path) for path in EXTRA_CODE}}
    matrix = {"schema_version": 1, "base_directory": str(base), "repair_directory": str(repair_root),
        "base_config_sha256": digest(base / "config.json"), "repair_matrix_config_sha256": digest(repair_root / "matrix_config.json"),
        "names": config["names"], "models": config["models"], "arms": config["arms"], "cells": prior["cells"],
        "controls": {name: job_key(name, pack["proof"]) for name, pack in packs.items()},
        "input_sha256": prior["input_sha256"], "input_files_sha256": prior["input_files_sha256"],
        "base_index_sha256": prior["base_index_sha256"], "base_input_hashes_sha256": prior["base_input_hashes_sha256"],
        "contexts": config["contexts"],
        "references_sha256": {name: fingerprint({v: item["reference"] for v, item in pack["incumbent"]["per_version"].items()})
                              for name, pack in packs.items()},
        "methods": list(METHODS), "budget": asdict(BUDGET), "code_sha256": code,
        "workers": args.workers, "watch": args.watch, "poll_seconds": args.poll_seconds,
        "protocol": "One ordered deterministic pass for every control and every valid repaired final, with exact all-version eligibility and shared proof-keyed jobs; no model calls or reference measurement."}
    return base, repair_root, output, config, matrix, packs


def snapshot_repair(repair_root, cell, pack):
    folder = repair_root / "cells" / cell["key"]
    if not (folder / "result.json").exists():
        return None, None
    record = read(folder / "result.json")
    if [record["name"], record["arm"], record["model"]] != cell["logical"] or record["base_request_sha256"] != cell["key"]:
        raise ValueError("Repair cell identity mismatch")
    cell_config = read(folder / "cell_config.json")
    if cell_config["input_sha256"] != fingerprint(pack):
        raise ValueError("Repair input identity changed")
    require_valid(record["selected_evaluation"], pack["row"], record["selected_proof"])
    actual_valid = all_versions_passed(record.get("final_evaluation") or {}, versions(pack["row"]))
    if record["final_valid"] is not actual_valid:
        raise ValueError("Repair final validity flag contradicts saved checks")
    if actual_valid:
        require_valid(record["final_evaluation"], pack["row"], record["final_proof"])
    return {"repair_result_sha256": digest(folder / "result.json"),
            "repair_cell_config_sha256": digest(folder / "cell_config.json"), "input_sha256": fingerprint(pack)}, record


def publish(output, matrix, jobs, results, snapshots, records, active, status, repair_status):
    controls = {name: {"job_key": key, "proof": results[key]["proof"], "evaluation": results[key]["evaluation"],
                       "cleanup_status": results[key]["status"], "result_sha256": digest(output / "jobs" / key / "result.json")}
                for name, key in matrix["controls"].items() if key in results}
    summary = {"status": status, "planned_cells": len(matrix["cells"]), "arrived_cells": len(snapshots),
        "recorded_cells": len(records), "complete_cleanup_cells": sum(r["complete_cleanup"] for r in records.values()),
        "planned_controls": len(matrix["controls"]), "recorded_controls": len(controls),
        "complete_controls": sum(v["cleanup_status"] == "complete" for v in controls.values()),
        "unique_cleanup_jobs": len(jobs), "terminal_cleanup_jobs": len(results), "active_cleanup_jobs": len(active),
        "repair_run_status": repair_status,
        "physical_counters": {key: sum(r["counters"].get(key, 0) for r in results.values()) for key in COUNTERS}}
    write_json(output / "controls.json", controls)
    write_json(output / "jobs.json", {"jobs": {key: {**value, "status": results[key]["status"] if key in results else "active" if key in active.values() else "pending"}
                                                for key, value in jobs.items()}})
    write_json(output / "arrivals.json", snapshots)
    write_json(output / "summary.json", summary)
    (output / "RUN_STATUS.md").write_text(f"# Combined deterministic cleanup\n\n**{status}**: {len(records)}/{len(matrix['cells'])} cells, {len(controls)}/{len(matrix['controls'])} controls, {len(results)}/{len(jobs)} unique cleanup jobs recorded.\n\nThe full cohort remains declared in `matrix_config.json`. Logical branches may share one physical cleanup. No new model requests or reference measurements occur. Unavailable discovery is incomplete cleanup. Detailed comparisons belong in [README.md](README.md).\n")
    return summary


def run(args, *, evaluator=None, cleanup_fn=cleanup_proof, sleep=time.sleep):
    base, repair_root, output, base_config, matrix, packs = prepare(args)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (output / "matrix_config.json").exists() and read(output / "matrix_config.json") != matrix:
            raise ValueError("Combined configuration changed; use a new output directory")
        write_json(output / "matrix_config.json", matrix)
        evaluator = evaluator or Evaluator(args.dataset, args.environments, args.cache)
        for pack in packs.values():
            check_references(evaluator, pack, base_config)
        snapshots, records, jobs, results, active, submitted = {}, {}, {}, {}, {}, set()
        if (output / "arrivals.json").exists():
            snapshots = read(output / "arrivals.json")
        def register(name, proof, origin):
            key = job_key(name, proof)
            if key not in jobs:
                jobs[key] = {"name": name, "proof_sha256": sha(proof), "origins": [], "proof": proof}
            if origin not in jobs[key]["origins"]:
                jobs[key]["origins"].append(origin)
            return key
        for name, pack in packs.items():
            register(name, pack["proof"], {"kind": "control", "name": name})
        def guard(name):
            if any(digest(ROOT / path) != expected for path, expected in matrix["code_sha256"].items()):
                raise ValueError("Frozen cleanup implementation changed during run")
            if digest(repair_root / "matrix_config.json") != matrix["repair_matrix_config_sha256"]:
                raise ValueError("Repair matrix configuration changed during run")
            if digest(base / "config.json") != matrix["base_config_sha256"]:
                raise ValueError("Base configuration changed during run")
            if any(digest(base / path) != expected for path, expected in matrix["input_files_sha256"].items()):
                raise ValueError("Frozen inputs changed during run")
            check_references(evaluator, packs[name], base_config)
        def work(key):
            job = jobs[key]
            name = job["name"]
            guard(name)
            return cleanup_fn(evaluator=evaluator, row=packs[name]["row"], proof=job["proof"],
                              folder=output / "jobs" / key, provenance=cleanup_provenance(matrix, name), guard=lambda: guard(name))
        run_record = {"status": "running", "started_at": now()}
        write_json(output / "run.json", run_record)
        try:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                while True:
                    repairs = {}
                    for cell in matrix["cells"]:
                        key, name = cell["key"], cell["logical"][0]
                        current, repair = snapshot_repair(repair_root, cell, packs[name])
                        path = output / "repair_snapshots" / (key + ".json")
                        if key in snapshots and current != snapshots[key] or path.exists() and read(path) != current:
                            raise ValueError("Saved repair cell changed: " + key)
                        if current is None:
                            continue
                        if not path.exists():
                            path.parent.mkdir(exist_ok=True)
                            write_json(path, current)
                        snapshots[key], repairs[key] = current, repair
                        if repair["final_valid"]:
                            register(name, repair["final_proof"], {"kind": "proposal", "cell_key": key})
                    for key in jobs:
                        if key not in submitted and len(active) < args.workers:
                            active[pool.submit(work, key)] = key
                            submitted.add(key)
                    done = [future for future in active if future.done()]
                    for future in done:
                        key = active.pop(future)
                        results[key] = future.result()
                    for cell in matrix["cells"]:
                        key, name = cell["key"], cell["logical"][0]
                        if key not in repairs or matrix["controls"][name] not in results:
                            continue
                        repair = repairs[key]
                        proposal_key = job_key(name, repair["final_proof"]) if repair["final_valid"] else None
                        if proposal_key and proposal_key not in results:
                            continue
                        record = select_cell(cell=cell, pack=packs[name], repair=repair, snapshot=snapshots[key],
                                             control=results[matrix["controls"][name]], proposal=results.get(proposal_key))
                        path = output / "cells" / key / "result.json"
                        if path.exists() and read(path) != record:
                            raise ValueError("Completed combined cell changed: " + key)
                        if not path.exists():
                            path.parent.mkdir(parents=True, exist_ok=True)
                            write_json(path, record)
                        records[key] = record
                    repair_status = read(repair_root / "run.json").get("status") if (repair_root / "run.json").exists() else "unknown"
                    finished = len(records) == len(matrix["cells"]) and len(results) == len(jobs)
                    if finished:
                        status = "complete" if all(r["complete_cleanup"] for r in records.values()) else "incomplete_cleanup"
                    elif active or len(submitted) < len(jobs):
                        status = "running"
                    elif not args.watch:
                        status = "incomplete_snapshot"
                    elif repair_status not in ACTIVE_STATUSES:
                        status = "incomplete_repair_terminal"
                    else:
                        status = "waiting_for_repair_results"
                    summary = publish(output, matrix, jobs, results, snapshots, records, active, status, repair_status)
                    write_json(output / "run.json", {**run_record, "status": status, "updated_at": now(), "summary": summary})
                    if status not in {"running", "waiting_for_repair_results"}:
                        return summary
                    if active:
                        wait(active, timeout=min(args.poll_seconds, 1), return_when=FIRST_COMPLETED)
                    elif len(submitted) == len(jobs):
                        sleep(args.poll_seconds)
        except BaseException as exc:
            write_json(output / "run.json", {**run_record, "status": "interrupted", "updated_at": now(),
                                             "error": type(exc).__name__ + ": " + str(exc)})
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="results/one_shot/03_repaired_context_ablation")
    parser.add_argument("--output", default="results/one_shot/04_combined_deterministic")
    parser.add_argument("--dataset", default="data/benchmark_data_warmup.jsonl")
    parser.add_argument("--environments", default="environments.local.json")
    parser.add_argument("--cache", default=".proof-eval")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=5)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "complete" else 2)


if __name__ == "__main__":
    main()
