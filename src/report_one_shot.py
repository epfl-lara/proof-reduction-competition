"""Summarize a frozen one-shot matrix without model calls or Lean execution.

Full-cohort means remain null until their denominator is complete. Paired effects
use the same proofs and are descriptive, not significance estimates. Generation
failures remain unknown raw scores; incumbent fallback is reported separately.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from statistics import mean


FIELDS = ("length_reduction_pct", "heartbeat_reduction_pct", "compatibility_pct", "combined_pct")
CONTRASTS = {
    "cards_minus_plain": {"cards": 1, "plain": -1},
    "goals_minus_plain": {"goals": 1, "plain": -1},
    "cards_goals_minus_plain": {"cards_goals": 1, "plain": -1},
    "cards_goals_costs_minus_plain": {"cards_goals_costs": 1, "plain": -1},
    "cards_main_effect": {"cards": .5, "plain": -.5, "cards_goals": .5, "goals": -.5},
    "goals_main_effect": {"goals": .5, "plain": -.5, "cards_goals": .5, "cards": -.5},
    "cards_goals_interaction": {"cards_goals": 1, "cards": -1, "goals": -1, "plain": 1},
    "costs_minus_cards_goals": {"cards_goals_costs": 1, "cards_goals": -1},
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_csv(path, rows, fields):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def scores(evaluation):
    return evaluation.get("scores", {})


def complete_scores(evaluation):
    return all(finite_number(scores(evaluation).get(field)) for field in FIELDS)


def average_scores(evaluations):
    if not evaluations or not all(complete_scores(e) for e in evaluations):
        return dict.fromkeys(FIELDS, None)
    return {field: mean(scores(e)[field] for e in evaluations) for field in FIELDS}


def generation_usage(record):
    usage = record.get("generation", {}).get("usage")
    return usage if isinstance(usage, dict) else {}


def sum_usage(records, key):
    return sum(generation_usage(r).get(key, 0) for r in records
               if finite_number(generation_usage(r).get(key, 0)))


def error_category(record):
    """Return labels only, never raw responses, reasoning, or provider errors."""
    generation = record.get("generation", {})
    status = generation.get("status", "unknown")
    if status != "received":
        return status
    if generation.get("finish_reason") == "length":
        return "generation_truncated"
    evaluation = record.get("evaluation", {})
    if evaluation.get("status") == "passed":
        return "passed"
    diagnostics = evaluation.get("diagnostics", [])
    parser_reasons = {
        "empty_final_content", "ambiguous_code_fences_or_surrounding_text",
        "query_tactic_in_final_output", "generation_truncated",
    }
    for diagnostic in diagnostics:
        if isinstance(diagnostic, str) and diagnostic in parser_reasons:
            return diagnostic
    return "evaluation_" + evaluation.get("status", "unknown")


def summarize_condition(records, names, inputs):
    expected = len(names)
    finished = len(records) == expected
    baseline = average_scores([inputs[n]["incumbent"] for n in names])
    raw = [r.get("evaluation", {}) for r in records]
    selected = [r["selected_evaluation"] for r in records]
    known_raw = [e for e in raw if complete_scores(e)]
    full_raw = average_scores(raw) if finished else dict.fromkeys(FIELDS, None)
    full_selected = average_scores(selected) if finished else dict.fromkeys(FIELDS, None)
    source_names = sorted({inputs[n]["row"]["source"] for n in names})
    sources = []
    for source in source_names:
        cohort = [n for n in names if inputs[n]["row"]["source"] == source]
        subset = [r for r in records if r["name"] in cohort]
        ready = len(subset) == len(cohort)
        base = average_scores([inputs[n]["incumbent"] for n in cohort])
        selected_mean = average_scores([r["selected_evaluation"] for r in subset]) if ready else dict.fromkeys(FIELDS, None)
        sources.append({"source": source, "expected_problems": len(cohort), "recorded_problems": len(subset),
                        "raw_mean": average_scores([r.get("evaluation", {}) for r in subset]) if ready else dict.fromkeys(FIELDS, None),
                        "selected_mean": selected_mean, "baseline_mean": base,
                        "selected_gain_pp": selected_mean["combined_pct"] - base["combined_pct"] if ready else None,
                        "improved_problems": sum(bool(r.get("accepted")) for r in subset)})
    return {
        "expected_problems": expected, "recorded_problems": len(records), "complete": finished,
        "scored_outputs": len(known_raw), "raw_mean": full_raw, "selected_mean": full_selected,
        "observed_raw_mean": average_scores(known_raw), "observed_selected_mean": average_scores(selected),
        "selected_gain_pp": full_selected["combined_pct"] - baseline["combined_pct"] if finished else None,
        "primary_passed_outputs": sum(r.get("evaluation", {}).get("per_version", {}).get(
            r.get("evaluation", {}).get("primary_version"), {}).get("passed") is True for r in records),
        "all_versions_passed_outputs": sum(bool(r.get("all_versions_passed")) for r in records),
        "improved_problems": sum(bool(r.get("accepted")) for r in records),
        "transport_error_outputs": sum(r.get("generation", {}).get("status") == "transport_error" for r in records),
        "indeterminate_outputs": sum(r.get("generation", {}).get("status") == "indeterminate" for r in records),
        "truncated_outputs": sum(r.get("generation", {}).get("finish_reason") == "length" for r in records),
        "unavailable_outputs": len(records) - len(known_raw),
        "error_categories": dict(sorted(Counter(error_category(r) for r in records).items())),
        "prompt_tokens": sum_usage(records, "prompt_tokens"),
        "completion_tokens": sum_usage(records, "completion_tokens"),
        "usage_missing_outputs": sum(not all(finite_number(generation_usage(r).get(k)) for k in (
            "prompt_tokens", "completion_tokens")) for r in records),
        "request_elapsed_seconds_sum": sum(r.get("generation", {}).get("elapsed_seconds", 0) for r in records
            if finite_number(r.get("generation", {}).get("elapsed_seconds", 0))),
        "source_results": sources,
    }


def load_matrix(root):
    config = read_json(root / "config.json")
    names, models, arms = config["names"], config["models"], config["arms"]
    for label, values in (("names", names), ("models", models), ("arms", arms)):
        if not values or len(set(values)) != len(values):
            raise ValueError(f"Configuration must have unique nonempty {label}")
    inputs = {}
    for path in sorted((root / "inputs").glob("*.json")):
        pack = read_json(path)
        if pack["name"] not in names or pack["name"] in inputs:
            raise ValueError(f"Unexpected or duplicate input: {path}")
        if not complete_scores(pack["incumbent"]):
            raise ValueError(f"Unscored incumbent: {pack['name']}")
        inputs[pack["name"]] = pack
    if set(inputs) != set(names):
        raise ValueError("All configured incumbent inputs are required before reporting")
    expected_keys = {(model, arm, name) for model in models for arm in arms for name in names}
    records = {}
    cell_hashes = {}
    for path in sorted((root / "cells").glob("*/result.json")):
        record = read_json(path)
        key = record["model"], record["arm"], record["name"]
        if key not in expected_keys or key in records:
            raise ValueError(f"Unexpected or duplicate cell: {path}")
        if path.parent.name != record.get("request_sha256"):
            raise ValueError(f"Result directory does not match request hash: {path}")
        if not complete_scores(record.get("selected_evaluation", {})):
            raise ValueError(f"Unscored selected proof: {path}")
        pack = inputs[record["name"]]
        if record.get("source") != pack["row"]["source"]:
            raise ValueError(f"Source identity mismatch: {path}")
        if not record.get("accepted") and (record["selected_proof"] != pack["proof"]
                or scores(record["selected_evaluation"]) != scores(pack["incumbent"])):
            raise ValueError(f"Fallback differs from common incumbent: {path}")
        if record.get("accepted") and (record["selected_proof"] != record.get("extracted_proof")
                or record["selected_evaluation"] != record.get("evaluation")):
            raise ValueError(f"Accepted selection differs from evaluated candidate: {path}")
        records[key] = record
        cell_hashes[str(path.relative_to(root))] = digest(path)
    baseline = average_scores([inputs[n]["incumbent"] for n in names])
    summary_path = root / "summary.json"
    summary = read_json(summary_path) if summary_path.exists() else None
    if summary:
        for field in FIELDS:
            if not math.isclose(baseline[field], summary["baseline_mean"][field], rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError("Runner summary baseline differs from saved inputs")
    return config, inputs, records, baseline, summary, cell_hashes


def paired_results(config, records, inputs):
    summaries, rows = [], []
    names = config["names"]
    for model in config["models"]:
        for label, weights in CONTRASTS.items():
            if set(weights) - set(config["arms"]):
                continue
            paired_names = [name for name in names if all((model, arm, name) in records for arm in weights)]
            values, raw_values, token_values = [], [], []
            for name in paired_names:
                value = sum(weight * records[model, arm, name]["selected_evaluation"]["scores"]["combined_pct"]
                            for arm, weight in weights.items())
                raw_known = all(complete_scores(records[model, arm, name].get("evaluation", {})) for arm in weights)
                raw_value = sum(weight * records[model, arm, name]["evaluation"]["scores"]["combined_pct"]
                                for arm, weight in weights.items()) if raw_known else None
                usage_known = all(finite_number(generation_usage(records[model, arm, name]).get("prompt_tokens"))
                                  for arm in weights)
                token_value = sum(weight * generation_usage(records[model, arm, name])["prompt_tokens"]
                                  for arm, weight in weights.items()) if usage_known else None
                values.append(value)
                if raw_known:
                    raw_values.append(raw_value)
                if usage_known:
                    token_values.append(token_value)
                rows.append({"model": model, "contrast": label, "name": name,
                             "source": inputs[name]["row"]["source"], "selected_delta_pp": value,
                             "raw_delta_pp": raw_value, "prompt_token_delta": token_value})
            finished = len(paired_names) == len(names)
            summaries.append({"model": model, "contrast": label, "weights": weights,
                              "expected_pairs": len(names), "recorded_pairs": len(paired_names),
                              "selected_mean_delta_pp": mean(values) if finished else None,
                              "raw_mean_delta_pp": mean(raw_values) if finished and len(raw_values) == len(names) else None,
                              "prompt_token_mean_delta": mean(token_values) if finished and len(token_values) == len(names) else None,
                              "observed_selected_mean_delta_pp": mean(values) if values else None,
                              "positive_pairs": sum(v > 1e-10 for v in values),
                              "negative_pairs": sum(v < -1e-10 for v in values),
                              "tied_pairs": sum(abs(v) <= 1e-10 for v in values)})
    return summaries, rows


def build_report(root):
    config, inputs, records, baseline, summary, cell_hashes = load_matrix(root)
    conditions, problem_rows, source_rows = [], [], []
    for model in config["models"]:
        for arm in config["arms"]:
            subset = [records[model, arm, name] for name in config["names"] if (model, arm, name) in records]
            condition = {"model": model, "arm": arm, **summarize_condition(subset, config["names"], inputs)}
            conditions.append(condition)
            for source in condition["source_results"]:
                source_rows.append({"model": model, "arm": arm, "source": source["source"],
                    "recorded": source["recorded_problems"], "expected": source["expected_problems"],
                    "baseline_score": source["baseline_mean"]["combined_pct"],
                    "raw_score": source["raw_mean"]["combined_pct"],
                    "selected_score": source["selected_mean"]["combined_pct"],
                    "selected_gain_pp": source["selected_gain_pp"], "improved": source["improved_problems"]})
            for name in config["names"]:
                record = records.get((model, arm, name))
                row = {"model": model, "arm": arm, "name": name, "source": inputs[name]["row"]["source"],
                       "recorded": record is not None, "baseline_score": scores(inputs[name]["incumbent"])["combined_pct"]}
                if record:
                    row.update({"raw_score": scores(record.get("evaluation", {})).get("combined_pct"),
                                "selected_score": scores(record["selected_evaluation"])["combined_pct"],
                                "selected_gain_pp": scores(record["selected_evaluation"])["combined_pct"] - row["baseline_score"],
                                "accepted": record.get("accepted", False), "all_versions_passed": record.get("all_versions_passed", False),
                                "outcome": error_category(record), "request_sha256": record["request_sha256"]})
                problem_rows.append(row)
    contrasts, pairwise = paired_results(config, records, inputs)
    expected = len(config["names"]) * len(config["models"]) * len(config["arms"])
    contexts = [inputs[n].get("context", {}) for n in config["names"]]
    sites = [site for context in contexts for site in context.get("sites", [])]
    context_summary = {
        "prepared_proofs": sum(context.get("status") == "ok" for context in contexts),
        "selected_sites": len(sites),
        "observed_goal_sites": sum(site.get("status") == "observed" for site in sites),
        "measured_original_tactic_sites": sum(site.get("cost_status") == "measured_original_tactic" for site in sites),
        "goal_text_truncated_sites": sum(bool(site.get("goals_truncated")) for site in sites),
        "cost_status_counts": dict(sorted(Counter(site.get("cost_status", "unknown") for site in sites).items())),
        "saved_contexts_marked_cached": sum(bool(context.get("cached")) for context in contexts),
        "saved_extraction_seconds_sum": sum(context.get("elapsed_seconds", 0) for context in contexts
            if finite_number(context.get("elapsed_seconds", 0))),
        "implementation_sha256": sorted({context["implementation_sha256"] for context in contexts
                                          if "implementation_sha256" in context}),
        "cost_semantics": sorted({context["cost_semantics"] for context in contexts if "cost_semantics" in context}),
    }
    report = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if len(records) == expected else "incomplete",
        "planned_cells": expected, "recorded_cells": len(records), "problem_count": len(config["names"]),
        "baseline_mean": baseline, "config_sha256": digest(root / "config.json"),
        "input_sha256": {str(p.relative_to(root)): digest(p) for p in sorted((root / "inputs").glob("*.json"))},
        "result_sha256": cell_hashes, "summary_sha256": digest(root / "summary.json") if summary else None,
        "runner_summary_recorded_cells": summary.get("recorded_cells") if summary else None,
        "generation_settings": {k: config[k] for k in ("temperature", "reasoning_effort", "max_tokens", "min_gain_pp")},
        "context_preparation": context_summary, "conditions": conditions, "paired_contrasts": contrasts,
        "error_categories": dict(sorted(Counter(error_category(record) for record in records.values()).items())),
        "largest_observed_individual_gains": sorted(
            [row for row in problem_rows if row.get("accepted")],
            key=lambda row: (-row["selected_gain_pp"], row["model"], row["arm"], row["name"]))[:5],
        "limitations": [
            "One stochastic draw per cell on a small development cohort; effects are descriptive and not statistically established.",
            "Fallback-selected scores include the shared incumbent when a request fails or its candidate is not accepted.",
            "Transport and indeterminate outcomes have unknown raw scores, not zeros; full raw means remain null if any are unavailable.",
            "Observed partial-cohort means are not full-cohort results and may change as slower cells finish.",
            "Request duration sums overlap under concurrency and are not end-to-end wall time; missing token usage is uncounted.",
            "Goal costs describe incumbent-state replay and do not predict replacement cost.",
            "This report reads saved evaluations; it does not recompile candidates or remeasure references.",
        ],
    }
    return report, config, inputs, records, pairwise, problem_rows, source_rows


def pooled_portfolio(config, inputs, records):
    expected = len(config["names"]) * len(config["models"]) * len(config["arms"])
    if len(records) != expected:
        raise ValueError(f"Portfolio requires the complete configured matrix ({len(records)}/{expected})")
    candidates, selections, evaluations = [], [], []
    for name in config["names"]:
        proof, evaluation = inputs[name]["proof"], inputs[name]["incumbent"]
        winner = None
        for model in config["models"]:
            for arm in config["arms"]:
                record = records[model, arm, name]
                if scores(record["selected_evaluation"])["combined_pct"] > scores(evaluation)["combined_pct"] + 1e-10:
                    proof, evaluation = record["selected_proof"], record["selected_evaluation"]
                    winner = {"model": model, "arm": arm, "request_sha256": record["request_sha256"]}
        candidates.append({"name": name, "proof": proof})
        evaluations.append(evaluation)
        selections.append({"name": name, "source": inputs[name]["row"]["source"], "winner": winner,
                           "scores": scores(evaluation), "gain_pp": scores(evaluation)["combined_pct"]
                           - scores(inputs[name]["incumbent"])["combined_pct"]})
    baseline = average_scores([inputs[n]["incumbent"] for n in config["names"]])
    final = average_scores(evaluations)
    return candidates, {"label": "Post-hoc pooled portfolio; not a one-shot condition",
                        "total_requests_in_matrix": expected,
                        "candidate_cells_per_problem": len(config["models"]) * len(config["arms"]),
                        "baseline_mean": baseline, "selected_mean": final,
                        "selected_gain_pp": final["combined_pct"] - baseline["combined_pct"],
                        "improved_problems": sum(s["winner"] is not None for s in selections), "selections": selections}


def fmt(value, signed=False):
    return "—" if value is None else format(value, "+.3f" if signed else ".3f")


def markdown_report(report, config):
    baseline = report["baseline_mean"]["combined_pct"]
    lines = ["# One-shot strategy and context ablation", "",
        f"Snapshot: **{report['status']}**, {report['recorded_cells']}/{report['planned_cells']} cells recorded. "
        f"Common deterministic incumbent: **{baseline:.6f}%** local combined score across {report['problem_count']} proofs.", "",
        f"Each model/arm/proof receives one independent request at temperature {config['temperature']}, "
        f"{config['reasoning_effort']} reasoning, and a {config['max_tokens']:,}-token output limit. "
        "There are no repair calls, automatic transport retries, or cross-arm feedback. "
        f"A candidate replaces its incumbent only under the frozen {config['min_gain_pp']}-percentage-point gain policy.", "",
        "`plain` has the common proof, objective, and environment context. `cards` adds selected strategy cards; "
        "`goals` adds actual goal annotations; `cards_goals` combines these. `cards_goals_costs` adds measured "
        "costs to the same selected goal sites. No random seed is fixed or repeated draws averaged.", "",
        "Full-cohort scores are blank until the condition completes. A raw score is also blank if any output "
        "could not be scored. Invalid or failed proofs keep their recorded zero score. Selected scores use "
        "the incumbent after an unavailable, invalid, or non-improving output. Counts and costs cover recorded cells.", "",
        "## Scores and passing outputs", "",
        "| Model | Arm | Recorded | Raw score | Selected score | Gain pp | Primary pass | All versions pass | Improved |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for c in report["conditions"]:
        lines.append(f"| {c['model'].split('/')[-1]} | {c['arm']} | {c['recorded_problems']}/{c['expected_problems']} "
            f"| {fmt(c['raw_mean']['combined_pct'])} | {fmt(c['selected_mean']['combined_pct'])} "
            f"| {fmt(c['selected_gain_pp'], True)} | {c['primary_passed_outputs']} "
            f"| {c['all_versions_passed_outputs']} | {c['improved_problems']} |")
    lines += ["", "The report JSON includes length, heartbeat, and compatibility axes for raw and selected outputs. "
        "Passing counts describe the generated candidate, not the fallback.", "", "## Generation cost and failures", "",
        "| Model | Arm | Transport errors | Indeterminate | Truncated | Prompt tokens | Completion tokens | Missing usage | Request seconds sum |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for c in report["conditions"]:
        lines.append(f"| {c['model'].split('/')[-1]} | {c['arm']} | {c['transport_error_outputs']} | {c['indeterminate_outputs']} "
            f"| {c['truncated_outputs']} | {c['prompt_tokens']:,} | {c['completion_tokens']:,} "
            f"| {c['usage_missing_outputs']} | {c['request_elapsed_seconds_sum']:.1f} |")
    lines += ["", "Token counts are provider-reported. Missing usage is not estimated. Concurrent request durations "
        "overlap, so their sum is not elapsed experiment time. No monetary price is inferred.", "",
        "Recorded outcome categories: " + (", ".join(f"`{key}`: {value}" for key, value in report["error_categories"].items())
                                            or "none yet") + ".", "",
        "## Context preparation", ""]
    context = report["context_preparation"]
    lines += [f"Prepared context for {context['prepared_proofs']} proofs: {context['selected_sites']} selected sites, "
        f"{context['observed_goal_sites']} observed goal sites, and {context['measured_original_tactic_sites']} "
        f"sites with incumbent-tactic cost measurements. Goal text is truncated at {context['goal_text_truncated_sites']} sites. "
        "Unavailable costs are left unmeasured; they are not zeros.", "",
        f"The saved extraction-duration fields sum to {context['saved_extraction_seconds_sum']:.3f} seconds; "
        f"{context['saved_contexts_marked_cached']} saved contexts are marked cached. These recorded timings "
        "are not a measurement of fresh preparation time in this generation run. Input hashes and extractor "
        "implementation hashes are retained in the report. Costs describe instrumented execution of the "
        "original tactic at its state, not a portable tactic price or the replacement's score.", "",
        "## Paired context comparisons", "",
        "Each contrast uses the same proof under the same model, with incumbent fallback after each single attempt. "
        "Positive values favor the named addition. Full means require every configured pair. "
        "This is one stochastic draw on a development cohort; these are descriptive differences, not causal or significant effects.", "",
        "| Model | Cards − plain | Goals − plain | Cards+goals − plain | Cards+goals+costs − plain | Costs − cards+goals |",
        "| --- | ---: | ---: | ---: | ---: | ---: |"]
    contrast_map = {(c["model"], c["contrast"]): c for c in report["paired_contrasts"]}
    labels = ("cards_minus_plain", "goals_minus_plain", "cards_goals_minus_plain", "cards_goals_costs_minus_plain", "costs_minus_cards_goals")
    for model in config["models"]:
        values = [fmt(contrast_map.get((model, label), {}).get("selected_mean_delta_pp"), True) for label in labels]
        lines.append("| " + model.split("/")[-1] + " | " + " | ".join(values) + " |")
    lines += ["", "The 2×2 card main effect averages `(cards − plain)` and `(cards_goals − goals)`. "
        "The goal main effect averages `(goals − plain)` and `(cards_goals − cards)`. "
        "The interaction is `cards_goals − cards − goals + plain`. Cost context is isolated only by "
        "`cards_goals_costs − cards_goals`.", "",
        "| Model | Card main effect pp | Goal main effect pp | Interaction pp |",
        "| --- | ---: | ---: | ---: |"]
    for model in config["models"]:
        values = [fmt(contrast_map.get((model, label), {}).get("selected_mean_delta_pp"), True)
                  for label in ("cards_main_effect", "goals_main_effect", "cards_goals_interaction")]
        lines.append("| " + model.split("/")[-1] + " | " + " | ".join(values) + " |")
    lines += ["", "## Per-problem evidence", "",
        "Use [per_problem.csv](per_problem.csv) for candidate outcomes, gains, source, and request hashes, "
        "[source_results.csv](source_results.csv) for source-level means, and [pairwise.csv](pairwise.csv) "
        "for the individual paired comparisons. [report.json](report.json) records full axis metrics, "
        "error-category counts, provenance hashes, partial observations, and all contrast denominators.", ""]
    improved = [c for c in report["conditions"] if c["complete"]]
    if improved:
        best = max(improved, key=lambda c: c["selected_mean"]["combined_pct"])
        lines += [f"Among the {len(improved)} completed conditions in this snapshot, the highest selected score is "
            f"**{best['model']} / {best['arm']}**, {best['selected_mean']['combined_pct']:.3f}% "
            f"({best['selected_gain_pp']:+.3f} pp over the incumbent). This identifies an observed result, "
            "not a statistically established best configuration.", ""]
    if report["largest_observed_individual_gains"]:
        lines += ["Largest individual accepted changes observed so far (each is a separate single-call cell):", "",
            "| Proof | Model | Arm | Gain pp |", "| --- | --- | --- | ---: |"]
        for row in report["largest_observed_individual_gains"]:
            lines.append(f"| `{row['name']}` | {row['model'].split('/')[-1]} | {row['arm']} | {row['selected_gain_pp']:+.3f} |")
        lines.append("")
    if "portfolio" in report:
        p = report["portfolio"]
        lines += ["## Separate post-hoc pooled portfolio", "",
            f"Selecting the best saved candidate across all {p['total_requests_in_matrix']} requests "
            f"({p['candidate_cells_per_problem']} cells per proof, with incumbent fallback) gives "
            f"**{p['selected_mean']['combined_pct']:.3f}%**, a {p['selected_gain_pp']:+.3f} pp gain. "
            "This pools models and contexts and is **not a one-shot condition**. "
            "[Selected proofs](portfolio/selected_candidates.jsonl) and [selection provenance](portfolio/manifest.json) "
            "are supplied separately; this read-only report does not perform a new Lean audit.", ""]
    lines += ["## Interpretation limits", "", *["- " + text for text in report["limitations"]], "",
        "Rebuild this snapshot without model calls or reference measurements:", "", "```bash",
        "python src/report_one_shot.py --input results/one_shot/01_context_ablation", "```", "",
        "Add `--portfolio` only after all configured cells finish to export the separate pooled selection.", ""]
    return "\n".join(lines)


def run(root, output=None, portfolio=False):
    root = Path(root).resolve()
    output = Path(output).resolve() if output else root
    report, config, inputs, records, pairwise, problems, sources = build_report(root)
    if portfolio:
        candidates, selection = pooled_portfolio(config, inputs, records)
        folder = output / "portfolio"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "selected_candidates.jsonl"
        temporary = target.with_suffix(".jsonl.tmp")
        temporary.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in candidates), encoding="utf-8")
        temporary.replace(target)
        selection["candidates_sha256"] = digest(target)
        write_json(folder / "manifest.json", selection)
        report["portfolio"] = selection
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "report.json", report)
    write_csv(output / "pairwise.csv", pairwise,
              ["model", "contrast", "name", "source", "selected_delta_pp", "raw_delta_pp", "prompt_token_delta"])
    write_csv(output / "per_problem.csv", problems,
              ["model", "arm", "name", "source", "recorded", "baseline_score", "raw_score", "selected_score",
               "selected_gain_pp", "accepted", "all_versions_passed", "outcome", "request_sha256"])
    write_csv(output / "source_results.csv", sources,
              ["model", "arm", "source", "recorded", "expected", "baseline_score", "raw_score", "selected_score", "selected_gain_pp", "improved"])
    (output / "README.md").write_text(markdown_report(report, config), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Frozen one-shot run directory")
    parser.add_argument("--output", type=Path, help="Report destination, defaults to the input directory")
    parser.add_argument("--portfolio", action="store_true", help="Export a separately labeled pooled selection; requires all cells")
    args = parser.parse_args(argv)
    report = run(args.input, args.output, args.portfolio)
    print(json.dumps({k: report[k] for k in ("status", "recorded_cells", "planned_cells", "baseline_mean")}))


if __name__ == "__main__":
    main()
