"""Execute the deterministic ablations, then bounded repeated portfolio sweeps.

Each child is independently resumable. Keep this process in a durable terminal
or rerun the same command after interruption. It stops on unavailable discovery,
a full no-improvement sweep, or the explicit sweep cap, never on a hidden budget.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from audit_experiments import audit
from run_deterministic import digest, write_json


STAGES = (
    ("03_wrappers", "wrappers"), ("04_local_facts", "facts"),
    ("05_fact_reuse", "reuse"), ("06_tactic_menu", "menu"),
    ("07_library_search", "search"), ("08_simp_minimization", "simp_min"),
    ("09_arithmetic_minimization", "arith_min"), ("10_rewrite_minimization", "rw_min"),
)
REPEAT = tuple(method for _, method in STAGES) + ("lint", "simp")


def stage_workers(output, requested):
    """Keep an existing stage's fingerprint; scale only stages not started yet."""
    path = Path(output) / "config.json"
    workers = json.loads(path.read_text())["workers"] if path.exists() else requested
    if not isinstance(workers, int) or workers < 1:
        raise ValueError("Worker count must be a positive integer")
    return workers


def finished_stage(output, input_path, method, budget, references):
    """Reuse complete, audited historical evidence, including archived code."""
    run_path = Path(output) / "run.json"
    if not run_path.exists() or json.loads(run_path.read_text()).get("status") != "finished":
        return False
    config = json.loads((Path(output) / "config.json").read_text())
    if (config["method"] != method or config["budget"] != budget
            or config["input_sha256"] != digest(input_path)):
        raise ValueError(f"Completed stage has different inputs, method or budget: {output}")
    audit([output], references=references, check_code=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=Path("results/deterministic"))
    parser.add_argument("--input", type=Path, default=Path("results/deterministic/02_explicit_simp/candidates.jsonl"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-rounds", type=int, default=6)
    parser.add_argument("--max-trials", type=int, default=64)
    parser.add_argument("--max-sites", type=int, default=6)
    parser.add_argument("--max-sweeps", type=int, default=2)
    parser.add_argument("--min-gain", type=float, default=0.05)
    args = parser.parse_args()
    if args.max_sweeps < 0 or args.workers < 1:
        parser.error("Sweep count must be nonnegative and workers positive")
    args.output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_root / "portfolio.json"
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    manifest = {"config": config, "started_at": datetime.now(timezone.utc).isoformat(),
                "stages": [], "sweeps": [], "status": "running", "worker_changes": []}
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if ({k: v for k, v in old["config"].items() if k != "workers"}
                != {k: v for k, v in config.items() if k != "workers"}):
            parser.error("Portfolio configuration changed; choose a new output root")
        manifest["started_at"] = old["started_at"]
        manifest["worker_changes"] = old.get("worker_changes", [])
        if old["config"]["workers"] != config["workers"]:
            manifest["worker_changes"].append({"at": datetime.now(timezone.utc).isoformat(),
                                                "from": old["config"]["workers"], "to": config["workers"],
                                                "scope": "new stages only; existing stage settings preserved"})
    previous = args.input.parent
    candidate_path = args.input
    baseline = args.input.parent.parent / "01_linter_deletion"
    references = args.input.parent.parent / "00_reference_baseline" / "reference_values.jsonl"

    def stage(relative_path, method):
        nonlocal previous, candidate_path
        output = args.output_root / relative_path
        cmd = [sys.executable, "src/run_experiments.py", "--method", method, "--output", str(output),
               "--input", str(candidate_path), "--workers", str(stage_workers(output, args.workers)),
               "--max-rounds", str(args.max_rounds), "--max-trials", str(args.max_trials),
               "--max-sites", str(args.max_sites), "--min-gain", str(args.min_gain)]
        manifest["active_stage"] = str(output)
        write_json(manifest_path, manifest)
        budget = {"rounds": args.max_rounds, "trials": args.max_trials,
                  "sites": args.max_sites, "min_gain": args.min_gain}
        if not finished_stage(output, candidate_path, method, budget, references):
            subprocess.run(cmd, check=True)
        subprocess.run([sys.executable, "src/report_experiments.py", "--stage", str(output),
                        "--previous", str(previous), "--baseline", str(baseline)], check=True)
        summary = json.loads((output / "summary.json").read_text())
        if summary["full_benchmark_combined_pct"] is None:
            raise RuntimeError(f"Incomplete benchmark coverage: {output}")
        manifest["stages"].append({"path": str(output), "method": method,
                                    "combined_pct": summary["full_benchmark_combined_pct"],
                                    "delta_pp": summary["full_benchmark_delta_pp"]})
        previous, candidate_path = output, output / "candidates.jsonl"
        write_json(manifest_path, manifest)
        return summary

    try:
        for path, method in STAGES:
            stage(Path(path), method)
        for sweep in range(1, args.max_sweeps + 1):
            delta = 0.0
            changes = 0
            for index, method in enumerate(REPEAT, 1):
                result = stage(Path("11_repeated_sweeps") / f"sweep_{sweep:02d}" / f"{index:02d}_{method}", method)
                delta += result["full_benchmark_delta_pp"]
                changes += result["changed_problems"]
            manifest["sweeps"].append({"sweep": sweep, "delta_pp": delta, "changed_problem_stages": changes})
            if changes == 0:
                manifest["stop_reason"] = "no_improvement_in_bounded_portfolio_sweep"
                break
        else:
            manifest["stop_reason"] = "sweep_limit"
        manifest.update(status="finished", selected_candidates=str(candidate_path),
                        finished_at=datetime.now(timezone.utc).isoformat())
    except BaseException as exc:
        manifest.update(status="interrupted", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        write_json(manifest_path, manifest)
    subprocess.run([sys.executable, "src/report_experiments.py", "--stages",
                    str(baseline), str(args.input.parent),
                    *[s["path"] for s in manifest["stages"]], "--output-root", str(args.output_root)], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
