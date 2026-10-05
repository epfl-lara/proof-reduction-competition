"""Full-cohort metrics, running-cell summaries, costs, and submission export."""

import json
import threading

from proof_eval.evidence.io import now, read, write_json
from proof_eval.protocol import FIELDS, code_identity
from proof_eval.providers.costs import CostConfig, generations_cost, summarize_costs

from .configuration import CONDITIONS, historical, score_control, structural_control

_REPORT_LOCK = threading.Lock()


def report(output, config):
    with _REPORT_LOCK:
        return _report(output, config)


def control_mean(loader, names, model, effort):
    controls = [loader(name, model, effort)[1] for name in names]
    return (
        sum(c["selected_evaluation"]["scores"]["combined_pct"] for c in controls)
        / len(names)
        if controls and all(c is not None for c in controls)
        else None
    )


def display(value, suffix="%", *, signed=False):
    return (
        "—"
        if value is None
        else (f"{value:+.6f}" if signed else f"{value:.6f}") + suffix
    )


def _report(output, config):
    records = [read(p) for p in (output / "cells").glob("*/result.json")]
    n = len(config["names"])
    result = {
        "at": now(),
        "mode": config["mode"],
        "planned_cells": len(config["conditions"]) * n,
        "terminal_cells": len(records),
        "conditions": [],
        "active": [],
    }
    for model, effort in config["conditions"]:
        group = [r for r in records if (r["model"], r["effort"]) == (model, effort)]
        complete = len(group) == n and all(r["status"] == "complete" for r in group)
        summary = {
            "model": model,
            "effort": effort,
            "terminal": len(group),
            "expected": n,
            "complete": complete,
            "incomplete_outcomes": sum(r["status"] != "complete" for r in group),
            "mean_scores": {
                f: (
                    sum(r["selected_evaluation"]["scores"][f] for r in group) / n
                    if complete
                    else None
                )
                for f in FIELDS
            },
            "historical_mean_score": control_mean(
                historical, config["names"], model, effort
            ),
            "structural_control_mean_score": (
                sum(
                    structural_control(name, model, effort)[1]["selected_evaluation"][
                        "scores"
                    ]["combined_pct"]
                    for name in config["names"]
                )
                / n
                if config["mode"] != "correctness"
                and (model, effort) in CONDITIONS["correctness"]
                else None
            ),
            "model_calls": sum(len(r["generations"]) for r in group),
            "completion_tokens": sum(
                (g.get("usage") or {}).get("completion_tokens") or 0
                for r in group
                for g in r["generations"]
            ),
            "unknown_usage_calls": sum(
                (g.get("usage") or {}).get("completion_tokens") is None
                for r in group
                for g in r["generations"]
            ),
            "agent_tool_checks": sum(r["agent_tool_checks"] for r in group),
            "improvements": sum(r["improvements"] for r in group),
        }
        if config.get("deterministic_cleanup"):
            proposal_count = sum(r["valid_changed_proposals"] for r in group)
            summary.update(
                score_control_mean_score=control_mean(
                    score_control, config["names"], model, effort
                ),
                mean_final_cleanup_gain_pp=(
                    sum(r["final_cleanup_gain_pp"] for r in group) / n
                    if complete
                    else None
                ),
                deterministic_tool_calls=sum(
                    r["deterministic_tool_calls"] for r in group
                ),
                deterministic_tool_coverage_pct=(
                    100
                    * sum(r["proposals_with_tool_cleanup"] for r in group)
                    / proposal_count
                    if proposal_count
                    else None
                ),
                incomplete_cleanups=sum(r["incomplete_cleanups"] for r in group),
            )
        summary["cost"] = summarize_costs(
            [
                {
                    "name": r["name"],
                    "cost": r.get("cost")
                    or generations_cost(CostConfig(model, effort), r["generations"]),
                }
                for r in group
            ]
        )
        result["conditions"].append(summary)
        if complete:
            destination = (
                output / "conditions" / (model.replace("/", "__") + "__" + effort)
            )
            destination.mkdir(parents=True, exist_ok=True)
            ordered = sorted(group, key=lambda r: config["names"].index(r["name"]))
            (destination / "selected_candidates.jsonl").write_text(
                "".join(
                    json.dumps(
                        {"name": r["name"], "proof": r["selected_proof"]},
                        ensure_ascii=False,
                    )
                    + "\n"
                    for r in ordered
                )
            )
    for path in sorted((output / "cells").glob("*/evidence/state.json")):
        if not (path.parent.parent / "result.json").exists():
            state = read(path)
            inp = path.parent.parent / "input.json"
            result["active"].append(
                {
                    **{
                        k: state[k]
                        for k in (
                            "name",
                            "checks",
                            "valid_checks",
                            "improvements",
                            "updated_at",
                        )
                    },
                    "model": read(inp)["model"] if inp.exists() else None,
                    "effort": read(inp)["effort"] if inp.exists() else None,
                    "best_score": state["best_evaluation"]["scores"]["combined_pct"],
                }
            )
    result["status"] = (
        "complete" if all(c["complete"] for c in result["conditions"]) else "partial"
    )
    write_json(output / "report.json", result)
    lines = [
        "# "
        + (
            "Structural context and correctness tools"
            if config["mode"] == "correctness"
            else "Score-feedback optimization"
        ),
        "",
        f"Updated {result['at']}. **{result['status']}**: {len(records)}/{result['planned_cells']} terminal cells.",
        "",
        "See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.",
        "",
        "| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for c in result["conditions"]:
        s = c["mean_scores"]["combined_pct"]
        structural = c["structural_control_mean_score"]
        lines.append(
            f"| {c['model']} | {c['effort']} | {c['terminal']}/{n} | {f'{s:.6f}%' if s is not None else 'pending'} | {display(c['historical_mean_score'])} | {f'{structural:.6f}%' if structural is not None else '—'} |"
        )
    if config.get("deterministic_cleanup"):
        lines += [
            "",
            f"Deterministic placement: `{config['mode']}`. Fixed reference denominators and saved original/D0 seeds.",
            "",
            "| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for c in result["conditions"]:
            gain = c["mean_final_cleanup_gain_pp"]
            coverage = c["deterministic_tool_coverage_pct"]
            lines.append(
                f"| {c['model']} / {c['effort']} | {display(c['score_control_mean_score'])} | {f'{gain:+.6f} pp' if gain is not None else 'pending'} | {c['deterministic_tool_calls']} | {f'{coverage:.2f}%' if coverage is not None else '—'} |"
            )
    lines += [
        "",
        "## Estimated API-equivalent cost",
        "",
        "Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.",
        "",
        "| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for c in result["conditions"]:
        cost = c["cost"]
        lines.append(
            f"| {c['model']} / {c['effort']} | {cost['known_cost_problems']}/{c['terminal']} | {display(cost['mean_observed_usd'], ' USD')} | {display(cost['max_observed_usd'], ' USD')} | {len(cost['over_budget_problems'])} |"
        )
    lines += [
        "",
        "## Completed cells",
        "",
        "| Theorem | Model / effort | Score | Change from historical | Tool checks |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for r in sorted(
        records,
        key=lambda r: (config["names"].index(r["name"]), r["model"], r["effort"]),
    ):
        lines.append(
            f"| {r['name']} | {r['model']} / {r['effort']} | {r['selected_evaluation']['scores']['combined_pct']:.6f}% | {display(r['gain_over_historical_pp'], ' pp', signed=True)} | {r['agent_tool_checks']} |"
        )
    lines += [
        "",
        "## Running cells",
        "",
        "| Theorem | Model / effort | Checks | Best score so far |",
        "| --- | --- | ---: | ---: |",
    ]
    for r in result["active"]:
        lines.append(
            f"| {r['name']} | {r['model']} / {r['effort']} | {r['checks']} | {r['best_score']:.6f}% |"
        )
    (output / "README.md").write_text("\n".join(lines) + "\n")
    return result


def trajectory(row, seed_code, seed_evaluation, checks):
    """Attribute accepted score increments; seed checks and final cleanup are distinct."""
    seed_identity = code_identity(row, seed_code)
    best = seed_evaluation["scores"]["combined_pct"]
    first_best = first_raw = None
    gains = {
        "model_gain_pp": 0.0,
        "in_loop_cleanup_gain_pp": 0.0,
        "final_cleanup_gain_pp": 0.0,
    }
    records = []
    for c in checks:
        numeric = c["evaluation"]["scores"]["combined_pct"]
        if c["accepted"]:
            kind = {
                "deterministic_agent_tool": "in_loop_cleanup_gain_pp",
                "deterministic_final_harness": "final_cleanup_gain_pp",
            }.get(c["origin"], "model_gain_pp")
            gains[kind] += numeric - best
            best = numeric
        changed = c["code_sha256"] != seed_identity
        if (
            c["all_versions_passed"]
            and changed
            and first_best is None
            and c["origin"] in ("agent_tool", "deterministic_input", "final_harness")
        ):
            first_best, first_raw = best, numeric
        records.append(
            {
                "number": c["number"],
                "origin": c["origin"],
                "valid": c["all_versions_passed"],
                "duplicate": c["duplicate"],
                "changed": changed,
                "accepted": c["accepted"],
                "candidate_score": numeric,
                "best_score": best,
            }
        )
    return records, {
        "first_changed_valid_raw_score": first_raw,
        "best_after_first_changed_valid": first_best,
        "further_search_gain_pp": (
            None
            if first_best is None
            else best - gains["final_cleanup_gain_pp"] - first_best
        ),
        **gains,
    }
