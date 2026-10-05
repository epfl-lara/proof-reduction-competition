"""Report deterministic controls and each independent model-plus-cleanup condition.

Reads saved artifacts only. Unique physical cleanup work is accounted once;
reused proof branches and original model conditions remain separate.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean

from report_one_shot import CONTRASTS, FIELDS, average_scores, complete_scores, digest, fmt, read_json, scores, write_csv, write_json
from proof_eval.one_shot import fingerprint
from validity_feedback import all_versions_passed


BRANCHES = ("d0", "d1", "l", "f", "cleaned_f", "h")


def versions(pack):
    return [version for item in pack["row"]["version_info"] for version in item]


def resolve_directory(root, saved, override):
    path = Path(override) if override is not None else Path(saved)
    return (root / path).resolve() if not path.is_absolute() else path.resolve()


def score(branch):
    return scores(branch["evaluation"])["combined_pct"]


def load(root, base_override=None, repair_override=None):
    config = read_json(root / "matrix_config.json")
    base = resolve_directory(root, config["base_directory"], base_override)
    repair = resolve_directory(root, config["repair_directory"], repair_override)
    base_config = read_json(base / "config.json")
    names = config["names"]
    if not names or len(set(names)) != len(names):
        raise ValueError("Expected unique nonempty theorem cohort")
    if set(names) != set(base_config["names"]):
        raise ValueError("Combined reporting requires the complete original theorem cohort")
    if any(set(config[field]) != set(base_config[field]) for field in ("models", "arms")):
        raise ValueError("Combined model and arm cohort differs from the original experiment")
    if config.get("base_config_sha256") and config["base_config_sha256"] != digest(base / "config.json"):
        raise ValueError("Base configuration hash changed")
    inputs, hashes = {}, {"matrix_config.json": digest(root / "matrix_config.json"), "base/config.json": digest(base / "config.json")}
    for config_key, label, path in (
            ("repair_matrix_config_sha256", "repair/matrix_config.json", repair / "matrix_config.json"),
            ("base_index_sha256", "base/cell_index.json", base / "cell_index.json"),
            ("base_input_hashes_sha256", "base/input_hashes.json", base / "input_hashes.json")):
        if config.get(config_key):
            if digest(path) != config[config_key]:
                raise ValueError("Frozen provenance changed: " + label)
            hashes[label] = digest(path)
    for path in (base / "inputs").glob("*.json"):
        pack = read_json(path)
        if pack["name"] not in names:
            continue
        if pack["name"] in inputs or not complete_scores(pack["incumbent"]):
            raise ValueError("Duplicate or unscored original incumbent")
        if config.get("input_sha256", {}).get(pack["name"], fingerprint(pack)) != fingerprint(pack):
            raise ValueError("Original incumbent input fingerprint changed")
        if config.get("input_files_sha256", {}).get(str(path.relative_to(base)), digest(path)) != digest(path):
            raise ValueError("Original incumbent input file changed")
        inputs[pack["name"]] = pack
        hashes["base/" + str(path.relative_to(base))] = digest(path)
    if set(inputs) != set(names):
        raise ValueError("Missing original incumbent input")
    planned = {}
    for cell in config["cells"]:
        name, arm, model = cell["logical"]
        if (cell["key"] in planned or name not in names or arm not in config["arms"]
                or model not in config["models"]):
            raise ValueError("Duplicate or unexpected planned cell")
        planned[cell["key"]] = cell
    expected = {(name, arm, model) for name in names for arm in config["arms"] for model in config["models"]}
    if {tuple(cell["logical"]) for cell in planned.values()} != expected or len(planned) != len(expected):
        raise ValueError("Combined matrix must declare the complete configured Cartesian cohort")
    index_path = base / "cell_index.json"
    if index_path.exists():
        index = read_json(index_path)
        if any(index.get(json.dumps(cell["logical"])) != key for key, cell in planned.items()):
            raise ValueError("Combined cell differs from the original request index")
    if set(config["controls"]) != set(names):
        raise ValueError("Every original theorem requires a control")
    # Reference snapshots precede job loading: a cell/control is published only
    # after its terminal job, so concurrently arriving cells cannot reference a
    # job omitted by an earlier directory scan.
    control_path = root / "controls.json"
    controls = read_json(control_path) if control_path.exists() else {}
    cell_snapshots = [(path, read_json(path)) for path in sorted((root / "cells").glob("*/result.json"))]
    jobs = {}
    for path in sorted((root / "jobs").glob("*/result.json")):
        job = read_json(path)
        if job["name"] not in inputs:
            raise ValueError("Cleanup job outside the configured theorem cohort")
        if job.get("input_proof_sha256") != hashlib.sha256(job["input_proof"].encode()).hexdigest():
            raise ValueError("Cleanup input proof hash mismatch")
        if path.parent.name != fingerprint({"name": job["name"], "proof_sha256": job["input_proof_sha256"]}):
            raise ValueError("Cleanup job key does not identify its theorem and input proof")
        if not complete_scores(job["evaluation"]) or not complete_scores(job["initial_evaluation"]):
            raise ValueError("Terminal cleanup result has incomplete evaluation metrics")
        valid = all_versions_passed(job["evaluation"], versions(inputs[job["name"]]))
        if job["all_versions_valid"] != valid or not valid:
            raise ValueError("Cleanup result does not have the recorded all-version validity")
        if scores(job["evaluation"])["combined_pct"] + 1e-10 < scores(job["initial_evaluation"])["combined_pct"]:
            raise ValueError("Cleanup job regressed from its own starting proof")
        jobs[path.parent.name] = job
        hashes[str(path.relative_to(root))] = digest(path)
    complete_controls = {}
    for name, control in controls.items():
        if name not in config["controls"] or control["job_key"] != config["controls"][name]:
            raise ValueError("Control identity mismatch")
        job_key = control["job_key"]
        if job_key not in jobs:
            raise ValueError("Control has no saved physical cleanup result")
        job = jobs[job_key]
        if control.get("result_sha256") != hashes["jobs/" + job_key + "/result.json"]:
            raise ValueError("Control cleanup result hash mismatch")
        if control["proof"] != job["proof"] or control["evaluation"] != job["evaluation"]:
            raise ValueError("Control differs from its physical cleanup result")
        if job["input_proof"] != inputs[name]["proof"]:
            raise ValueError("Control was not started from the original incumbent")
        if job["status"] == "complete" and control["cleanup_status"] == "complete":
            complete_controls[name] = control
    records = {}
    for path, record in cell_snapshots:
        key = path.parent.name
        if key not in planned or [record["name"], record["arm"], record["model"]] != planned[key]["logical"]:
            raise ValueError("Combined cell identity mismatch")
        name = record["name"]
        if record["control_job_key"] != config["controls"][name]:
            raise ValueError("Combined cell has a different control")
        if record["source"] != inputs[name]["row"]["source"]:
            raise ValueError("Combined source identity mismatch")
        for label in BRANCHES:
            branch = record.get(label)
            if branch is None:
                if label not in {"f", "cleaned_f"}:
                    raise ValueError("Required comparison branch is absent")
                continue
            if not complete_scores(branch["evaluation"]) or not all_versions_passed(branch["evaluation"], versions(inputs[name])):
                raise ValueError("Comparison branch is not fully scored and all-version valid")
        if record["d0"]["proof"] != inputs[name]["proof"] or record["d0"]["evaluation"] != inputs[name]["incumbent"]:
            raise ValueError("Archived deterministic incumbent differs from original input")
        for label, job_key in (("d1", record["control_job_key"]), ("cleaned_f", record.get("proposal_job_key"))):
            if job_key is None:
                if record.get(label) is not None:
                    raise ValueError("Cleaned proposal is missing its physical job")
                continue
            if job_key not in jobs or record[label]["proof"] != jobs[job_key]["proof"] or record[label]["evaluation"] != jobs[job_key]["evaluation"]:
                raise ValueError("Cell cleanup branch differs from its physical job")
        if record.get("proposal_job_key") and jobs[record["proposal_job_key"]]["input_proof"] != record["f"]["proof"]:
            raise ValueError("Proposal cleanup did not start from the valid repaired final")
        h = record["h"]
        if record["selected_proof"] != h["proof"] or record["selected_evaluation"] != h["evaluation"]:
            raise ValueError("Combined selection differs from H")
        if score(h) + 1e-10 < max(score(record["d0"]), score(record["d1"]), score(record["l"])):
            raise ValueError("Combined selection regressed below D0, D1, or L")
        chosen = record["selected_from"]
        if chosen not in BRANCHES[:-1] or record.get(chosen) is None:
            raise ValueError("Unknown selected branch")
        if h["proof"] != record[chosen]["proof"] or h["evaluation"] != record[chosen]["evaluation"]:
            raise ValueError("Selected branch provenance disagrees with H")
        eligible = [label for label in ("d1", "l", "d0", "f", "cleaned_f")
                    if record.get(label) is not None and (label in {"d1", "l", "d0"}
                    or score(record[label]) > score(record["d0"]) + .05)]
        expected_choice = max(eligible, key=lambda label: score(record[label]))
        if chosen != expected_choice:
            raise ValueError("H is not the exact eligible maximum with control tie preference")
        distinct_rejected = (record.get("f") is not None and not record["stage03_accepted"]
                             and record["f"]["proof"].strip() != record["d0"]["proof"].strip())
        for suffix, threshold in (("d0", score(record["d0"]) + .05), ("d1", score(record["d1"]))):
            rescued = bool(distinct_rejected and record.get("cleaned_f")
                           and score(record["cleaned_f"]) > score(record["d0"]) + .05
                           and score(record["cleaned_f"]) > threshold)
            if record.get("rescued_vs_" + suffix) != rescued:
                raise ValueError("Rescue flag disagrees with saved branch scores")
        actually_complete = all(jobs[job_key]["status"] == "complete" for job_key in
                (record["control_job_key"], record.get("proposal_job_key")) if job_key is not None)
        if record["complete_cleanup"] != actually_complete:
            raise ValueError("Cell completion disagrees with physical cleanup status")
        repair_result = repair / "cells" / key / "result.json"
        if not repair_result.exists() or digest(repair_result) != record["repair_result_sha256"]:
            raise ValueError("Consumed repair result hash mismatch")
        previous = read_json(repair_result)
        if record["l"]["proof"] != previous["selected_proof"] or record["l"]["evaluation"] != previous["selected_evaluation"]:
            raise ValueError("Preserved L differs from its saved repair result")
        if record["stage03_accepted"] != previous["accepted"] or record["returned_incumbent"] != previous["returned_incumbent"]:
            raise ValueError("Repair acceptance or unchanged-incumbent label changed")
        if (record.get("f") is not None) != previous["final_valid"]:
            raise ValueError("Raw F availability differs from saved repair validity")
        if record.get("f") is not None and (record["f"]["proof"] != previous["final_proof"]
                or record["f"]["evaluation"] != previous["final_evaluation"]):
            raise ValueError("Raw F differs from its saved repaired final")
        if record.get("input_sha256", fingerprint(inputs[name])) != fingerprint(inputs[name]):
            raise ValueError("Combined cell input fingerprint changed")
        if record.get("repair_cell_config_sha256"):
            cell_config = repair_result.with_name("cell_config.json")
            if digest(cell_config) != record["repair_cell_config_sha256"]:
                raise ValueError("Consumed repair cell configuration changed")
            hashes["repair/cells/" + key + "/cell_config.json"] = digest(cell_config)
        records[key] = record
        hashes[str(path.relative_to(root))] = digest(path)
        hashes["repair/cells/" + key + "/result.json"] = digest(repair_result)
    jobs_path = root / "jobs.json"
    manifest = read_json(jobs_path).get("jobs", {}) if jobs_path.exists() else {}
    return config, base_config, inputs, planned, jobs, controls, complete_controls, records, manifest, hashes


def summarize_rows(rows, expected, controls_ready):
    completed = [row for row in rows if row["complete_cleanup"]]
    ready = len(completed) == expected and controls_ready
    means = {label: average_scores([row[label]["evaluation"] for row in completed]) if ready
             else dict.fromkeys(FIELDS, None) for label in ("d0", "d1", "l", "h")}
    return {
        "expected_problems": expected, "recorded_problems": len(rows), "complete_cleanup_problems": len(completed),
        "complete": ready, "means": means,
        "gain_h_minus_d1_pp": means["h"]["combined_pct"] - means["d1"]["combined_pct"] if ready else None,
        "gain_h_minus_l_pp": means["h"]["combined_pct"] - means["l"]["combined_pct"] if ready else None,
        "gain_d1_minus_d0_pp": means["d1"]["combined_pct"] - means["d0"]["combined_pct"] if ready else None,
        "improved_over_control": sum(score(row["h"]) > score(row["d1"]) + 1e-10 for row in completed),
        "improved_over_stage03": sum(score(row["h"]) > score(row["l"]) + 1e-10 for row in completed),
        "valid_proposal_branches": sum(row.get("f") is not None for row in rows),
        "rescued_vs_d0": sum(bool(row.get("rescued_vs_d0")) for row in completed),
        "rescued_vs_d1": sum(bool(row.get("rescued_vs_d1")) for row in completed),
        "selected_from_counts": dict(sorted(Counter(row["selected_from"] for row in completed).items())),
        "proposal_job_references": sum(row.get("proposal_job_key") is not None for row in rows),
        "distinct_proposal_jobs": len({row["proposal_job_key"] for row in rows if row.get("proposal_job_key")}),
        "selected_version_checks": sum(len(row["h"]["evaluation"]["per_version"]) for row in completed),
    }


def pairwise_effects(config, records, controls_ready):
    by_logical = {(r["model"], r["arm"], r["name"]): r for r in records.values() if r["complete_cleanup"]}
    summaries, rows = [], []
    for model in config["models"]:
        for label, weights in CONTRASTS.items():
            if set(weights) - set(config["arms"]):
                continue
            values = []
            for name in config["names"]:
                if not all((model, arm, name) in by_logical for arm in weights):
                    continue
                selected = {arm: by_logical[model, arm, name] for arm in weights}
                value = sum(weight * score(selected[arm]["h"]) for arm, weight in weights.items())
                values.append(value)
                rows.append({"model": model, "contrast": label, "name": name,
                             "combined_selected_delta_pp": value})
            ready = len(values) == len(config["names"]) and controls_ready
            summaries.append({"model": model, "contrast": label, "weights": weights,
                              "expected_pairs": len(config["names"]), "recorded_pairs": len(values),
                              "combined_selected_mean_delta_pp": mean(values) if ready else None,
                              "positive_pairs": sum(v > 1e-10 for v in values), "negative_pairs": sum(v < -1e-10 for v in values)})
    return summaries, rows


def build_report(root, base_override=None, repair_override=None):
    config, base_config, inputs, planned, jobs, controls, ready_controls, records, manifest, hashes = load(root, base_override, repair_override)
    controls_ready = set(ready_controls) == set(config["names"])
    conditions, sources, problems = [], [], []
    for model in config["models"]:
        for arm in config["arms"]:
            rows = [r for r in records.values() if r["model"] == model and r["arm"] == arm]
            condition = {"model": model, "arm": arm, **summarize_rows(rows, len(config["names"]), controls_ready)}
            conditions.append(condition)
            for source in sorted({inputs[name]["row"]["source"] for name in config["names"]}):
                names = [name for name in config["names"] if inputs[name]["row"]["source"] == source]
                sources.append({"model": model, "arm": arm, "source": source,
                                **summarize_rows([r for r in rows if r["name"] in names], len(names), condition["complete"])})
            by_name = {r["name"]: r for r in rows}
            for name in config["names"]:
                row = by_name.get(name)
                problems.append({"model": model, "arm": arm, "name": name, "source": inputs[name]["row"]["source"],
                    "recorded": row is not None, "complete_cleanup": row["complete_cleanup"] if row else False,
                    "d0": scores(inputs[name]["incumbent"])["combined_pct"],
                    **{label: score(row[label]) if row and row.get(label) else None for label in ("d1", "l", "f", "cleaned_f", "h")},
                    "h_minus_d1_pp": score(row["h"]) - score(row["d1"]) if row else None,
                    "h_minus_l_pp": score(row["h"]) - score(row["l"]) if row else None,
                    "selected_from": row["selected_from"] if row else None,
                    "rescued_vs_d0": row.get("rescued_vs_d0") if row else None,
                    "rescued_vs_d1": row.get("rescued_vs_d1") if row else None,
                    "control_job_key": config["controls"][name], "proposal_job_key": row.get("proposal_job_key") if row else None})
    counters = Counter()
    for job in jobs.values():
        for key, value in job.get("counters", {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                counters[key] += value
    physical_refs = Counter(config["controls"].values())
    physical_refs.update(r["proposal_job_key"] for r in records.values() if r.get("proposal_job_key"))
    proposal_refs = sum(r.get("proposal_job_key") is not None for r in records.values())
    origins = [origin for job in manifest.values() for origin in job.get("origins", [])]
    effects, paired = pairwise_effects(config, records, controls_ready)
    report = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if all(c["complete"] for c in conditions) else "incomplete",
        "planned_cells": len(planned), "recorded_cells": len(records),
        "complete_cleanup_cells": sum(r["complete_cleanup"] for r in records.values()),
        "problem_count": len(config["names"]), "names": config["names"],
        "baseline_d0_mean": average_scores([inputs[n]["incumbent"] for n in config["names"]]),
        "control_d1_mean": average_scores([ready_controls[n]["evaluation"] for n in config["names"]]) if controls_ready else dict.fromkeys(FIELDS, None),
        "recorded_controls": len(controls), "completed_controls": len(ready_controls),
        "methods": config["methods"], "budget": config["budget"],
        "conditions": conditions, "sources": sources, "paired_contrasts": effects,
        "work_accounting": {
            "logical_control_cleanup_references": len(config["controls"]),
            "control_result_uses_in_recorded_cells": len(records),
            "proposal_cleanup_references_in_recorded_cells": proposal_refs,
            "total_recorded_cleanup_references": len(config["controls"]) + proposal_refs,
            "distinct_jobs_in_recorded_references": len(physical_refs),
            "deduplicated_recorded_references": sum(physical_refs.values()) - len(physical_refs),
            "jobs_with_multiple_recorded_references": sum(count > 1 for count in physical_refs.values()),
            "registered_physical_jobs": len(manifest), "terminal_physical_jobs": len(jobs),
            "registered_control_origins": sum(origin.get("kind") == "control" for origin in origins),
            "registered_proposal_origins": sum(origin.get("kind") == "proposal" for origin in origins),
            "registered_logical_cleanup_origins": len(origins),
            "deduplicated_registered_origins": len(origins) - len(manifest),
            "complete_physical_jobs": sum(job["status"] == "complete" for job in jobs.values()),
            "incomplete_discovery_jobs": sum(job["status"] == "incomplete_discovery" for job in jobs.values()),
            "unique_terminal_job_counters": dict(counters),
            "registered_job_origins": {key: item.get("origins", []) for key, item in manifest.items()},
            "verification_accounting": sorted({job["verification_accounting"] for job in jobs.values() if "verification_accounting" in job}),
            "semantics": "Counters sum each saved terminal job exactly once, including incomplete-discovery terminals. In-progress work is not estimated. Logical proposal references count recorded cell artifacts only; registered origins may include pending cells. Control result uses are not extra cleanup jobs.",
        },
        "artifact_sha256": hashes,
        "limitations": [
            "This exploratory extension was chosen after partial model results were observed; it is not an independent preregistered confirmation.",
            "H minus D1 compares the added model branch against the extra deterministic control; H minus L includes cleanup and control fallback.",
            "Control plus proposal cleanup can perform more total computation than the control alone; identical per-job budgets do not equalize total compute.",
            "No new model calls occur in this stage. Earlier model calls overlap with correctness repairs and can encounter queue blocking; no latency ranking is justified.",
            "One stochastic optimization proposal per cell and fifteen development problems do not establish a universally best model or context.",
            "Deterministic search is bounded, not exhaustive; incomplete discovery is not proof that no improvement exists.",
            "Full condition means and exports require all configured theorems and all controls to complete. No cross-model or cross-arm pooling is performed.",
            "The reporter reads recorded Lean checks and cached-reference scores without new compilation or reference measurement.",
        ],
    }
    return report, config, records, problems, paired


def export_conditions(root, output, report, config, records):
    exports = []
    for condition in report["conditions"]:
        if not condition["complete"]:
            continue
        model, arm = condition["model"], condition["arm"]
        by_name = {r["name"]: (key, r) for key, r in records.items() if r["model"] == model and r["arm"] == arm}
        candidates, evidence = [], []
        for name in config["names"]:
            key, row = by_name[name]
            path = "cells/" + key + "/result.json"
            if digest(root / path) != report["artifact_sha256"][path]:
                raise ValueError("Combined result changed while exporting")
            candidates.append({"name": name, "proof": row["selected_proof"]})
            evidence.append({"name": name, "base_request_sha256": key, "combined_result_sha256": report["artifact_sha256"][path],
                             "repair_result_sha256": row["repair_result_sha256"], "selected_from": row["selected_from"],
                             "control_job_key": row["control_job_key"], "proposal_job_key": row.get("proposal_job_key"),
                             "job_result_sha256": {job: report["artifact_sha256"]["jobs/" + job + "/result.json"] for job in
                                 (row["control_job_key"], row.get("proposal_job_key")) if job is not None},
                             "selected_scores": scores(row["selected_evaluation"])})
        relative = Path("conditions") / (model.split("/")[-1] + "__" + arm)
        folder = output / relative
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "selected_candidates.jsonl"
        temporary = target.with_suffix(".jsonl.tmp")
        temporary.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in candidates), encoding="utf-8")
        temporary.replace(target)
        manifest = {"schema_version": 1, "created_at": report["created_at"], "model": model, "arm": arm,
                    "scope": "Independent combined condition; no pooling across model or context arms.", "problem_count": len(candidates),
                    "matrix_config_sha256": report["artifact_sha256"]["matrix_config.json"],
                    "baseline_d0_mean": report["baseline_d0_mean"], "control_d1_mean": report["control_d1_mean"],
                    "selected_mean": condition["means"]["h"], "gain_over_control_pp": condition["gain_h_minus_d1_pp"],
                    "candidates_sha256": digest(target), "problems": evidence}
        write_json(folder / "manifest.json", manifest)
        exports.append({"model": model, "arm": arm, "submission": str(relative / "selected_candidates.jsonl"),
                        "manifest": str(relative / "manifest.json"), "candidates_sha256": manifest["candidates_sha256"]})
    return exports


def markdown(report):
    work = report["work_accounting"]
    lines = ["# Deterministic cleanup after model proposals", "",
        f"**{report['status']}**: {report['complete_cleanup_cells']}/{report['planned_cells']} cells have complete cleanup; "
        f"{report['completed_controls']}/{report['problem_count']} deterministic controls are complete. "
        f"The archived deterministic incumbent score is **{report['baseline_d0_mean']['combined_pct']:.6f}%**.", "",
        "D0 is the archived deterministic incumbent. D1 applies the new bounded cleanup to D0. "
        "F is the first all-version-valid model proposal after correctness repair, even when its score was rejected. "
        "L is stage 03's incumbent-selected result. H selects the highest-scoring eligible proof from the control, "
        "the preserved earlier selection, and the cleaned proposal. D0 remains the fallback; exact ties prefer D1. "
        "Eligibility for new improvements is measured against D0 with the 0.05-point margin, not a second sequential margin against L.", "",
        "All selected transitions must pass every required version. No deterministic results or scores are sent to the model, "
        "and this stage makes no new model calls. Each unique cleanup uses one ordered pass of ten methods, with "
        "three rounds, 32 trials, and six discovery sites per method; it does not search to a fixed point.", "",
        "## Complete-condition score comparison", "",
        "All means remain blank until every theorem in that condition and every control is complete. "
        "H − D1 is the value of the model branch beyond the extra deterministic control. H − L is the additional "
        "gain from cleanup and control fallback. Identical per-job budgets do not make these equal-total-compute comparisons.", "",
        "| Model | Arm | Complete / expected | D1 | L | H | H − D1 pp | H − L pp | Above D1 | Rejected F rescued above D1 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for c in report["conditions"]:
        lines.append(f"| {c['model'].split('/')[-1]} | {c['arm']} | {c['complete_cleanup_problems']}/{c['expected_problems']} "
            f"| {fmt(c['means']['d1']['combined_pct'])} | {fmt(c['means']['l']['combined_pct'])} | {fmt(c['means']['h']['combined_pct'])} "
            f"| {fmt(c['gain_h_minus_d1_pp'], True)} | {fmt(c['gain_h_minus_l_pp'], True)} | {c['improved_over_control']} | {c['rescued_vs_d1']} |")
    lines += ["", "Counts concern completed cleanup rows; they can be partial while means remain blank. "
        "A score-rejected F cleaned above D0 is recorded separately from one that actually beats D1. "
        "Returning the unchanged incumbent is not a model rescue. Per-axis scores and selected version checks are in the JSON.", "",
        "## Unique work versus reused branches", "",
        f"There are {work['logical_control_cleanup_references']} logical control cleanups. Recorded cells reuse those results "
        f"{work['control_result_uses_in_recorded_cells']} times; those uses are not extra compiler jobs. "
        f"Recorded model branches reference cleanup jobs {work['proposal_cleanup_references_in_recorded_cells']} times. "
        f"The combined references cover {work['distinct_jobs_in_recorded_references']} unique jobs, with "
        f"{work['deduplicated_recorded_references']} shared references beyond those distinct jobs.", "",
        f"Registered physical jobs: {work['registered_physical_jobs']}; terminal jobs: {work['terminal_physical_jobs']}; "
        f"complete: {work['complete_physical_jobs']}; incomplete discovery: {work['incomplete_discovery_jobs']}. "
        f"The job registry includes {work['registered_proposal_origins']} proposal origins, including pending cells. "
        "The following counters sum each terminal physical job once. Work in unfinished jobs is not estimated; "
        "cache hits within a physical job are distinct from reusing that entire job.", "",
        "| Recorded physical-work counter | Total |", "| --- | ---: |"]
    for key, value in sorted(work["unique_terminal_job_counters"].items()):
        rendered = f"{value:.3f}" if isinstance(value, float) else str(value)
        lines.append(f"| `{key}` | {rendered} |")
    lines += ["", "Optimizer counters exclude the job's initial and final whole-proof validation calls, which can hit "
        "the evaluator cache. The job records preserve that accounting; no extra compiler-process count is inferred. "
        "Saved durations can overlap and are not end-to-end wall time. Earlier initial and repair requests share "
        "model services and may encounter queue blocking; this experiment does not support model latency rankings.", "",
        "## Evidence and exports", "",
        "[per_problem.csv](per_problem.csv) preserves D0, D1, L, F, cleaned F, H, branch identities, and rescue flags. "
        "[source_results.csv](source_results.csv) shows source-level gains after full conditions complete. "
        "[pairwise.csv](pairwise.csv) records paired context contrasts; the JSON includes the same 2×2 card/goal "
        "effects and interaction as earlier stages, with cost context isolated by `cards_goals_costs − cards_goals`. "
        "These are descriptive one-draw comparisons, not significance tests. [report.json](report.json) also records "
        "all completion denominators, physical-work accounting, registered job origins, and input/result hashes.", "",
        "Only complete conditions receive separate submission JSONL files and manifests. No pooled best-of-arms selection is made.", ""]
    if report.get("condition_exports"):
        lines += ["Available submissions: " + "; ".join(
            f"[{e['model'].split('/')[-1]} / {e['arm']}]({e['submission']})" for e in report["condition_exports"]) + ".", ""]
    lines += ["## Limits", "", *["- " + item for item in report["limitations"]], "",
        "Rebuild the report from saved evidence:", "", "```bash",
        "python src/report_combined_matrix.py --input results/one_shot/04_combined_deterministic", "```", ""]
    return "\n".join(lines)


def run(root, output=None, base=None, repair=None):
    root = Path(root).resolve()
    output = Path(output).resolve() if output is not None else root
    report, config, records, problems, paired = build_report(root, base, repair)
    output.mkdir(parents=True, exist_ok=True)
    report["condition_exports"] = export_conditions(root, output, report, config, records)
    write_json(output / "report.json", report)
    write_csv(output / "per_problem.csv", problems, list(problems[0]))
    write_csv(output / "pairwise.csv", paired, ["model", "contrast", "name", "combined_selected_delta_pp"])
    source_rows = [{"model": row["model"], "arm": row["arm"], "source": row["source"],
                    "expected": row["expected_problems"], "complete_cleanup": row["complete_cleanup_problems"],
                    "condition_complete": row["complete"], **{label: row["means"][label]["combined_pct"] for label in ("d0", "d1", "l", "h")},
                    "h_minus_d1_pp": row["gain_h_minus_d1_pp"], "h_minus_l_pp": row["gain_h_minus_l_pp"],
                    "rescued_vs_d0": row["rescued_vs_d0"], "rescued_vs_d1": row["rescued_vs_d1"]} for row in report["sources"]]
    write_csv(output / "source_results.csv", source_rows, list(source_rows[0]))
    (output / "README.md").write_text(markdown(report), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--base", type=Path, help="Relocated original experiment")
    parser.add_argument("--repair", type=Path, help="Relocated repaired experiment")
    args = parser.parse_args(argv)
    report = run(args.input, args.output, args.base, args.repair)
    print(json.dumps({key: report[key] for key in ("status", "planned_cells", "recorded_cells", "completed_controls")}))


if __name__ == "__main__":
    main()
