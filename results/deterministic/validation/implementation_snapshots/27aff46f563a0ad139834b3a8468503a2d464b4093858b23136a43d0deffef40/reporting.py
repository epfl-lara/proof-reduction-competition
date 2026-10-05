"""Report saved deterministic experiments without running Lean or modifying evidence.

One-stage usage: --stage results/03_wrappers --previous results/02_explicit_simp
Comparison usage: --stages results/01_linter_deletion results/02_explicit_simp ...
The original control is stage 01's measured initial state, not an idealized 33.333.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import textwrap
from pathlib import Path

from .statistics import build_comparison, stage_report

FIELDS = (
    "length_reduction_pct",
    "heartbeat_reduction_pct",
    "compatibility_pct",
    "combined_pct",
)
LABELS = ("Token reduction", "Heartbeat reduction", "Compatibility", "Combined")
METHODS = {
    "lint": "Delete tactics nominated by Lean's unused/unreachable-tactic linters.",
    "simp": "Replace existing simplifier calls with compiler-suggested explicit lemma sets.",
    "wrappers": "Contract local return wrappers using parsed syntax spans.",
    "facts": "Try deleting local facts, then recheck the complete declaration.",
    "reuse": "Try reusing an existing local fact instead of proving it again.",
    "menu": "Try the fixed goal-closing tactic menu at selected parsed sites.",
    "search": "Ask deterministic Lean search tactics for explicit proof suggestions.",
    "simp_min": "Remove chunks and individual arguments from explicit simplifier lists.",
    "arith_min": "Remove chunks and individual arithmetic hints while preserving tactic controls.",
    "rw_min": "Remove rewrite-list entries while preserving the order of retained rewrites.",
}


def _number(value, signed=False):
    return (
        "unavailable" if value is None else format(value, "+.3f" if signed else ".3f")
    )


def render_stage(report):
    """Render the computed report without consulting mutable evaluator state."""
    r = report
    title = r["stage"].replace("_", " ")
    lines = [
        f"# {title}",
        "",
        f"Stage: `{r['stage_path']}`.",
        "",
        METHODS.get(r["method"], f"Method: `{r['method']}`."),
        "",
        f"**{r['changed_problems']} of {r['expected_problems']} proofs changed. "
        f"The selected outputs pass {r['passed_version_checks']}/{r['expected_version_checks']} required version checks.**",
        "",
        f"Fully scored problems: {r['fully_scored_problems']}/{r['expected_problems']}. "
        f"Full-benchmark combined score: **{_number(r['full_benchmark_final_mean']['combined_pct'])}%**. "
        f"Gain over the preceding stage: **{_number(r['delta_previous_pp']['combined_pct'], True)} pp**; "
        f"gain over the measured original control: **{_number(r['delta_original_pp']['combined_pct'], True)} pp**.",
        "",
        "| Full warm-up mean | Initial | Selected | Change (pp) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for field, label in zip(FIELDS, LABELS):
        lines.append(
            f"| {label} | {_number(r['full_benchmark_initial_mean'][field])} | "
            f"{_number(r['full_benchmark_final_mean'][field])} | {_number(r['delta_initial_pp'][field], True)} |"
        )
    if not r["complete_benchmark"]:
        lines += [
            "",
            "The benchmark is incomplete. Subset means are retained in report.json; they are not presented as full-benchmark gains.",
        ]
    lines += [
        "",
        "## Search and limits",
        "",
        f"Configuration: `{json.dumps(r['budget'], sort_keys=True)}`.",
        "",
        f"Recorded totals: `{json.dumps(r['counters'], sort_keys=True)}`. "
        "Null counters were not recorded by that runner.",
        "",
        f"Budget stops: **{r['cap_stopped_problems']}**. Stop reasons: `{json.dumps(r['stop_reasons'], sort_keys=True)}`.",
        "",
        f"Primary-only screened trial events: {r['primary_screened_events']}. "
        f"Version-check outcomes: `{json.dumps(r['version_check_statuses'], sort_keys=True)}`.",
        "",
        f"Candidate evaluation statuses: `{json.dumps(r['candidate_status_counts'], sort_keys=True)}`. "
        f"Decision outcomes: `{json.dumps(r['candidate_outcome_counts'], sort_keys=True)}`.",
        "",
        f"Discovery statuses: `{json.dumps(r['discovery_status_counts'], sort_keys=True)}`. "
        f"Tactic outcomes: `{json.dumps(r['tactic_outcome_status_counts'], sort_keys=True)}`. "
        f"Proposal/analysis error events and diagnostics: **{r['proposal_error_count']}** "
        f"(`{json.dumps(r['proposal_error_counts_by_kind'], sort_keys=True)}`). "
        "The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.",
    ]
    changed = sorted(
        (p for p in r["per_problem"] if p["changed"]),
        key=lambda p: -(p["gain_pp"] or 0),
    )
    if changed:
        lines += [
            "",
            "## Changed proofs",
            "",
            "| Problem | Tokens before → after | Combined gain (pp) | Stop |",
            "| --- | ---: | ---: | --- |",
        ]
        for p in changed:
            name = p["name"].replace("|", "\\|")
            lines.append(
                f"| `{name}` | {p['initial_tokens']} → {p['final_tokens']} | {_number(p['gain_pp'], True)} | {p['stop_reason']} |"
            )
    else:
        lines += [
            "",
            "No improvement was selected under this stage's recorded search and acceptance budgets.",
        ]
    example = r.get("accepted_example")
    if example:

        def snippet(text):
            return textwrap.dedent(" " * example.get("start_column", 0) + text)

        lines += [
            "",
            "## Accepted example",
            "",
            f"`{example['name']}` — trial {example['trial']} in "
            f"[{example['log_file']}]({example['log_file']}). "
            f"This accepted **single edit** changes the complete candidate's combined score from "
            f"{_number(example['initial_combined_pct'])}% to {_number(example['final_combined_pct'])}% "
            f"(**{_number(example['combined_gain_pp'], True)} pp**).",
            "",
            "Before (enclosing indentation removed):",
            "",
            "```lean",
            snippet(example["before"]),
            "```",
            "",
        ]
        if example["after"]:
            lines += ["After:", "", "```lean", snippet(example["after"]), "```"]
        else:
            lines += ["After: this fragment is deleted."]
    lines += ["", "## Interpretation", ""] + [f"- {c}" for c in r["caveats"]]
    lines += [
        "",
        "Evidence: [configuration](config.json), [runner summary](summary.json), "
        "[computed report](report.json), [selected proofs](candidates.jsonl), "
        "and the per-problem `problem_*.json` / `trials_*.jsonl` records.",
        "",
    ]
    return "\n".join(lines)


def _write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def write_stage_report(stage, previous=None, **kwargs):
    report = stage_report(stage, previous, **kwargs)
    _write(
        Path(stage) / "report.json",
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
    )
    _write(Path(stage) / "README.md", render_stage(report))
    return report


def write_comparison(stages, *, output_root=None, **kwargs):
    stages = list(stages)
    result = build_comparison(stages, **kwargs)
    root = Path(output_root) if output_root else Path(stages[0]).parent
    _write(
        root / "deterministic_comparison.json",
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
    )
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=(
            "stage",
            "stage_path",
            "method",
            *FIELDS,
            "gain_previous_pp",
            "gain_original_pp",
            "fully_scored_problems",
            "passed_version_checks",
            "expected_version_checks",
            "changed_problems",
            "attempts",
            "cap_stopped_problems",
            "wall_seconds",
        ),
    )
    writer.writeheader()
    for stage in result["stages"]:
        writer.writerow(
            {
                "stage": stage["stage"],
                "stage_path": stage["stage_path"],
                "method": stage["method"],
                **stage["full_benchmark_final_mean"],
                "gain_previous_pp": stage["delta_previous_pp"]["combined_pct"],
                "gain_original_pp": stage["delta_original_pp"]["combined_pct"],
                **{
                    k: stage[k]
                    for k in (
                        "fully_scored_problems",
                        "passed_version_checks",
                        "expected_version_checks",
                        "changed_problems",
                        "cap_stopped_problems",
                    )
                },
                "attempts": stage["counters"]["attempts"],
                "wall_seconds": stage["counters"]["wall_seconds"],
            }
        )
    _write(root / "deterministic_comparison.csv", output.getvalue())
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--stage", type=Path)
    choice.add_argument("--stages", type=Path, nargs="+")
    parser.add_argument("--previous", type=Path)
    parser.add_argument(
        "--dataset", type=Path, default=Path("data/benchmark_data_warmup.jsonl")
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Stage whose initial records are the unchanged measured control",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        help="Comparison output folder; defaults to the first stage's parent",
    )
    args = parser.parse_args(argv)
    if args.stage and args.output_root or args.stages and args.previous:
        parser.error("--output-root applies to --stages; --previous applies to --stage")
    kwargs = {"dataset": args.dataset, "baseline": args.baseline}
    try:
        if args.stage:
            result = write_stage_report(args.stage, args.previous, **kwargs)
            print(
                json.dumps(
                    {
                        k: result[k]
                        for k in (
                            "stage",
                            "stage_path",
                            "fully_scored_problems",
                            "passed_version_checks",
                            "changed_problems",
                        )
                    }
                )
            )
        else:
            result = write_comparison(
                args.stages, output_root=args.output_root, **kwargs
            )
            print(json.dumps({"stages": [s["stage_path"] for s in result["stages"]]}))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
