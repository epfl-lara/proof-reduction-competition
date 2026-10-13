"""Offline replay orchestration, fixed gate, and provenance-backed reports."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from statistics import mean, median

from proof_eval.evidence.io import digest, now, write_json

from . import discovery_tree, replay
from .discovery_tree import EvidenceReader, ProblemTree, load_run
from .replay import (
    AttemptCap,
    Identity,
    Stagnation,
    eligible,
    restart_yield,
    splice,
    summarize,
)


def validate_identity(trees: list[ProblemTree], comparison: dict | None = None) -> dict:
    """Abort on raw or attempt-level disagreement, including first-attempt scores."""
    compared = {r["name"]: r for r in (comparison or {}).get("rows", [])}
    attempts_checked = 0
    for tree in trees:
        outcome = splice(tree, Identity())
        if not outcome.on_support or abs(outcome.loss_pp) > 1e-9:
            raise ValueError(f"Identity mismatch: {tree.name}")
        first = splice(tree, AttemptCap(1))
        row = compared.get(tree.name)
        if row:
            if (
                abs(row["first_attempt_raw_combined_pct"] - first.raw_combined_pct)
                > 1e-9
            ):
                raise ValueError(f"First-attempt comparison mismatch: {tree.name}")
            if (
                abs(row["all_attempts_raw_combined_pct"] - outcome.raw_combined_pct)
                > 1e-9
            ):
                raise ValueError(f"All-attempt comparison mismatch: {tree.name}")
            if len(row["attempts"]) != len(outcome.attempts):
                raise ValueError(f"Attempt-count comparison mismatch: {tree.name}")
            score = tree.seed_combined_pct
            for actual, saved in zip(outcome.attempts, row["attempts"]):
                score += actual.gain_pp
                if abs(score - saved["best_after_attempt_combined_pct"]) > 1e-9:
                    raise ValueError(
                        f"Attempt comparison mismatch: {tree.name}/{actual.number}"
                    )
                attempts_checked += 1
    if compared and set(compared) != {tree.name for tree in trees}:
        raise ValueError("Comparison and loaded problem cohorts differ")
    return {
        "status": "passed",
        "problems": len(trees),
        "comparison_attempts": attempts_checked,
        "tolerance": 1e-9,
    }


def gate(
    primary: list[ProblemTree], controls: list[list[ProblemTree]], protocol: dict
) -> dict:
    """Select only from the pre-registered grid, then check leave-one-out stability."""

    def select(
        trees: list[ProblemTree], robust: list[list[ProblemTree]], lopo: bool
    ) -> tuple[float | None, list[dict]]:
        rows = []
        for minutes in protocol["grid_minutes"]:
            policy = Stagnation(minutes)
            summary = summarize(
                [splice(t, policy) for t in trees], restart_yield(trees)
            )
            checks = [
                summarize([splice(t, policy) for t in cohort])
                for cohort in robust
                if cohort
            ]
            rows.append(
                {
                    "minutes": minutes,
                    "primary": summary,
                    "robustness": checks,
                    "eligible": eligible(summary, checks, protocol, lopo=lopo),
                }
            )
        feasible = [r for r in rows if r["eligible"]]
        chosen = (
            max(
                feasible,
                key=lambda r: (
                    r["primary"]["mean_freed_minutes"],
                    -r["primary"]["mean_loss_pp"],
                    r["minutes"],
                ),
            )["minutes"]
            if feasible
            else None
        )
        return chosen, rows

    if not primary:
        return {
            "verdict": "NO-GO",
            "reason": "primary_cohort_empty",
            "selected_minutes": None,
        }
    selected, rows = select(primary, controls, False)
    folds = []
    if selected is not None:
        for held in primary:
            remaining = [t for t in primary if t.name != held.name]
            robust = [[t for t in cohort if t.name != held.name] for cohort in controls]
            chosen, _ = select(remaining, robust, True)
            distance = (
                abs(
                    protocol["grid_minutes"].index(selected)
                    - protocol["grid_minutes"].index(chosen)
                )
                if chosen is not None
                else None
            )
            folds.append(
                {
                    "held_out": held.name,
                    "selected_minutes": chosen,
                    "grid_distance": distance,
                }
            )
    stable = selected is not None and all(
        f["grid_distance"] is not None
        and f["grid_distance"] <= protocol["gate"]["maximum_lopo_grid_steps"]
        for f in folds
    )
    return {
        "verdict": "GO" if stable else "NO-GO",
        "reason": (
            "all_preregistered_conditions_passed"
            if stable
            else (
                "no_eligible_threshold"
                if selected is None
                else "leave_one_out_unstable"
            )
        ),
        "selected_minutes": selected,
        "leave_one_out_stable": stable,
        "thresholds": protocol["gate"],
        "grid": rows,
        "leave_one_out": folds,
        "scope": "offline sensitivity analysis; reinvestment is model-based; no Phase 1 launched",
    }


def descriptive(trees: list[ProblemTree], grid: list[float]) -> tuple[dict, list[dict]]:
    gaps, restarts, hazards = [], [], []
    tail_seconds = total_seconds = 0.0
    for tree in trees:
        score = tree.seed_combined_pct
        for attempt in tree.attempts:
            before = score
            clock = attempt.started
            for check in attempt.checks:
                if check.accepted:
                    gaps.append(
                        {
                            "run": tree.run,
                            "name": tree.name,
                            "attempt": attempt.number,
                            "gap_seconds": check.at - clock,
                            "gain_pp": check.combined_pct - score,
                            "kind": "accepted_improvement",
                        }
                    )
                    score, clock = check.combined_pct, check.at
            tail = attempt.ended - clock
            gaps.append(
                {
                    "run": tree.run,
                    "name": tree.name,
                    "attempt": attempt.number,
                    "gap_seconds": tail,
                    "gain_pp": 0,
                    "kind": "censored_tail",
                }
            )
            duration = attempt.ended - attempt.started
            total_seconds += duration
            tail_seconds += tail
            if attempt.number >= 1 and duration > 0:
                restarts.append(
                    {
                        "name": tree.name,
                        "attempt": attempt.number,
                        "gain_pp": score - before,
                        "minutes": duration / 60,
                        "yield_pp_per_minute": (score - before) / (duration / 60),
                    }
                )
    for minutes in grid:
        future_gains = []
        for tree in trees:
            for attempt in tree.attempts:
                clock = attempt.started
                events = [
                    (c.at, c.accepted, c.combined_pct) for c in attempt.checks
                ] + [(attempt.ended, False, 0.0)]
                for index, (at, accepted, _) in enumerate(events):
                    if accepted:
                        clock = at
                    if at - clock >= minutes * 60:
                        future = [c for c in attempt.checks[index + 1 :] if c.accepted]
                        previous = tree.seed_combined_pct
                        for earlier in tree.attempts[: attempt.number]:
                            for c in earlier.checks:
                                if c.accepted:
                                    previous = c.combined_pct
                        for c in attempt.checks[: index + 1]:
                            if c.accepted:
                                previous = c.combined_pct
                        future_gains.append(
                            future[-1].combined_pct - previous if future else 0.0
                        )
                        break
        hazards.append(
            {
                "minutes": minutes,
                "observed_attempts": len(future_gains),
                "probability_later_accepted_improvement": (
                    sum(g > 0 for g in future_gains) / len(future_gains)
                    if future_gains
                    else None
                ),
                "expected_future_gain_pp": mean(future_gains) if future_gains else None,
            }
        )
    uncensored = [
        r["gap_seconds"] / 60 for r in gaps if r["kind"] == "accepted_improvement"
    ]
    return {
        "attempts": sum(len(t.attempts) for t in trees),
        "attempt_minutes": total_seconds / 60,
        "tail_fraction_after_last_accepted": (
            tail_seconds / total_seconds if total_seconds else None
        ),
        "inter_improvement_gap_minutes": {
            "count": len(uncensored),
            "median": median(uncensored) if uncensored else None,
            "maximum": max(uncensored) if uncensored else None,
        },
        "hazard_at_first_observed_stagnation_event": hazards,
        "restart_attempts": restarts,
        "restart_yield_by_index": [
            {
                "attempt": n,
                "count": len(rows),
                "mean_gain_pp": mean(r["gain_pp"] for r in rows),
                "median_yield_pp_per_minute": median(
                    r["yield_pp_per_minute"] for r in rows
                ),
            }
            for n in sorted({r["attempt"] for r in restarts})
            for rows in [[r for r in restarts if r["attempt"] == n]]
        ],
    }, gaps


def validate_output(output: Path, runs: list[Path]) -> None:
    output = output.resolve()
    for run in runs:
        run = run.resolve()
        if output == run or run in output.parents or output in run.parents:
            raise ValueError(f"Replay output overlaps input run: {run}")
    if output.exists():
        raise ValueError(f"Replay output already exists: {output}")


def audit_replay(output: Path) -> dict:
    """Verify saved replay bytes and CSV arithmetic without compiling or sampling."""
    report = json.loads((output / "report.json").read_text())
    for category in ("input_sha256", "source_sha256"):
        for name, expected in report[category].items():
            if digest(name) != expected:
                raise ValueError(f"Replay audit {category} mismatch: {name}")
    for name, expected in report["artifact_sha256"].items():
        if digest(output / name) != expected:
            raise ValueError(f"Replay artifact mismatch: {name}")
    with (output / "per_problem.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    checked = 0
    for label, cohort in report["cohorts"].items():
        for policy, summary in cohort["policies"].items():
            selected = [
                row
                for row in rows
                if f"{row['run']}::{row['model']}/{row['effort']}" == label
                and row["policy"] == policy
            ]
            if len(selected) != summary["problems"]:
                raise ValueError(
                    f"Replay audit cohort-count mismatch: {label}/{policy}"
                )
            for field, csv_field, scale in (
                ("mean_raw_combined_pct", "raw_combined_pct", 1),
                ("mean_loss_pp", "loss_pp", 1),
                ("mean_freed_minutes", "freed_seconds", 60),
            ):
                actual = mean(float(row[csv_field]) / scale for row in selected)
                if abs(actual - summary[field]) > 1e-9:
                    raise ValueError(f"Replay audit arithmetic mismatch: {field}")
            if (
                sum(row["on_support"] == "True" for row in selected)
                != summary["on_support_problems"]
            ):
                raise ValueError("Replay audit support-count mismatch")
            checked += 1
    return {
        "status": "passed",
        "scope": "saved replay bytes and arithmetic; no model or Lean calls",
        "checked_files": len(report["input_sha256"])
        + len(report["source_sha256"])
        + len(report["artifact_sha256"]),
        "cohort_policy_summaries": checked,
        "gate": report["gate"]["verdict"],
    }


def _csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_replay(
    runs: list[Path],
    protocol_path: Path,
    output: Path,
    *,
    pilot: bool = False,
    descriptive_only: bool = False,
) -> dict:
    """Compute a complete report before atomically publishing a fresh directory."""
    validate_output(output, runs)
    reader = EvidenceReader()
    protocol = reader.json(protocol_path)
    if protocol.get("decision_events") != "after_check_and_attempt_end":
        raise ValueError("Unsupported protocol decision semantics")
    cohorts, excluded, identities = {}, [], {}
    for run in runs:
        config = reader.json(run / "config.json")
        trees, exclusions = load_run(
            run, reader=reader, allow_incomplete=descriptive_only
        )
        excluded.extend(exclusions)
        for condition in sorted({t.condition for t in trees}):
            cohort = [t for t in trees if t.condition == condition]
            label = f"{run.resolve()}::{condition[0]}/{condition[1]}"
            comparison = None
            if (run / "comparison.json").exists() and "10_budget_resets" in run.parts:
                comparison = reader.json(run / "comparison.json")
            identities[label] = validate_identity(cohort, comparison)
            if pilot:
                cohort = cohort[:1]
            cohorts[label] = (run.resolve(), config, cohort)
    if not cohorts:
        raise ValueError("No replayable terminal cohorts")
    per_problem, anytime, all_gaps, reports = [], [], [], {}
    primary, controls = [], []
    for label, (run, config, trees) in cohorts.items():
        if list(trees[0].condition) == protocol["condition"]:
            if run.as_posix().endswith(protocol["primary_run"]):
                primary = trees
            if any(run.as_posix().endswith(r) for r in protocol["robustness_runs"]):
                controls.append(trees)
        stats, gaps = descriptive(trees, protocol["grid_minutes"])
        all_gaps.extend(gaps)
        summaries = {}
        full = len(trees) == len(config["names"]) and all(
            t.status == "complete" for t in trees
        )
        for policy in replay.policy_grid(protocol):
            outcomes = [splice(t, policy) for t in trees]
            summaries[policy.name] = summarize(outcomes, restart_yield(trees))
            for tree, outcome in zip(trees, outcomes):
                row = {
                    k: v
                    for k, v in asdict(outcome).items()
                    if k not in ("attempts", "anytime", "condition")
                }
                row.update(
                    model=tree.condition[0],
                    effort=tree.condition[1],
                    start_basis=tree.start_basis,
                )
                per_problem.append(row)
            horizon = max(t.attempts[-1].ended - t.problem_start for t in trees)
            for elapsed in range(
                0,
                int(horizon) + protocol["anytime_step_seconds"],
                protocol["anytime_step_seconds"],
            ):
                scores = [
                    next(score for at, score in reversed(o.anytime) if at <= elapsed)
                    for o in outcomes
                ]
                anytime.append(
                    {
                        "cohort": label,
                        "policy": policy.name,
                        "elapsed_seconds": elapsed,
                        "problems": len(trees),
                        "mean_best_raw_pct": mean(scores),
                    }
                )
        reports[label] = {
            "scope": "full_declared_cohort" if full else "loaded_subset_only",
            "declared_problems": len(config["names"]),
            "loaded_problems": len(trees),
            "complete_loaded_problems": sum(t.status == "complete" for t in trees),
            "policies": summaries,
            "descriptive": stats,
            "timeline_bases": [
                {
                    "name": t.name,
                    "start_basis": t.start_basis,
                    "post_terminal_nonaccepted_check_numbers": [
                        c.number for c in t.post_terminal_checks
                    ],
                    "attempt_end_bases": [a.end_basis for a in t.attempts],
                }
                for t in trees
            ],
        }
    verdict = (
        gate(primary, controls, protocol)
        if not descriptive_only and not pilot
        else {
            "verdict": "NOT_EVALUATED",
            "reason": "descriptive_only" if descriptive_only else "one_problem_pilot",
        }
    )
    reader.verify()
    sources = {
        str(Path(module.__file__).resolve()): digest(module.__file__)
        for module in (discovery_tree, replay)
    }
    sources[str(Path(__file__).resolve())] = digest(__file__)
    result = {
        "at": now(),
        "status": "complete",
        "scope": "saved evidence only; no new model or Lean calls",
        "pilot": pilot,
        "protocol": protocol,
        "protocol_sha256": digest(protocol_path),
        "input_sha256": reader.files,
        "source_sha256": sources,
        "identity": identities,
        "exclusions": excluded,
        "cohorts": reports,
        "gate": verdict,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".replay-", dir=output.parent) as temporary:
        stage = Path(temporary) / "report"
        stage.mkdir()
        _csv(stage / "per_problem.csv", per_problem)
        _csv(stage / "anytime.csv", anytime)
        _csv(stage / "gaps.csv", all_gaps)
        rows = [
            "# Offline stopping-policy replay",
            "",
            f"Gate: **{verdict['verdict']}** ({verdict['reason']}).",
            "",
            "No new model or Lean calls. Scores are local raw accepted incumbents before cleanup. Spliced histories assume unchanged behavior under shifted restart prompts. Reinvestment and cost interpolation are model-based estimates.",
            "",
            "Protocol thresholds: 12/15 on support; mean loss <=0.10 pp; freed time >=8 min/problem; estimated reinvestment >=2x lost gain; <=0.10 pp loss separately on stages 06 and 08; leave-one-out within one grid step.",
            "",
            "| Cohort | Policy | Raw score | Loss pp | Freed min/problem | On support |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
        for label, report in reports.items():
            for name, s in report["policies"].items():
                rows.append(
                    f"| {label.split('/results/harness/')[-1]} ({report['scope']}) | {name} | {s['mean_raw_combined_pct']:.6f} | {s['mean_loss_pp']:.6f} | {s['mean_freed_minutes']:.3f} | {s['on_support_problems']}/{s['problems']} |"
                )
        rows.extend(
            ["", "## Exclusions", "", *(json.dumps(r) for r in excluded)]
            if excluded
            else ["", "Exclusions: none."]
        )
        (stage / "README.md").write_text("\n".join(rows) + "\n")
        result["artifact_sha256"] = {
            path.name: digest(path) for path in stage.iterdir() if path.is_file()
        }
        write_json(stage / "report.json", result)
        reader.verify()
        if output.exists():
            raise ValueError(f"Output created concurrently: {output}")
        os.rename(stage, output)
    return result
