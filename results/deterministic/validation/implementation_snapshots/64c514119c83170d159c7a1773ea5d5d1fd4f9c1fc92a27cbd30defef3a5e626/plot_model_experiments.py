"""Export complete-cohort comparison figures from saved experiment reports.

No model requests, compiler runs, or report regeneration. Incomplete conditions
remain masked even when a report contains an observed partial-cohort mean.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys


ARM_ORDER = ("plain", "cards", "goals", "cards_goals", "cards_goals_costs")
ARM_LABELS = {"plain": "Plain", "cards": "Cards", "goals": "Goals",
              "cards_goals": "Cards +\ngoals", "cards_goals_costs": "Cards + goals\n+ costs"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def read_report(path):
    raw = path.read_bytes()
    report = json.loads(raw)
    return report, {"path": str(path.resolve()), "sha256": sha(raw),
                    "created_at": report.get("created_at"), "status": report["status"]}


def condition_index(report):
    index = {}
    for row in report["conditions"]:
        key = row["model"], row["arm"]
        if key in index:
            raise ValueError("Duplicate model/arm condition")
        index[key] = row
    return index


def prepare_panels(repair, combined):
    """Keep full precision and explicit mask reasons before rendering."""
    repaired, cleaned = condition_index(repair), condition_index(combined)
    if set(repaired) != set(cleaned):
        raise ValueError("The two reports declare different model/context conditions")
    if (not repair["cohort_is_full_base_matrix"]
            or set(repair["base_names"]) != set(combined["names"])
            or repair["problem_count"] != combined["problem_count"]):
        raise ValueError("Use reports from the same complete declared theorem cohort")
    models = list(dict.fromkeys(row["model"] for row in combined["conditions"]))
    arm_set = {row["arm"] for row in combined["conditions"]}
    arms = [arm for arm in ARM_ORDER if arm in arm_set] + sorted(arm_set - set(ARM_ORDER))
    if set(cleaned) != {(model, arm) for model in models for arm in arms}:
        raise ValueError("Missing declared model/context condition")
    expected = combined["problem_count"]
    controls_ready = combined["completed_controls"] == expected
    definitions = [
        ("h_minus_d1", "H − D1: model branch above the deterministic control", "gain_h_minus_d1_pp"),
        ("h_minus_l", "H − L: gain from cleanup and control fallback", "gain_h_minus_l_pp"),
        ("initial_valid", "Initial proposal: confirmed all-version validity", "initial_all_versions_valid"),
        ("final_valid", "After up to 3 correctness repairs: confirmed validity", "final_all_versions_valid"),
    ]
    panels = {}
    for label, title, field in definitions:
        rows = []
        for model in models:
            row_cells = []
            for arm in arms:
                c, r = cleaned[model, arm], repaired[model, arm]
                if c["expected_problems"] != expected or r["expected_problems"] != expected:
                    raise ValueError("Condition denominator differs from the declared cohort")
                if label.startswith("h_"):
                    count = c["complete_cleanup_problems"]
                    ready = c["complete"] and count == expected and controls_ready
                    value = c[field] if ready and finite(c[field]) else None
                    reason = None if value is not None else (
                        "controls incomplete" if count == expected and not controls_ready else
                        "cleanup incomplete" if not ready else "score unavailable")
                    annotation = f"{value:+.6f}" if value is not None else (
                        "controls\npending" if reason == "controls incomplete" else
                        f"pending\n{count}/{expected}" if not ready else "unavailable")
                    if value is not None and value < -1e-9:
                        raise ValueError("Combined selection should not regress D1 or L")
                else:
                    initial = label == "initial_valid"
                    count = r["initial_recorded" if initial else "repair_recorded"]
                    ready = r["initial_complete" if initial else "repair_complete"] and count == expected
                    valid = r[field]
                    if not isinstance(valid, int) or not 0 <= valid <= count <= expected:
                        raise ValueError("Invalid validity numerator or denominator")
                    value = 100 * valid / expected if ready else None
                    reason = None if ready else "initial outcomes incomplete" if initial else "repair outcomes incomplete"
                    annotation = f"{valid}/{expected} valid" if ready else f"pending\n{count}/{expected}"
                    if ready and not initial:
                        annotation += f"\n{r['valid_changed_proposals']} changed"
                row_cells.append({"model": model, "arm": arm, "value": value,
                                  "recorded": count, "expected": expected,
                                  "mask_reason": reason, "annotation": annotation})
            rows.append(row_cells)
        panels[label] = {"title": title, "unit": "percentage points" if label.startswith("h_") else
                         "percent of declared problems with a confirmed valid output", "cells": rows}
    return models, arms, panels


def render_pair(*, plt, np, output, stem, title, subtitle, footer, labels,
                panels, models, arms, gains, dpi):
    fig, axes = plt.subplots(2, 1, figsize=(12, 8.5))
    fig.subplots_adjust(left=.25, right=.88, top=.83, bottom=.17, hspace=.66)
    fig.suptitle(title, x=.25, y=.972, ha="left", fontsize=17, fontweight="bold")
    fig.text(.25, .915, subtitle, ha="left", fontsize=10, color="#444444")
    values = [cell["value"] for label in labels for row in panels[label]["cells"]
              for cell in row if cell["value"] is not None]
    vmax = max(max(values, default=0), 1) if gains else 100
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("#e8ebef")
    image = None
    for ax, label in zip(axes, labels):
        panel = panels[label]
        matrix = np.array([[np.nan if cell["value"] is None else cell["value"] for cell in row]
                           for row in panel["cells"]])
        image = ax.imshow(np.ma.masked_invalid(matrix), cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
        ax.set_title(panel["title"], loc="left", pad=13, fontsize=11, fontweight="bold")
        ax.set_xticks(range(len(arms)), [ARM_LABELS.get(arm, arm) for arm in arms], fontsize=10)
        ax.set_yticks(range(len(models)), [model.split("/")[-1] for model in models], fontsize=10)
        ax.set_xticks(np.arange(-.5, len(arms), 1), minor=True)
        ax.set_yticks(np.arange(-.5, len(models), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=2)
        ax.tick_params(which="both", length=0)
        ax.tick_params(axis="y", pad=10)
        ax.tick_params(axis="x", pad=8)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for i, row in enumerate(panel["cells"]):
            for j, cell in enumerate(row):
                value = cell["value"]
                color = "#667080" if value is None else "white" if value / vmax < .52 else "#142220"
                ax.text(j, i, cell["annotation"], ha="center", va="center", fontsize=10, color=color,
                        linespacing=1.4, fontweight="normal" if value is None else "medium")
    if values:
        cax = fig.add_axes([.915, .265, .014, .455])
        colorbar = fig.colorbar(image, cax=cax)
        colorbar.set_label("Score gain (percentage points)" if gains else "Confirmed valid outputs (%)", fontsize=9)
        colorbar.ax.tick_params(labelsize=9)
    else:
        fig.text(.25, .105, "Gray cells: condition incomplete. No full-cohort values are available in this snapshot.",
                 fontsize=9, color="#536171")
    fig.text(.25, .025, footer, fontsize=8.6, ha="left", va="bottom", linespacing=1.5, color="#4d4d4d")
    outputs = []
    for suffix in ("png", "svg"):
        path = output / f"{stem}.{suffix}"
        fig.savefig(path, dpi=dpi, facecolor="white", metadata={"Creator": "plot_model_experiments.py"}
                    if suffix == "svg" else {"Software": "plot_model_experiments.py"})
        outputs.append({"path": path.name, "sha256": sha(path.read_bytes())})
    plt.close(fig)
    return outputs


def run(root, output, dpi=180):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Matplotlib is required; use the existing af environment. No dependencies were installed.") from exc
    root, output = Path(root).resolve(), Path(output).resolve()
    repair, repair_source = read_report(root / "03_repaired_context_ablation" / "report.json")
    combined, combined_source = read_report(root / "04_combined_deterministic" / "report.json")
    models, arms, panels = prepare_panels(repair, combined)
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none", "axes.unicode_minus": True})
    total = len(models) * len(arms)
    gain_complete = sum(cell["value"] is not None for row in panels["h_minus_d1"]["cells"] for cell in row)
    initial_complete = sum(cell["value"] is not None for row in panels["initial_valid"]["cells"] for cell in row)
    final_complete = sum(cell["value"] is not None for row in panels["final_valid"]["cells"] for cell in row)
    d0 = combined["baseline_d0_mean"]["combined_pct"]
    d1 = combined["control_d1_mean"]["combined_pct"]
    baseline = f"D0 {d0:.6f}% · D1 {d1:.6f}%" if finite(d1) else f"D0 {d0:.6f}% · D1 pending"
    partial_gain = gain_complete != total
    partial_validity = initial_complete != total or final_complete != total
    output_files = render_pair(plt=plt, np=np, output=output, stem="combined_gains",
        title="Combined competition-score gains",
        subtitle=f"{'PARTIAL SNAPSHOT' if partial_gain else 'COMPLETE COHORTS'} · {gain_complete}/{total} conditions available · {combined['problem_count']} problems per condition\n{baseline}",
        footer="H: combined selection. D1: additional deterministic control. L: model + correctness-repair selection.\n"
               "Gray means incomplete or unavailable; gains use only complete cohorts. No pooling across arms or models.\n"
               "One stochastic proposal per cell; descriptive development comparison. Input report hashes are in provenance.json.",
        labels=("h_minus_d1", "h_minus_l"), panels=panels, models=models, arms=arms, gains=True, dpi=dpi)
    output_files += render_pair(plt=plt, np=np, output=output, stem="valid_output_yield",
        title="All-version-valid output yield",
        subtitle=f"{'PARTIAL SNAPSHOT' if partial_validity else 'COMPLETE COHORTS'} · complete initial conditions {initial_complete}/{total}; repaired {final_complete}/{total}\n"
                 "Only completed fifteen-problem conditions receive a validity fraction.",
        footer="Denominator: all declared problems, including failures and unavailable responses; numerator: confirmed valid outputs.\n"
               "Final validity includes unchanged-incumbent returns; 'changed' excludes them. Validity alone is not optimization.\n"
               "Gray cells remain pending. An unavailable response is unconfirmed, not recoded as a compiler failure.",
        labels=("initial_valid", "final_valid"), panels=panels, models=models, arms=arms, gains=False, dpi=dpi)
    provenance = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                  "script": str(Path(__file__).resolve()), "script_sha256": sha(Path(__file__).read_bytes()),
                  "python_version": sys.version.split()[0], "matplotlib_version": matplotlib.__version__,
                  "numpy_version": np.__version__, "dpi": dpi,
                  "sources": {"repair": repair_source, "combined": combined_source},
                  "models": models, "arms": arms, "panels": panels, "outputs": output_files,
                  "rules": ["No incomplete-condition means or observed partial means are plotted.",
                            "Unknown scores remain null and gray, never zero.",
                            "Validity is confirmed-output yield over all declared problems, not a pass rate restricted to compiler checks.",
                            "Gain annotations are rounded to six decimals; this JSON retains full stored precision.",
                            "Counts and status come from the source report snapshots, not live worker state.",
                            "No selection is pooled across models or arms."]}
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/one_shot"), help="Parent directory of stages 03 and 04")
    parser.add_argument("--output", type=Path, help="Defaults to INPUT/figures")
    parser.add_argument("--dpi", type=int, default=180)
    args = parser.parse_args(argv)
    if args.dpi < 72:
        parser.error("Use --dpi of at least 72")
    provenance = run(args.input, args.output or args.input / "figures", args.dpi)
    print(json.dumps({"output": str((args.output or args.input / "figures").resolve()),
                      "files": [row["path"] for row in provenance["outputs"]],
                      "complete_gain_conditions": sum(cell["value"] is not None for row in provenance["panels"]["h_minus_d1"]["cells"] for cell in row)}))


if __name__ == "__main__":
    main()
