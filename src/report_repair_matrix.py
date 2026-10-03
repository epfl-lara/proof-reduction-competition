"""Read-only reporting for one optimization proposal plus validity-only repairs.

No model calls, Lean execution, prompt changes, or pooled best-of-arm selection.
Initial proposals and repaired outcomes have separate completion denominators.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean

from report_one_shot import (
    CONTRASTS, FIELDS, average_scores, complete_scores, digest, finite_number,
    fmt, read_json, scores, write_csv, write_json,
)
from validity_feedback import all_versions_passed


def required_versions(pack):
    return [version for item in pack["row"]["version_info"] for version in item]


def raw_evaluation(evaluation):
    """Keep infrastructure uncertainty distinct from a rejected candidate."""
    if evaluation.get("status") in {"invalid", "failed"}:
        return {"scores": dict.fromkeys(FIELDS, 0.0)}
    if evaluation.get("status") in {"unavailable", "incomplete"} or any(
            check.get("status") == "unavailable" for check in evaluation.get("per_version", {}).values()):
        return {"scores": dict.fromkeys(FIELDS, None)}
    return evaluation


def cohort_mean(evaluations, expected):
    return average_scores(evaluations) if len(evaluations) == expected else dict.fromkeys(FIELDS, None)


def generation_statistics(events):
    """One event per request directory; omit unknown usage rather than invent it."""
    generations = [event["generation"] for event in events if event.get("generation") is not None]
    def usage(generation):
        value = generation.get("usage")
        return value if isinstance(value, dict) else {}
    def reasoning(generation):
        value = usage(generation).get("completion_tokens_details")
        return value.get("reasoning_tokens") if isinstance(value, dict) else None
    def count_tokens(key):
        return sum(usage(g).get(key, 0) for g in generations if finite_number(usage(g).get(key, 0)))
    return {
        "request_attempts": len(events), "saved_generations": len(generations),
        "pending_generations": len(events) - len(generations),
        "received": sum(g.get("status") == "received" for g in generations),
        "transport_errors": sum(g.get("status") == "transport_error" for g in generations),
        "indeterminate": sum(g.get("status") == "indeterminate" for g in generations),
        "truncated": sum(g.get("finish_reason") == "length" for g in generations),
        "empty_final": sum(g.get("status") == "received" and not g.get("content", "").strip() for g in generations),
        "truncated_empty_final_with_reasoning": sum(
            g.get("status") == "received" and g.get("finish_reason") == "length"
            and not g.get("content", "").strip()
            and ((reasoning(g) or 0) > 0 or (g.get("reasoning_characters") or 0) > 0) for g in generations),
        "prompt_tokens": count_tokens("prompt_tokens"), "completion_tokens": count_tokens("completion_tokens"),
        "reasoning_tokens": sum(reasoning(g) for g in generations if finite_number(reasoning(g))),
        "usage_missing_generations": sum(not all(finite_number(usage(g).get(k)) for k in (
            "prompt_tokens", "completion_tokens")) for g in generations),
        "reasoning_tokens_missing_generations": sum(not finite_number(reasoning(g)) for g in generations),
        "request_elapsed_seconds_sum": sum(g.get("elapsed_seconds", 0) for g in generations
                                            if finite_number(g.get("elapsed_seconds", 0))),
    }


def read_generation_event(folder, embedded=None):
    generation_path = folder / "generation.json"
    generation = read_json(generation_path) if generation_path.exists() else embedded
    if generation is None and not (folder / "request_started.json").exists():
        return None
    return {"generation": generation}


def load_run(root, base_override=None):
    declaration = root / "matrix_config.json"
    if not declaration.exists():
        declaration = root / "config.json"
    config = read_json(declaration)
    base = Path(base_override if base_override is not None else config["base_directory"])
    if not base.is_absolute():
        base = root / base
    base = base.resolve()
    base_config = read_json(base / "config.json")
    if config.get("base_config_sha256") != digest(base / "config.json"):
        raise ValueError("Saved base configuration changed")
    base_index = read_json(base / "cell_index.json")
    if config.get("base_index_sha256") and config["base_index_sha256"] != digest(base / "cell_index.json"):
        raise ValueError("Saved base cell index changed")
    if config.get("base_input_hashes_sha256") and config["base_input_hashes_sha256"] != digest(base / "input_hashes.json"):
        raise ValueError("Saved input manifest changed")
    inputs = {}
    for path in (base / "inputs").glob("*.json"):
        expected_hash = config.get("input_files_sha256", {}).get(str(path.relative_to(base)))
        if expected_hash is not None and digest(path) != expected_hash:
            raise ValueError("Saved incumbent input changed")
        pack = read_json(path)
        if pack["name"] in inputs:
            raise ValueError("Duplicate input pack")
        if not complete_scores(pack.get("incumbent", {})):
            raise ValueError("Unscored incumbent")
        inputs[pack["name"]] = pack
    cells, by_condition = {}, {}
    for cell in config["cells"]:
        key = cell["key"]
        name, arm, model = cell["logical"]
        if key in cells or base_index.get(json.dumps([name, arm, model])) != key:
            raise ValueError("Duplicate or mismatched planned cell")
        if name not in inputs or name not in base_config["names"]:
            raise ValueError("Missing configured incumbent")
        if model not in base_config["models"] or arm not in base_config["arms"]:
            raise ValueError("Planned model or arm is outside the base configuration")
        cells[key] = cell
        by_condition.setdefault((model, arm), []).append(name)
    if not cells:
        raise ValueError("The declared cohort is empty")
    for names in by_condition.values():
        if len(set(names)) != len(names):
            raise ValueError("Duplicate problem in condition")
        names.sort(key=base_config["names"].index)
    initials, finals, initial_events, repair_events, evidence_hashes = {}, {}, {}, {}, {}
    for key, cell in cells.items():
        name, arm, model = cell["logical"]
        pack = inputs[name]
        initial_path = base / "cells" / key / "result.json"
        if initial_path.exists():
            initial = read_json(initial_path)
            if [initial["name"], initial["arm"], initial["model"]] != cell["logical"] or initial["request_sha256"] != key:
                raise ValueError("Initial record identity changed")
            if cell.get("result_sha256") and digest(initial_path) != cell["result_sha256"]:
                raise ValueError("Initial result differs from repair cohort")
            initials[key] = initial
            evidence_hashes["base/cells/" + key + "/result.json"] = digest(initial_path)
        event = read_generation_event(initial_path.parent, initials.get(key, {}).get("generation"))
        initial_events[key] = [event] if event else []
        folder = root / "cells" / key
        # Read the terminal marker before scanning rounds. If it exists, all
        # its immutable rounds must already exist; a live arrival cannot make
        # an earlier round scan look spuriously incomplete.
        final_path = folder / "result.json"
        final = read_json(final_path) if final_path.exists() else None
        if final is not None and key not in initials and initial_path.exists():
            initial = read_json(initial_path)
            if [initial["name"], initial["arm"], initial["model"]] != cell["logical"] or initial["request_sha256"] != key:
                raise ValueError("Initial record identity changed")
            initials[key] = initial
            evidence_hashes["base/cells/" + key + "/result.json"] = digest(initial_path)
            event = read_generation_event(initial_path.parent, initial.get("generation"))
            initial_events[key] = [event] if event else []
        rounds, events = {}, []
        for round_folder in sorted((folder / "rounds").glob("*")):
            if not round_folder.is_dir() or not round_folder.name.isdigit():
                continue
            number = int(round_folder.name)
            if not 1 <= number <= config["max_rounds"] or number in rounds:
                raise ValueError("Unexpected repair round")
            trial_path = round_folder / "result.json"
            trial = read_json(trial_path) if trial_path.exists() else None
            if trial:
                if trial["round"] != number:
                    raise ValueError("Round identity mismatch")
                rounds[number] = trial
                evidence_hashes[str(trial_path.relative_to(root))] = digest(trial_path)
            event = read_generation_event(round_folder, trial.get("generation") if trial else None)
            if event:
                events.append(event)
        repair_events[key] = events
        if final is None:
            continue
        if key not in initials:
            raise ValueError("Completed repair has no saved initial result")
        if [final["name"], final["arm"], final["model"]] != cell["logical"] or final["base_request_sha256"] != key:
            raise ValueError("Repair identity mismatch")
        if final["source"] != pack["row"]["source"]:
            raise ValueError("Repair source mismatch")
        if final["round_count"] != len(rounds) or set(rounds) != set(range(1, final["round_count"] + 1)):
            raise ValueError("Saved repair rounds are incomplete")
        if final["round_count"] > config["max_rounds"] or len(final["rounds"]) != final["round_count"]:
            raise ValueError("Repair round count exceeds declared limit")
        initial_valid = all_versions_passed(initials[key]["evaluation"], required_versions(pack))
        final_valid = all_versions_passed(final["final_evaluation"], required_versions(pack))
        if final["initial_valid"] != initial_valid or final["final_valid"] != final_valid:
            raise ValueError("Recorded all-version validity disagrees with saved compiler checks")
        if final["returned_incumbent"] != (final_valid and final["final_proof"].strip() == pack["proof"].strip()):
            raise ValueError("Returned-incumbent label disagrees with saved proof")
        if not complete_scores(final["selected_evaluation"]):
            raise ValueError("Selected repair score is incomplete")
        if final["accepted"]:
            if not final_valid or final["selected_proof"] != final["final_proof"] or final["selected_evaluation"] != final["final_evaluation"]:
                raise ValueError("Accepted selection disagrees with final valid candidate")
        elif final["selected_proof"] != pack["proof"] or scores(final["selected_evaluation"]) != scores(pack["incumbent"]):
            raise ValueError("Fallback disagrees with original incumbent")
        for number, trial in rounds.items():
            if trial["request_sha256"] != final["rounds"][number - 1]["request_sha256"]:
                raise ValueError("Round request identity mismatch")
        finals[key] = final
        evidence_hashes[str(final_path.relative_to(root))] = digest(final_path)
    unexpected = {path.parent.name for path in (root / "cells").glob("*/result.json")} - set(cells)
    if unexpected:
        raise ValueError("Results outside the predeclared cohort")
    return config, base_config, base, inputs, cells, by_condition, initials, finals, initial_events, repair_events, evidence_hashes


def summarize(keys, cells, inputs, initials, finals, initial_events, repair_events):
    before = [initials[key] for key in keys if key in initials]
    after = [finals[key] for key in keys if key in finals]
    expected = len(keys)
    baseline = average_scores([inputs[cells[key]["logical"][0]]["incumbent"] for key in keys])
    initial_raw = [raw_evaluation(record["evaluation"]) for record in before]
    final_raw = [raw_evaluation(record["final_evaluation"]) for record in after]
    initial_selected = cohort_mean([record["selected_evaluation"] for record in before], expected)
    selected = cohort_mean([record["selected_evaluation"] for record in after], expected)
    paired_initial = [initials[key] for key in keys if key in finals]
    selected_change = [scores(finals[key]["selected_evaluation"])["combined_pct"]
                       - scores(initials[key]["selected_evaluation"])["combined_pct"] for key in keys if key in finals]
    return {
        "expected_problems": expected, "initial_recorded": len(before), "repair_recorded": len(after),
        "initial_complete": len(before) == expected, "repair_complete": len(after) == expected,
        "initial_scored": sum(complete_scores(e) for e in initial_raw),
        "repaired_scored": sum(complete_scores(e) for e in final_raw),
        "baseline_mean": baseline, "initial_raw_mean": cohort_mean(initial_raw, expected),
        "repaired_raw_mean": cohort_mean(final_raw, expected), "initial_selected_mean": initial_selected,
        "selected_mean": selected,
        "selected_gain_pp": selected["combined_pct"] - baseline["combined_pct"] if len(after) == expected else None,
        "repair_selected_delta_pp": mean(selected_change) if len(after) == expected else None,
        "observed_initial_raw_mean": average_scores([e for e in initial_raw if complete_scores(e)]),
        "observed_repaired_raw_mean": average_scores([e for e in final_raw if complete_scores(e)]),
        "observed_selected_mean": average_scores([r["selected_evaluation"] for r in after]),
        "initial_all_versions_valid": sum(all_versions_passed(record["evaluation"], required_versions(inputs[record["name"]])) for record in before),
        "paired_initial_all_versions_valid": sum(all_versions_passed(record["evaluation"], required_versions(inputs[record["name"]])) for record in paired_initial),
        "final_all_versions_valid": sum(record["final_valid"] for record in after),
        "repaired_valid": sum(not record["initial_valid"] and record["final_valid"] for record in after),
        "returned_incumbent": sum(record["returned_incumbent"] for record in after),
        "returned_incumbent_after_repair": sum(record["returned_incumbent"] and record["round_count"] > 0 for record in after),
        "valid_changed_proposals": sum(record["final_valid"] and not record["returned_incumbent"] for record in after),
        "accepted_improvements": sum(record["accepted"] for record in after),
        "initial_accepted_improvements": sum(bool(record.get("accepted")) for record in before),
        "outcomes": dict(sorted(Counter(record["outcome"] for record in after).items())),
        "initial_kinds": dict(sorted(Counter(record["initial_kind"] for record in after).items())),
        "round_counts_completed_cells": dict(sorted(Counter(str(record["round_count"]) for record in after).items())),
        "initial_generation": generation_statistics([event for key in keys for event in initial_events.get(key, [])]),
        "additional_repair_generation": generation_statistics([event for key in keys for event in repair_events.get(key, [])]),
    }


def paired_effects(base_config, cells, by_condition, finals, inputs):
    logical = {(cell["logical"][2], cell["logical"][1], cell["logical"][0]): key for key, cell in cells.items()}
    summaries, rows = [], []
    for model in base_config["models"]:
        for label, weights in CONTRASTS.items():
            if any((model, arm) not in by_condition for arm in weights):
                continue
            cohort = [name for name in base_config["names"] if all(name in by_condition[model, arm] for arm in weights)]
            if not cohort:
                continue
            observed = [name for name in cohort if all(logical[model, arm, name] in finals for arm in weights)]
            values, accepted_values = [], []
            for name in observed:
                records = {arm: finals[logical[model, arm, name]] for arm in weights}
                value = sum(weight * scores(records[arm]["selected_evaluation"])["combined_pct"] for arm, weight in weights.items())
                accepted = sum(weight * bool(records[arm]["accepted"]) for arm, weight in weights.items())
                values.append(value)
                accepted_values.append(accepted)
                rows.append({"model": model, "contrast": label, "name": name,
                             "source": inputs[name]["row"]["source"], "corrected_selected_delta_pp": value,
                             "accepted_indicator_delta": accepted})
            summaries.append({"model": model, "contrast": label, "weights": weights,
                              "expected_pairs": len(cohort), "recorded_pairs": len(observed),
                              "corrected_selected_mean_delta_pp": mean(values) if len(observed) == len(cohort) else None,
                              "accepted_rate_delta_pp": 100 * mean(accepted_values) if len(observed) == len(cohort) else None,
                              "observed_corrected_selected_mean_delta_pp": mean(values) if values else None,
                              "positive_pairs": sum(v > 1e-10 for v in values),
                              "negative_pairs": sum(v < -1e-10 for v in values),
                              "tied_pairs": sum(abs(v) <= 1e-10 for v in values)})
    return summaries, rows


def build_report(root, base_override=None):
    config, base_config, base, inputs, cells, by_condition, initials, finals, initial_events, repair_events, hashes = load_run(root, base_override)
    conditions, sources, problems = [], [], []
    ordered_conditions = [(model, arm) for model in base_config["models"] for arm in base_config["arms"] if (model, arm) in by_condition]
    for model, arm in ordered_conditions:
        keys = [key for key, cell in cells.items() if cell["logical"][1:] == [arm, model]]
        condition = {"model": model, "arm": arm, **summarize(keys, cells, inputs, initials, finals, initial_events, repair_events)}
        conditions.append(condition)
        source_names = sorted({inputs[cells[key]["logical"][0]]["row"]["source"] for key in keys})
        for source in source_names:
            subset = [key for key in keys if inputs[cells[key]["logical"][0]]["row"]["source"] == source]
            sources.append({"model": model, "arm": arm, "source": source,
                            **summarize(subset, cells, inputs, initials, finals, initial_events, repair_events)})
        for key in keys:
            name = cells[key]["logical"][0]
            initial, final = initials.get(key), finals.get(key)
            row = {"model": model, "arm": arm, "name": name, "source": inputs[name]["row"]["source"],
                   "base_request_sha256": key, "initial_recorded": initial is not None, "repair_recorded": final is not None,
                   "baseline_score": scores(inputs[name]["incumbent"])["combined_pct"],
                   "initial_raw_score": scores(raw_evaluation(initial["evaluation"])).get("combined_pct") if initial else None,
                   "initial_selected_score": scores(initial["selected_evaluation"])["combined_pct"] if initial else None,
                   "repaired_raw_score": scores(raw_evaluation(final["final_evaluation"])).get("combined_pct") if final else None,
                   "selected_score": scores(final["selected_evaluation"])["combined_pct"] if final else None,
                   "initial_valid": all_versions_passed(initial["evaluation"], required_versions(inputs[name])) if initial else None,
                   "final_valid": final["final_valid"] if final else None,
                   "returned_incumbent": final["returned_incumbent"] if final else None,
                   "accepted": final["accepted"] if final else None,
                   "round_count": final["round_count"] if final else None,
                   "outcome": final["outcome"] if final else None,
                   "additional_requests_recorded": len(repair_events.get(key, [])),
                   "selected_gain_pp": scores(final["selected_evaluation"])["combined_pct"] - scores(inputs[name]["incumbent"])["combined_pct"] if final else None}
            problems.append(row)
    effects, pairwise = paired_effects(base_config, cells, by_condition, finals, inputs)
    cohort_names = [name for name in base_config["names"] if any(cell["logical"][0] == name for cell in cells.values())]
    report = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if len(finals) == len(cells) else "incomplete",
        "planned_cells": len(cells), "initial_recorded_cells": len(initials), "repair_recorded_cells": len(finals),
        "problem_count": len(cohort_names), "base_problem_count": len(base_config["names"]),
        "base_names": base_config["names"],
        "base_directory": str(base), "max_repair_rounds": config["max_rounds"],
        "generation_settings": {key: base_config.get(key) for key in ("temperature", "reasoning_effort", "max_tokens")},
        "baseline_mean": average_scores([inputs[name]["incumbent"] for name in cohort_names]),
        "cohort_is_full_base_matrix": len(cells) == len(base_config["names"]) * len(base_config["models"]) * len(base_config["arms"]),
        "conditions": conditions, "sources": sources, "paired_contrasts": effects,
        "totals": summarize(list(cells), cells, inputs, initials, finals, initial_events, repair_events),
        "artifact_sha256": {**hashes, "base/config.json": digest(base / "config.json"),
                             "matrix_config.json" if (root / "matrix_config.json").exists() else "config.json":
                             digest(root / ("matrix_config.json" if (root / "matrix_config.json").exists() else "config.json"))},
        "limitations": [
            "One initial optimization proposal plus up to three correctness-only debugging calls; this is not a single HTTP call.",
            "The first all-version-valid proposal stops debugging. Scores affect only final incumbent selection, not feedback or continuation.",
            "A return to the supplied incumbent is counted separately from a valid changed proposal and an accepted improvement.",
            "Empty output, infrastructure failure, or exhausted repair budget can leave a proposal unusable; fallback is reported separately.",
            "Unknown infrastructure outcomes have null raw scores. Invalid and failed declarations score zero.",
            "Context effects are descriptive paired differences from one stochastic proposal per cell, not statistical significance or causal proof.",
            "Conditions can consume different numbers of repair calls; paired score differences are not equal-cost comparisons.",
            "Request durations overlap under concurrency; saved duration sums are not experiment wall time. Missing usage is not estimated.",
            "This report reads saved artifacts, does not recompile proofs, and creates no pooled best-of-arms portfolio.",
        ],
    }
    return report, problems, pairwise


def export_complete_conditions(root, output, report, problems):
    """Export each complete original cohort, without pooling its conditions."""
    exports = []
    names = report["base_names"]
    for condition in report["conditions"]:
        model, arm = condition["model"], condition["arm"]
        rows = [row for row in problems if row["model"] == model and row["arm"] == arm]
        if (not condition["repair_complete"] or len(rows) != len(names)
                or {row["name"] for row in rows} != set(names)):
            continue
        by_name = {row["name"]: row for row in rows}
        candidates, provenance = [], []
        for name in names:
            row = by_name[name]
            result_path = root / "cells" / row["base_request_sha256"] / "result.json"
            result_hash = digest(result_path)
            if result_hash != report["artifact_sha256"][str(result_path.relative_to(root))]:
                raise ValueError("Repair result changed during report export")
            record = read_json(result_path)
            proof = record["selected_proof"]
            candidates.append({"name": name, "proof": proof})
            provenance.append({"name": name, "base_request_sha256": row["base_request_sha256"],
                               "repair_result_sha256": result_hash, "accepted": record["accepted"],
                               "returned_incumbent": record["returned_incumbent"],
                               "selected_scores": scores(record["selected_evaluation"]),
                               "selected_proof_sha256": hashlib.sha256(proof.encode("utf-8")).hexdigest()})
        relative = Path("conditions") / (model.split("/")[-1] + "__" + arm)
        folder = output / relative
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "selected_candidates.jsonl"
        temporary = target.with_suffix(".jsonl.tmp")
        temporary.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in candidates), encoding="utf-8")
        temporary.replace(target)
        candidate_hash = digest(target)
        manifest = {"schema_version": 1, "created_at": report["created_at"], "model": model, "arm": arm,
                    "scope": "One original proposal plus bounded validity-only repairs per theorem; this condition only, no pooling.",
                    "problem_count": len(names), "names": names, "max_repair_rounds": report["max_repair_rounds"],
                    "base_config_sha256": report["artifact_sha256"]["base/config.json"],
                    "baseline_mean": condition["baseline_mean"], "selected_mean": condition["selected_mean"],
                    "selected_gain_pp": condition["selected_gain_pp"], "accepted_improvements": condition["accepted_improvements"],
                    "candidates_sha256": candidate_hash, "problems": provenance,
                    "verification": "Selection uses the saved all-version evaluations; this export performs no new Lean execution."}
        write_json(folder / "manifest.json", manifest)
        exports.append({"model": model, "arm": arm, "problem_count": len(names),
                        "submission": str(relative / "selected_candidates.jsonl"),
                        "manifest": str(relative / "manifest.json"), "candidates_sha256": candidate_hash})
    return exports


def markdown(report):
    settings = report["generation_settings"]
    lines = ["# Context ablation with correctness-only repairs", "",
        f"**{report['status']}**: {report['initial_recorded_cells']}/{report['planned_cells']} initial proposals recorded; "
        f"{report['repair_recorded_cells']}/{report['planned_cells']} repair outcomes complete. "
        f"The shared deterministic incumbent averages **{report['baseline_mean']['combined_pct']:.6f}%** "
        f"local combined score on the {report['problem_count']}-proof declared cohort.", "",
        f"Each cell starts from one saved optimization proposal and permits up to **{report['max_repair_rounds']} "
        "correctness-only debugging calls**. The debugger sees compiler validity feedback and the known-valid incumbent; "
        "it receives no candidate scores, heartbeat measurements, or reward feedback. It stops at the first proof passing "
        "all required versions. Final score comparison occurs only after debugging ends. Empty initial output is not regenerated.", "",
        f"Generation settings remain temperature {settings['temperature']}, {settings['reasoning_effort']} reasoning, "
        f"and {settings['max_tokens']:,} output tokens. This protocol is one optimization proposal plus bounded repairs, "
        "not one HTTP request. Initial calls and additional repair calls are counted separately.", "",
        "## Candidate scores and validity", "",
        "Raw scores concern the generated candidate. Selected scores retain the incumbent when the final proposal "
        "is invalid, unavailable, or not accepted. Unknown infrastructure results leave a raw mean blank; failed or "
        "invalid declarations contribute zero. Full means remain blank until their own declared cohort completes. "
        "Initial proposals can finish before their repair outcomes.", "",
        "| Model | Arm | Initial / repaired / expected | Initial raw | Repaired raw | Selected | Gain pp | Valid initial / final | Incumbent returned | Improved |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for c in report["conditions"]:
        lines.append(f"| {c['model'].split('/')[-1]} | {c['arm']} | {c['initial_recorded']}/{c['repair_recorded']}/{c['expected_problems']} "
            f"| {fmt(c['initial_raw_mean']['combined_pct'])} | {fmt(c['repaired_raw_mean']['combined_pct'])} "
            f"| {fmt(c['selected_mean']['combined_pct'])} | {fmt(c['selected_gain_pp'], True)} "
            f"| {c['initial_all_versions_valid']}/{c['final_all_versions_valid']} | {c['returned_incumbent']} | {c['accepted_improvements']} |")
    if not report["cohort_is_full_base_matrix"]:
        lines += ["", "**This is an explicitly selected subset, not the full base matrix.** Each condition's expected count comes from its declared cells."]
    totals = report["totals"]
    lines += ["", f"Among completed repair cells: {totals['repaired_valid']} initially invalid proposals became all-version valid; "
        f"{totals['returned_incumbent_after_repair']} returned the unchanged incumbent after debugging. "
        f"There are {totals['valid_changed_proposals']} valid changed proposals and {totals['accepted_improvements']} accepted improvements. "
        "Validity recovery alone is not proof optimization. The JSON also records initial-selected scores and the paired gain due to repair.", "",
        "## Additional calls and costs", "",
        "Counts include saved generations and durable request-start markers, including pending repairs. "
        "An attempt without a saved generation has unknown usage. Token counts are provider-reported; reasoning tokens, "
        "where reported, are a subset of completion tokens and must not be added a second time.", "",
        "| Model | Arm | Initial calls | Extra repair calls | Repair pending | Initial prompt / completion | Repair prompt / completion | Repair trunc. | Repair empty-final trunc. with reasoning | Repair request seconds sum |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for c in report["conditions"]:
        initial, repair = c["initial_generation"], c["additional_repair_generation"]
        lines.append(f"| {c['model'].split('/')[-1]} | {c['arm']} | {initial['request_attempts']} | {repair['request_attempts']} "
            f"| {repair['pending_generations']} | {initial['prompt_tokens']:,}/{initial['completion_tokens']:,} "
            f"| {repair['prompt_tokens']:,}/{repair['completion_tokens']:,} | {repair['truncated']} "
            f"| {repair['truncated_empty_final_with_reasoning']} | {repair['request_elapsed_seconds_sum']:.1f} |")
    initial, repair = totals["initial_generation"], totals["additional_repair_generation"]
    lines += ["", f"Initial / repair generation failures: transport {initial['transport_errors']}/{repair['transport_errors']}, "
        f"indeterminate {initial['indeterminate']}/{repair['indeterminate']}, length-truncated {initial['truncated']}/{repair['truncated']}. "
        f"Missing usage affects {initial['usage_missing_generations']}/{repair['usage_missing_generations']} saved generations. "
        "Request seconds are summed overlapping durations, not end-to-end wall time. No monetary price is inferred.", "",
        "## Paired effects of the initial context", "",
        "The original arms differ in cards, goal annotations, and original-tactic cost context. Debugging uses the same "
        "correctness-only message contract for all arms. Each comparison pairs the same model and proof, using final "
        "incumbent-selected scores. Different repair-call counts mean these are not matched-cost comparisons. "
        "One stochastic proposal per cell provides descriptive evidence, not statistical significance.", "",
        "| Model | Cards − plain | Goals − plain | Cards+goals − plain | Cards+goals+costs − plain | Costs − cards+goals |",
        "| --- | ---: | ---: | ---: | ---: | ---: |"]
    effects = {(c["model"], c["contrast"]): c for c in report["paired_contrasts"]}
    models = list(dict.fromkeys(c["model"] for c in report["conditions"]))
    for model in models:
        values = [fmt(effects.get((model, label), {}).get("corrected_selected_mean_delta_pp"), True) for label in
                  ("cards_minus_plain", "goals_minus_plain", "cards_goals_minus_plain", "cards_goals_costs_minus_plain", "costs_minus_cards_goals")]
        lines.append("| " + model.split("/")[-1] + " | " + " | ".join(values) + " |")
    lines += ["", "Card main effect = average of `(cards − plain)` and `(cards_goals − goals)`; "
        "goal main effect = average of `(goals − plain)` and `(cards_goals − cards)`; "
        "interaction = `cards_goals − cards − goals + plain`. Cost context is isolated by "
        "`cards_goals_costs − cards_goals`. The JSON reports the same contrasts on accepted-improvement rates.", "",
        "| Model | Card effect pp | Goal effect pp | Interaction pp |", "| --- | ---: | ---: | ---: |"]
    for model in models:
        values = [fmt(effects.get((model, label), {}).get("corrected_selected_mean_delta_pp"), True) for label in
                  ("cards_main_effect", "goals_main_effect", "cards_goals_interaction")]
        lines.append("| " + model.split("/")[-1] + " | " + " | ".join(values) + " |")
    lines += ["", "## Evidence", "",
        "[report.json](report.json) records per-axis scores, exact completion denominators, outcomes, repair-round counts, "
        "generation statistics, source summaries, and artifact hashes. [per_problem.csv](per_problem.csv) separates "
        "initial, repaired, and fallback-selected results for each proposal. [source_results.csv](source_results.csv) "
        "and [pairwise.csv](pairwise.csv) expose source-level and paired effects. "
        "No pooled best-of-models or best-of-arms submission is constructed.", "",
        "Complete original-cohort conditions receive their own `conditions/<model>__<arm>/selected_candidates.jsonl` "
        "and manifest with source request keys, repair-result hashes, selected metrics, and submission hash. "
        "Partial or subset cohorts do not produce full submissions.", ""]
    if report.get("condition_exports"):
        lines += ["Available condition submissions: " + "; ".join(
            f"[{item['model'].split('/')[-1]} / {item['arm']}]({item['submission']})"
            for item in report["condition_exports"]) + ".", ""]
    lines += [
        "## Limits", "", *["- " + item for item in report["limitations"]], "",
        "Rebuild from saved artifacts without model calls or Lean execution:", "", "```bash",
        "python src/report_repair_matrix.py --input results/one_shot/03_repaired_context_ablation", "```", "",
        "Use `--base PATH` if the initial experiment was relocated, or `--output PATH` for a separate report snapshot.", ""]
    return "\n".join(lines)


def run(root, base=None, output=None):
    root = Path(root).resolve()
    output = Path(output).resolve() if output is not None else root
    report, problems, pairwise = build_report(root, base)
    output.mkdir(parents=True, exist_ok=True)
    report["condition_exports"] = export_complete_conditions(root, output, report, problems)
    write_json(output / "report.json", report)
    write_csv(output / "per_problem.csv", problems, list(problems[0]))
    write_csv(output / "pairwise.csv", pairwise,
              ["model", "contrast", "name", "source", "corrected_selected_delta_pp", "accepted_indicator_delta"])
    source_rows = [{"model": s["model"], "arm": s["arm"], "source": s["source"],
                    "expected": s["expected_problems"], "initial_recorded": s["initial_recorded"],
                    "repair_recorded": s["repair_recorded"], "baseline_score": s["baseline_mean"]["combined_pct"],
                    "initial_raw_score": s["initial_raw_mean"]["combined_pct"],
                    "repaired_raw_score": s["repaired_raw_mean"]["combined_pct"],
                    "selected_score": s["selected_mean"]["combined_pct"], "selected_gain_pp": s["selected_gain_pp"],
                    "initial_valid": s["initial_all_versions_valid"], "final_valid": s["final_all_versions_valid"],
                    "returned_incumbent": s["returned_incumbent"], "accepted": s["accepted_improvements"]} for s in report["sources"]]
    write_csv(output / "source_results.csv", source_rows, list(source_rows[0]))
    (output / "README.md").write_text(markdown(report), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Repair matrix directory")
    parser.add_argument("--base", type=Path, help="Override saved original experiment directory after relocation")
    parser.add_argument("--output", type=Path, help="Separate report destination; defaults to the repair matrix")
    args = parser.parse_args(argv)
    report = run(args.input, args.base, args.output)
    print(json.dumps({key: report[key] for key in ("status", "planned_cells", "initial_recorded_cells", "repair_recorded_cells")}))


if __name__ == "__main__":
    main()
