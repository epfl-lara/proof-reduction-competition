"""Replay saved completed correctness-repair trajectories at budgets 0/1/2/3.

No model calls, Lean checks, resampling, or pooled proof selection. This analysis
uses the same recorded prefixes, not independent stochastic budget experiments.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean

from proof_eval.optimizer import score_improves
from report_one_shot import digest, finite_number, fmt, read_json, scores, write_csv, write_json
from report_repair_matrix import generation_statistics, load_run, raw_evaluation, required_versions
from run_validity_repair import unavailable
from validity_feedback import all_versions_passed


def can_continue(state, versions):
    return (not all_versions_passed(state["evaluation"], versions)
            and not unavailable(state["evaluation"])
            and state["generation"].get("status") == "received"
            and bool(state["proof"].strip()))


def replay_cell(pack, initial, trials, final):
    """Validate a terminal trajectory, then replay its four deterministic prefixes."""
    versions = required_versions(pack)
    generation = initial["generation"]
    states = [{"proof": initial.get("extracted_proof", generation.get("content", "")),
               "evaluation": initial["evaluation"], "generation": generation}]
    if len(trials) != final["round_count"] or len(trials) > 3:
        raise ValueError("Terminal round count differs from saved trajectory")
    for number, trial in enumerate(trials, 1):
        if trial["round"] != number or not can_continue(states[-1], versions):
            raise ValueError("Repair follows a terminal prefix or skips a round")
        states.append({key: trial[key] for key in ("proof", "evaluation", "generation")})
    if len(trials) < 3 and can_continue(states[-1], versions):
        raise ValueError("Terminal trajectory ended before its declared three-round limit")
    if states[-1]["proof"] != final["final_proof"] or states[-1]["evaluation"] != final["final_evaluation"]:
        raise ValueError("Saved final candidate differs from the last recorded prefix")
    baseline = scores(pack["incumbent"])["combined_pct"]
    replay = []
    for budget in range(4):
        used = min(budget, len(trials))
        state = states[used]
        valid = all_versions_passed(state["evaluation"], versions)
        returned = valid and state["proof"].strip() == pack["proof"].strip()
        accepted = bool(valid and score_improves(pack["incumbent"], state["evaluation"], .05))
        selected_evaluation = state["evaluation"] if accepted else pack["incumbent"]
        selected_proof = state["proof"] if accepted else pack["proof"]
        selected_score = scores(selected_evaluation)["combined_pct"]
        raw = scores(raw_evaluation(state["evaluation"]))["combined_pct"]
        events = [{"generation": trial["generation"]} for trial in trials[:used]]
        row = {"budget": budget, "repair_calls": used, "all_versions_valid": valid,
            "changed_valid": valid and not returned, "returned_incumbent": returned,
            "accepted_improvement": accepted, "raw_score": raw,
            "raw_unknown": not finite_number(raw), "baseline_score": baseline,
            "selected_score": selected_score, "selected_gain_pp": selected_score - baseline,
            "additional_generation": generation_statistics(events)}
        if budget == 3 and (valid != final["final_valid"] or returned != final["returned_incumbent"]
                or accepted != final["accepted"] or selected_proof != final["selected_proof"]
                or selected_evaluation != final["selected_evaluation"]):
            raise ValueError("Budget-three replay differs from the recorded final selection")
        replay.append(row)
    return replay


def summarize(rows, expected, previous=None):
    complete = len(rows) == expected
    selected = mean(row["selected_score"] for row in rows) if complete else None
    gain = mean(row["selected_gain_pp"] for row in rows) if complete else None
    raw = (mean(row["raw_score"] for row in rows)
           if complete and all(not row["raw_unknown"] for row in rows) else None)
    fields = generation_statistics([])
    generation = {key: sum(row["additional_generation"][key] for row in rows) for key in fields}
    result = {"expected_problems": expected, "recorded_complete_trajectories": len(rows), "complete": complete,
        "raw_mean": raw, "raw_unknown_outcomes": sum(row["raw_unknown"] for row in rows),
        "selected_mean": selected, "selected_gain_pp": gain,
        "all_versions_valid": sum(row["all_versions_valid"] for row in rows),
        "changed_valid": sum(row["changed_valid"] for row in rows),
        "returned_incumbent": sum(row["returned_incumbent"] for row in rows),
        "accepted_improvements": sum(row["accepted_improvement"] for row in rows),
        "additional_generation": generation}
    if previous is not None:
        result["marginal_selected_gain_pp"] = selected - previous["selected_mean"] if complete else None
        result["marginal_valid_proposals"] = result["all_versions_valid"] - previous["all_versions_valid"]
        result["marginal_changed_valid"] = result["changed_valid"] - previous["changed_valid"]
        result["marginal_incumbent_returns"] = result["returned_incumbent"] - previous["returned_incumbent"]
        result["marginal_accepted_improvements"] = result["accepted_improvements"] - previous["accepted_improvements"]
        result["marginal_generation"] = {key: generation[key] - previous["additional_generation"][key] for key in fields}
    return result


def analyze(root, *, require_complete=False):
    root = Path(root).resolve()
    config, base_config, base, inputs, cells, by_condition, initials, finals, _, _, hashes = load_run(root)
    if config["max_rounds"] != 3:
        raise ValueError("Four-budget replay requires a declared maximum of three repairs")
    if any(set(names) != set(base_config["names"]) for names in by_condition.values()):
        raise ValueError("Budget analysis requires the full original theorem cohort per condition")
    complete = len(finals) == len(cells)
    if require_complete and not complete:
        raise ValueError("The declared repair matrix is incomplete")
    problems, replays = [], {}
    for key, final in finals.items():
        name, arm, model = cells[key]["logical"]
        trials = [read_json(root / "cells" / key / "rounds" / f"{number:02d}" / "result.json")
                  for number in range(1, final["round_count"] + 1)]
        replays[key] = replay_cell(inputs[name], initials[key], trials, final)
        for row in replays[key]:
            problems.append({"key": key, "name": name, "source": inputs[name]["row"]["source"],
                "model": model, "arm": arm, **row})
    conditions = []
    for model, arm in by_condition:
        cohort = [row for row in problems if row["model"] == model and row["arm"] == arm]
        previous = None
        for budget in range(4):
            result = summarize([row for row in cohort if row["budget"] == budget],
                               len(by_condition[model, arm]), previous)
            conditions.append({"model": model, "arm": arm, "budget": budget, **result})
            previous = result
    diagnostic_totals = []
    for budget in range(4):
        # Counts/costs may be summed across requests; no pooled competition mean.
        result = summarize([row for row in problems if row["budget"] == budget], len(cells))
        for key in ("raw_mean", "selected_mean", "selected_gain_pp"):
            del result[key]
        diagnostic_totals.append({"budget": budget, **result})
    marginal = []
    if complete:
        for key, replay in replays.items():
            name, arm, model = cells[key]["logical"]
            for budget in (1, 2, 3):
                delta = replay[budget]["selected_score"] - replay[budget - 1]["selected_score"]
                if delta > 1e-10:
                    before, after = replay[budget - 1], replay[budget]
                    marginal.append({"key": key, "name": name, "model": model, "arm": arm,
                        "round": budget, "selected_gain_pp": delta,
                        "from_score": before["selected_score"], "to_score": after["selected_score"],
                        "additional_generation": {field: after["additional_generation"][field]
                            - before["additional_generation"][field] for field in before["additional_generation"]}})
    for relative in ("matrix_config.json", "config.json"):
        if (root / relative).exists():
            hashes[relative] = digest(root / relative)
    for path in [base / "config.json", *sorted((base / "inputs").glob("*.json"))]:
        hashes["base/" + str(path.relative_to(base))] = digest(path)
    for filename in ("analyze_repair_budgets.py", "report_repair_matrix.py", "run_validity_repair.py",
                     "validity_feedback.py", "proof_eval/optimizer.py"):
        hashes["source/" + filename] = digest(Path(__file__).parent / filename)
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if complete else "incomplete", "input_directory": str(root),
        "base_directory": str(base), "expected_cells": len(cells), "terminal_cells": len(finals),
        "baseline_mean": mean(scores(inputs[name]["incumbent"])["combined_pct"] for name in base_config["names"]),
        "conditions": conditions, "diagnostic_totals": diagnostic_totals,
        "initial_generation_for_completed_trajectories": generation_statistics(
            [{"generation": initials[key]["generation"]} for key in finals]),
        "positive_marginal_outcomes": sorted(marginal, key=lambda row: (-row["selected_gain_pp"], row["key"])),
        "artifact_sha256": hashes, "limitations": [
            "These are deterministic replays of saved prefixes, not newly sampled stochastic experiments at each budget.",
            "Only complete terminal trajectories enter any budget; a condition mean requires every declared proof. Pending trajectory prefixes are excluded even from budget zero.",
            "The first all-version-valid candidate stops repair even if it is inferior. Empty outputs and unavailable outcomes stop too; no later candidate is fabricated.",
            "Selection preserves the exact strict score > D0 + 0.05 threshold and otherwise retains D0. Unknown raw scores remain null; known invalid/failed outputs have zero raw score.",
            "Calls and known provider usage are cumulative additional repairs. Reasoning tokens are part of completion tokens; missing usage is counted rather than estimated.",
            "Each declared cell is counted once, including copied completed trajectories. Do not add original or pilot folders to continuation totals.",
            "Duration sums include overlapping service/admission waiting and are not model latency or counterfactual elapsed-time savings.",
            "Budget replays share the same sampled prefixes and have no significance claim. Their outcomes do not cover post-model deterministic cleanup.",
            "Run the independent saved-evidence audit before final interpretation; this report executes no model or Lean calls."]}
    return report, problems


def markdown(report):
    lines = ["# Recorded repair budgets", "", f"**{report['status']}**: {report['terminal_cells']}/{report['expected_cells']} "
             "terminal trajectories available. Budgets 0/1/2/3 replay the same saved proposals and repair prefixes.", "",
             f"D0 averages **{report['baseline_mean']:.6f}%** local combined score. Means remain blank for incomplete conditions.", "",
             "| Model | Arm | Complete / expected | L at 0 | L at 1 | L at 2 | L at 3 |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    grouped = {}
    for condition in report["conditions"]:
        grouped.setdefault((condition["model"], condition["arm"]), []).append(condition)
    for (model, arm), rows in grouped.items():
        lines.append(f"| {model.split('/')[-1]} | {arm} | {rows[0]['recorded_complete_trajectories']}/{rows[0]['expected_problems']} | "
                     + " | ".join(fmt(row["selected_mean"]) for row in rows) + " |")
    lines += ["", "The following count sequences correspond to budgets **0 / 1 / 2 / 3**. They concern the same completed trajectories in each row; they are not independent samples.", "",
        "| Model | Arm | All-version valid | Changed valid | Returned incumbent | Accepted improvement |",
        "| --- | --- | ---: | ---: | ---: | ---: |"]
    for (model, arm), rows in grouped.items():
        counts = [" / ".join(str(row[field]) for row in rows)
                  for field in ("all_versions_valid", "changed_valid", "returned_incumbent", "accepted_improvements")]
        lines.append(f"| {model.split('/')[-1]} | {arm} | " + " | ".join(counts) + " |")
    lines += ["", "These diagnostic totals sum physical request records represented once in this directory; they do not form a pooled proof score. Each budget is cumulative: do not add the four rows together. Only completed trajectories are included. Initial calls are separate and shared by every replay.", "",
        "| Maximum repairs | Extra calls | Known prompt tokens | Known completion tokens | Usage missing | Empty length-truncated outputs |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in report["diagnostic_totals"]:
        g = row["additional_generation"]
        lines.append(f"| {row['budget']} | {g['request_attempts']} | {g['prompt_tokens']:,} | {g['completion_tokens']:,} | "
                     f"{g['usage_missing_generations']} | {g['truncated_empty_final_with_reasoning']} |")
    lines += ["", "Full per-condition cumulative and marginal usage, selected-score gains, raw unknown outcomes, and provenance hashes are in [report.json](report.json). [per_problem.csv](per_problem.csv) contains the exact replayed prefixes; [conditions.csv](conditions.csv) contains budget-specific condition statistics.", ""]
    if report["status"] == "complete":
        lines += ["The largest observed individual marginal gains are listed below. This is a post hoc description of saved outcomes, not a proof portfolio or evidence that a later round will help a new request.", "",
            "| Model | Arm | Proof | Additional round | Selected gain pp |", "| --- | --- | --- | ---: | ---: |"]
        for row in report["positive_marginal_outcomes"][:8]:
            lines.append(f"| {row['model'].split('/')[-1]} | {row['arm']} | `{row['name']}` | {row['round']} | {row['selected_gain_pp']:+.6f} |")
    lines += ["", *["- " + item for item in report["limitations"]], ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--complete", action="store_true")
    args = parser.parse_args(argv)
    report, problems = analyze(args.input, require_complete=args.complete)
    output = args.output or args.input / "analysis" / "repair_budgets"
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "report.json", report)
    flat = [{**{key: value for key, value in row.items() if key != "additional_generation"},
             **{"repair_" + key: value for key, value in row["additional_generation"].items()}} for row in problems]
    if flat:
        write_csv(output / "per_problem.csv", flat, list(flat[0]))
    else:
        write_csv(output / "per_problem.csv", [], ["key", "name", "model", "arm", "budget", "selected_score"])
    write_csv(output / "conditions.csv", report["conditions"], list(dict.fromkeys(
        key for row in report["conditions"] for key in row)))
    (output / "README.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "terminal_cells": report["terminal_cells"],
                      "expected_cells": report["expected_cells"], "output": str(output)}))


if __name__ == "__main__":
    main()
