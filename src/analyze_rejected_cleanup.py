"""Counterfactual analysis of saved deterministic cleanup, with no new execution.

Scores remain independent per model/context condition. Physical job accounting
respects shared control/proposal origins and distinguishes copied old evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean

from report_combined_matrix import load, score
from report_one_shot import digest, read_json, write_csv, write_json


COUNTERS = ("attempts", "analysis_requests", "lean_candidate_checks", "cache_hits", "accepted_transitions")


def selected_without_rejected_cleanup(row, *, retained_jobs=None):
    """Exact original margin/tie order; optionally reuse a retained same-proof job."""
    permit_cleanup = bool(row["stage03_accepted"])
    if retained_jobs is not None:
        permit_cleanup = row.get("proposal_job_key") in retained_jobs
    labels = [label for label in ("d1", "l", "d0", "f", "cleaned_f")
              if row.get(label) is not None
              and (label != "cleaned_f" or permit_cleanup)
              and (label in {"d1", "l", "d0"} or score(row[label]) > score(row["d0"]) + .05)]
    chosen = max(labels, key=lambda label: score(row[label]))
    return chosen, score(row[chosen])


def summed_counters(keys, jobs):
    return {field: sum(jobs[key].get("counters", {}).get(field, 0) for key in keys) for field in COUNTERS}


def historical_jobs(root, jobs, receipts):
    """Require explicit copying evidence, rather than guessing from timestamps."""
    historical, receipt_hashes = set(), {}
    for path in receipts:
        path = Path(path).resolve()
        receipt = read_json(path)
        if receipt.get("status") != "complete":
            raise ValueError("Historical-copy receipt is incomplete")
        receipt_hashes[str(path)] = digest(path)
        rows = receipt.get("jobs", receipt.get("controls"))
        if not isinstance(rows, dict):
            raise ValueError("Historical-copy receipt lacks job records")
        for item in rows.values():
            key = item["job_key"]
            destination = root / "jobs" / key
            if Path(item["destination_directory"]).resolve() != destination.resolve():
                raise ValueError("Historical-copy receipt refers to another destination")
            if key not in jobs or digest(destination / "result.json") != item["result_sha256"]:
                raise ValueError("Copied job result differs from its receipt")
            if item.get("job_config_sha256") and digest(destination / "job_config.json") != item["job_config_sha256"]:
                raise ValueError("Copied job configuration differs from its receipt")
            if item.get("historical_counters") != jobs[key].get("counters"):
                raise ValueError("Historical job counters changed")
            historical.add(key)
    return historical, receipt_hashes


def classify_jobs(config, planned, records, jobs, manifest):
    """Reject incomplete origin lists when establishing removable physical work."""
    controls = set(config["controls"].values())
    accepted = {row["proposal_job_key"] for row in records.values()
                if row["stage03_accepted"] and row.get("proposal_job_key")}
    proposal_origins = {}
    for key, row in records.items():
        if row.get("proposal_job_key"):
            proposal_origins.setdefault(row["proposal_job_key"], set()).add(key)
    for job_key, keys in proposal_origins.items():
        if job_key not in jobs or job_key not in manifest:
            raise ValueError("Physical proposal job lacks registered origin evidence")
        if any(origin.get("kind") not in {"control", "proposal"}
               for origin in manifest[job_key].get("origins", [])):
            raise ValueError("Unknown physical job origin kind")
        registered = {origin["cell_key"] for origin in manifest[job_key].get("origins", [])
                      if origin.get("kind") == "proposal"}
        if not keys <= registered:
            raise ValueError("Physical proposal job is missing a recorded cell origin")
        for key in registered:
            if key not in planned or key not in records or records[key].get("proposal_job_key") != job_key:
                raise ValueError("Registered job origin is incomplete or inconsistent")
    retained = controls | accepted
    omitted = set(proposal_origins) - retained
    return retained, omitted, proposal_origins


def analyze(root, *, receipts=(), require_complete=False):
    root = Path(root).resolve()
    config, _, _, planned, jobs, _, complete_controls, records, manifest, hashes = load(root)
    ready = (len(records) == len(planned) and len(complete_controls) == len(config["names"])
             and all(row["complete_cleanup"] for row in records.values()))
    if require_complete and not ready:
        raise ValueError("Full counterfactual accounting requires all declared cells and controls")
    standard_receipts = [root / "validation" / filename for filename in ("control_reuse.json", "cleanup_reuse.json")]
    receipts = list(dict.fromkeys(Path(path).resolve() for path in [*receipts, *standard_receipts]
                                 if Path(path).exists() or path in receipts))
    historical, receipt_hashes = historical_jobs(root, jobs, receipts)
    retained, omitted, origins = (set(), set(), {})
    if ready:
        retained, omitted, origins = classify_jobs(config, planned, records, jobs, manifest)
    rows = []
    for cell in config["cells"]:
        key = cell["key"]
        name, arm, model = cell["logical"]
        row = records.get(key)
        complete = row is not None and row["complete_cleanup"]
        chosen, counterfactual = selected_without_rejected_cleanup(row) if complete else (None, None)
        cached_choice, cached = selected_without_rejected_cleanup(row, retained_jobs=retained) if ready else (None, None)
        actual = score(row["h"]) if complete else None
        if complete and counterfactual > actual + 1e-10:
            raise ValueError("Removing cleanup cannot improve the recorded eligible maximum")
        rows.append({"key": key, "name": name, "model": model, "arm": arm, "complete": complete,
            "stage03_accepted": row["stage03_accepted"] if row else None,
            "proposal_job_key": row.get("proposal_job_key") if row else None,
            "actual_h": actual, "accepted_only_score": counterfactual,
            "accepted_only_selected_from": chosen,
            "score_lost_pp": actual - counterfactual if complete else None,
            "cache_preserving_score": cached, "cache_preserving_selected_from": cached_choice,
            "cache_preserving_loss_pp": actual - cached if ready else None})
    conditions = []
    for model in config["models"]:
        for arm in config["arms"]:
            cohort = [row for row in rows if row["model"] == model and row["arm"] == arm]
            complete = all(row["complete"] for row in cohort) and len(complete_controls) == len(config["names"])
            condition_jobs = {row["proposal_job_key"] for row in cohort if row["proposal_job_key"]}
            referenced_omitted = condition_jobs & omitted
            conditions.append({"model": model, "arm": arm, "expected_problems": len(cohort),
                "complete_problems": sum(row["complete"] for row in cohort), "complete": complete,
                "actual_h_mean": mean(row["actual_h"] for row in cohort) if complete else None,
                "accepted_only_mean": mean(row["accepted_only_score"] for row in cohort) if complete else None,
                "mean_score_lost_pp": mean(row["score_lost_pp"] for row in cohort) if complete else None,
                "affected_problems": sum(row["score_lost_pp"] > 1e-10 for row in cohort) if complete else None,
                "cache_preserving_mean_loss_pp": mean(row["cache_preserving_loss_pp"] for row in cohort) if ready else None,
                "globally_omittable_jobs_referenced": len(referenced_omitted) if ready else None,
                "globally_omittable_job_keys": sorted(referenced_omitted) if ready else None,
                "recorded_counters_of_referenced_omittable_jobs": summed_counters(referenced_omitted, jobs) if ready else None})
    omitted_rows = [{"job_key": key, "name": jobs[key]["name"], "origins": sorted(origins[key]),
        "copied_historical": key in historical, "result_sha256": hashes["jobs/" + key + "/result.json"],
        "recorded_counters": summed_counters({key}, jobs)} for key in sorted(omitted)]
    def job_group(keys):
        return {"unique_jobs": len(keys), "job_keys": sorted(keys), "recorded_counters": summed_counters(keys, jobs)}
    physical = {"complete": ready, "omitted": job_group(omitted) if ready else None,
        "omitted_copied_historical": job_group(omitted & historical) if ready else None,
        "omitted_without_recognized_copy_receipt": job_group(omitted - historical) if ready else None,
        "copied_historical_evidence": job_group(historical),
        "terminal_jobs_without_copy_receipt": job_group(set(jobs) - historical)}
    hashes["analysis_script"] = digest(Path(__file__))
    hashes["combined_report_reader"] = digest(Path(__file__).with_name("report_combined_matrix.py"))
    if (root / "jobs.json").exists():
        hashes["jobs.json"] = digest(root / "jobs.json")
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if ready else "incomplete", "input_directory": str(root),
        "expected_cells": len(planned), "recorded_cells": len(records), "conditions": conditions,
        "physical_work": physical, "omitted_jobs": omitted_rows if ready else None,
        "artifact_sha256": hashes, "copy_receipt_sha256": receipt_hashes,
        "limitations": [
            "Each condition selects only its own proof branches; there is no pooled proof portfolio.",
            "Primary counterfactual removes cleaned-F from cells rejected by stage03, retaining D1/L/D0 and only raw F strictly above D0+0.05. Original exact maximum and control-first tie order remain unchanged.",
            "Global physical omission removes a non-control job only if no accepted proposal origin needs it. Per-condition referenced job counts overlap and must not be summed.",
            "The cache-preserving diagnostic permits each cell's same-proof cleanup when another accepted origin still needs that physical job; it adds no different proof candidate.",
            "Global omission counts and the cache-preserving diagnostic remain null until the full matrix and controls complete.",
            "Counters describe recorded work, not exact runtime or checks saved under a counterfactual execution: changed cache history and ordering can alter cost.",
            "Optimizer counters exclude initial and final whole-proof verification; no elapsed-time savings are estimated.",
            "Copied historical counters are not new spend. Absence of a recognized copy receipt does not independently prove new execution; provide every applicable historical-copy receipt.",
            "Run the independent complete saved-matrix audit before final interpretation. This analysis is not a substitute for that audit's proof, lineage, and orphan-job checks.",
            "This is a post hoc deterministic analysis of one observed draw per cell, with no new model or Lean calls and no causal significance claim."]}
    return report, rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--copy-receipt", type=Path, action="append", default=[])
    parser.add_argument("--complete", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report, rows = analyze(args.input, receipts=args.copy_receipt, require_complete=args.complete)
    output = args.output or args.input / "analysis" / "rejected_cleanup"
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "report.json", report)
    write_csv(output / "per_problem.csv", rows, list(rows[0]))
    write_csv(output / "conditions.csv", report["conditions"], list(report["conditions"][0]))
    print(json.dumps({"status": report["status"], "output": str(output),
        "recorded_cells": report["recorded_cells"], "expected_cells": report["expected_cells"]}))


if __name__ == "__main__":
    main()
