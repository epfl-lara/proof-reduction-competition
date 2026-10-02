"""Plot saved benchmark scores; no Lean calls or new reference measurements.

Usage: python src/plot_experiments.py
Reads results/deterministic_comparison.json and writes results/score_progress.svg.
Requires matplotlib, an optional plotting dependency already present in af.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re


COLORS = {"Prior stages": "#8793A5", "New methods": "#4165D5", "Repeat sweeps": "#078F79"}
METHOD_LABELS = {
    "lint": "Tactic deletion", "simp": "Explicit simp", "wrappers": "Return wrappers",
    "facts": "Local fact deletion", "reuse": "Fact reuse", "menu": "Tactic menu",
    "search": "Library search", "simp_min": "Simp lists", "arith_min": "Arithmetic hints",
    "rw_min": "Rewrite lists",
}


def stage_label(stage, index):
    """Disambiguate repeated method names with both sequence and sweep indices."""
    path = stage.get("stage_path", stage["stage"])
    sweep = re.search(r"(?:^|/)sweep_(\d+)(?:/|$)", path)
    method = METHOD_LABELS.get(stage.get("method"), stage["stage"].replace("_", " "))
    if sweep:
        return f"{index:02d}  S{int(sweep.group(1))} · {method}", "Repeat sweeps"
    prior = stage["stage"] in {"01_linter_deletion", "02_explicit_simp"}
    return f"{index:02d}  {method}", "Prior stages" if prior else "New methods"


def _number(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def plot_comparison(comparison, output):
    """Save an SVG for a complete, sequential comparison starting at the control."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import MaxNLocator

    stages = comparison.get("stages", [])
    control = comparison.get("original_control_mean", {}).get("combined_pct")
    if not stages or not _number(control):
        raise ValueError("A measured original control and at least one stage are required")
    points = [control]
    labels, phases, gains = [], [], []
    for index, stage in enumerate(stages, 1):
        before = stage.get("full_benchmark_initial_mean", {}).get("combined_pct")
        after = stage.get("full_benchmark_final_mean", {}).get("combined_pct")
        if not stage.get("complete_benchmark") or not _number(before) or not _number(after):
            raise ValueError(f"Incomplete benchmark score at {stage.get('stage_path', stage['stage'])}")
        if not math.isclose(before, points[-1], abs_tol=1e-8, rel_tol=1e-10):
            raise ValueError("Stages must be sequential and start from the measured original control")
        label, phase = stage_label(stage, index)
        labels.append(label)
        phases.append(phase)
        gains.append(after - before)
        points.append(after)

    count = len(stages)
    bar_height = max(1.7, count * 0.29)
    height = 4.6 + bar_height
    style = {"font.family": "DejaVu Sans", "font.size": 9,
             "axes.labelcolor": "#263445", "text.color": "#263445",
             "xtick.color": "#526070", "ytick.color": "#263445",
             "axes.edgecolor": "#D5DCE5", "svg.fonttype": "none",
             "svg.hashsalt": "proof-reduction-score-progress"}
    with plt.rc_context(style):
        fig = plt.figure(figsize=(10.5, height), facecolor="white")
        # Keep the inter-panel gap near 0.7 inches even for 30+ stage rows.
        grid = fig.add_gridspec(2, 1, height_ratios=[2.4, bar_height],
                               hspace=1.4 / max(height - 2.5, 1))
        ax_score = fig.add_subplot(grid[0])
        ax_gain = fig.add_subplot(grid[1])
        fig.subplots_adjust(left=0.27, right=0.93, top=1 - 0.90 / height, bottom=0.90 / height)
        fig.suptitle("Deterministic proof optimization", x=0.06, y=1 - 0.13 / height,
                     ha="left", fontsize=16, fontweight="bold")
        final = stages[-1]
        problems = comparison.get("expected_problems", final.get("expected_problems", "?"))
        passed, expected = final.get("passed_version_checks", "?"), final.get("expected_version_checks", "?")
        fig.text(0.06, 1 - 0.46 / height,
                 f"Warm-up benchmark · {problems} proofs · local score proxy · final version checks: {passed}/{expected} pass",
                 fontsize=9, color="#526070")

        ax_score.plot(range(count + 1), points, color="#C4CDD8", linewidth=1.6, zorder=1)
        ax_score.scatter([0], [control], s=34, color="#263445", zorder=3)
        for index, phase in enumerate(phases, 1):
            ax_score.plot([index - 1, index], points[index - 1:index + 1],
                          color=COLORS[phase], linewidth=2, zorder=2)
            ax_score.scatter([index], [points[index]], s=24, color=COLORS[phase], zorder=3)
        ax_score.annotate(f"Control {control:.3f}%", (0, control), xytext=(6, -15),
                          textcoords="offset points", fontsize=9)
        ax_score.annotate(f"Final {points[-1]:.3f}%", (count, points[-1]), xytext=(-3, 10),
                          ha="right", textcoords="offset points", fontsize=10, fontweight="bold")
        ax_score.set_title("Cumulative combined score", loc="left", fontsize=11, pad=13)
        ax_score.set_ylabel("Benchmark mean (%)")
        ax_score.set_xlabel("Stage sequence; 0 = measured original control")
        ax_score.xaxis.set_major_locator(MaxNLocator(nbins=min(count + 1, 10), integer=True))
        span = max(points) - min(points)
        padding = max(span * 0.15, 0.2)
        ax_score.set_ylim(min(points) - padding, max(points) + padding * 1.5)
        ax_score.set_xlim(-0.15, count + 0.35)
        ax_score.grid(axis="y", color="#E8EDF3", linewidth=0.7)
        ax_score.set_axisbelow(True)

        colors = [COLORS[phase] for phase in phases]
        ax_gain.barh(range(count), gains, color=colors, height=0.68, zorder=2)
        ax_gain.set_yticks(range(count), labels, fontsize=8.5)
        ax_gain.invert_yaxis()
        ax_gain.set_xlabel("Gain over preceding stage (percentage points)")
        ax_gain.set_title("Marginal gain from each bounded stage", loc="left", fontsize=11, pad=13)
        ax_gain.axvline(0, color="#A9B5C3", linewidth=0.8, zorder=1)
        extent = max(max(gains), 0.05) - min(min(gains), 0)
        offset = max(extent * 0.012, 0.003)
        for index, gain in enumerate(gains):
            if abs(gain) < 1e-12:
                ax_gain.scatter([0], [index], s=10, color=colors[index], zorder=3)
            label = "0.000" if abs(gain) < 1e-12 else f"{gain:+.3f}"
            ax_gain.text(gain + (offset if gain >= 0 else -offset), index, label,
                         va="center", ha="left" if gain >= 0 else "right", fontsize=8)
        ax_gain.set_xlim(min(min(gains), 0) - extent * 0.12, max(max(gains), 0.05) + extent * 0.20)
        ax_gain.grid(axis="x", color="#E8EDF3", linewidth=0.7)
        ax_gain.set_axisbelow(True)
        present = [phase for phase in COLORS if phase in phases]
        fig.legend([Patch(facecolor=COLORS[phase]) for phase in present], present,
                   loc="lower left", bbox_to_anchor=(0.06, 0.34 / height), frameon=False,
                   ncol=len(present), fontsize=8.5)
        for axes in (ax_score, ax_gain):
            axes.spines[["top", "right"]].set_visible(False)
            axes.tick_params(length=0)
        fig.text(0.06, 0.18 / height,
                 "Combined = mean(token reduction, heartbeat reduction, compatibility). Cached local reference denominators.\n"
                 "Sequential gains from bounded search; not independent ablations or an arena submission.",
                 fontsize=7.5, color="#637183", va="center")
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, format="svg", metadata={"Date": None,
                    "Title": "Deterministic warm-up proof optimization: cumulative score and marginal gains",
                    "Description": f"Local proxy; dataset SHA256 {comparison.get('dataset_sha256', 'unrecorded')}. "
                                   f"Measured control {control}; final score {points[-1]}."})
        plt.close(fig)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/deterministic_comparison.json"))
    parser.add_argument("--output", type=Path, default=Path("results/score_progress.svg"))
    args = parser.parse_args(argv)
    try:
        output = plot_comparison(json.loads(args.input.read_text()), args.output)
    except (OSError, ValueError, ImportError) as exc:
        parser.error(str(exc))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
