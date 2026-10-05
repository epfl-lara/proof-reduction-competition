"""Dataset-independent batch interface for the complete deterministic portfolio.

Run from any working directory. Inputs and output are explicit; environment
setup and reference preparation are separate operations. Child progress goes to
stderr; the CLI writes one machine-readable JSON result to stdout.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from proof_eval import Evaluator
from proof_eval.evidence.audit import audit
from proof_eval.evidence.io import digest, write_json
from proof_eval.optimization.reporting import write_comparison, write_stage_report
from proof_eval.paths import ROOT as REPOSITORY

METHODS = (
    "lint",
    "simp",
    "wrappers",
    "facts",
    "reuse",
    "menu",
    "search",
    "simp_min",
    "arith_min",
    "rw_min",
)
FOLDERS = dict(
    zip(
        METHODS,
        (
            "01_linter_deletion",
            "02_explicit_simp",
            "03_wrappers",
            "04_local_facts",
            "05_fact_reuse",
            "06_tactic_menu",
            "07_library_search",
            "08_simp_minimization",
            "09_arithmetic_minimization",
            "10_rewrite_minimization",
        ),
    )
)
REPEAT = METHODS[2:] + METHODS[:2]


@dataclass(frozen=True)
class BatchConfig:
    dataset: str | Path
    environments: str | Path
    cache: str | Path
    references: str | Path
    output: str | Path
    workers: int = 4
    max_rounds: int = 6
    max_trials: int = 64
    max_sites: int = 6
    max_sweeps: int = 2
    min_gain: float = 0.05
    methods: tuple[str, ...] = METHODS


def _now():
    return datetime.now(timezone.utc).isoformat()


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _paths(config):
    return {
        key: Path(getattr(config, key)).expanduser().resolve()
        for key in ("dataset", "environments", "cache", "references", "output")
    }


def _validate(config):
    for key in ("workers", "max_rounds", "max_trials", "max_sites", "max_sweeps"):
        value = getattr(config, key)
        if type(value) is not int or value < (0 if key == "max_sweeps" else 1):
            raise ValueError(f"Invalid {key}: {value}")
    if not math.isfinite(config.min_gain) or not 0 <= config.min_gain < 100:
        raise ValueError("min_gain must be finite and in [0, 100)")
    if (
        not config.methods
        or len(set(config.methods)) != len(config.methods)
        or set(config.methods) - set(METHODS)
    ):
        raise ValueError("Select nonempty, unique, supported methods")


def _preflight(evaluator, paths):
    """Verify the exported denominators against the live cache, without compiling."""
    rows = [
        json.loads(line)
        for line in paths["references"].read_text().splitlines()
        if line.strip()
    ]
    names = evaluator.dataset.names
    if len(rows) != len(names) or {row["name"] for row in rows} != set(names):
        raise ValueError("Reference export must contain exactly the selected dataset")
    expected = {row["name"]: row for row in rows}
    dataset_sha = digest(paths["dataset"])
    contexts = {}
    for name in names:
        row, exported = evaluator.dataset.get(name), expected[name]
        versions = {version for item in row["version_info"] for version in item}
        proof_sha = hashlib.sha256(row["src"].encode()).hexdigest()
        if (
            exported["dataset_sha256"] != dataset_sha
            or exported["status"] != "prepared"
            or exported["reference_code_sha256"] != proof_sha
            or exported["reference_length_tokens"] != row["proof_length"]
            or set(exported["per_version"]) != versions
        ):
            raise ValueError(f"Mismatched or incomplete reference export for {name}")
        cached = evaluator.get_reference(name)["versions"]
        contexts[name] = {}
        for version in sorted(versions):
            reference, value = exported["per_version"][version], cached[version]
            if reference["status"] != "prepared" or value.get("status") != "prepared":
                raise ValueError(
                    f"Cached reference unavailable for {name}/{version}; prepare separately"
                )
            if (
                not isinstance(value.get("heartbeats"), (int, float))
                or not math.isfinite(value["heartbeats"])
                or value["heartbeats"] <= 0
            ):
                raise ValueError(
                    f"Nonpositive or invalid reference heartbeats for {name}/{version}"
                )
            for key in ("heartbeats", "heartbeats_raw"):
                if reference[key] != value[key]:
                    raise ValueError(
                        f"Reference export/cache mismatch for {name}/{version}: {key}"
                    )
            for key in (
                "measured_at",
                "environment_fingerprint",
                "reference_code_sha256",
                "machine",
                "details",
            ):
                if reference["provenance"][key] != value[key]:
                    raise ValueError(
                        f"Reference export/cache mismatch for {name}/{version}: {key}"
                    )
            contexts[name][version] = evaluator._context(row, version)[2]
    return contexts


def _run_stage(command):
    return subprocess.run(command, cwd=REPOSITORY, stdout=sys.stderr).returncode


def run_batch(config: BatchConfig) -> dict:
    """Run/resume a batch and return its manifest; never set up or refresh references.

    A finished manifest names submission.jsonl. Incomplete discovery returns an
    unavailable manifest; configuration, process and audit errors raise. The last
    completed stage and every candidate checkpoint survive interruption.
    """
    _validate(config)
    paths = _paths(config)
    output = paths["output"]
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".batch.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another process owns this batch output") from exc
        manifest_path = output / "batch.json"
        old = _read(manifest_path) if manifest_path.exists() else None
        # Do not reuse an experiment archive or an unrelated populated folder.
        if old is None and any(p.name != ".batch.lock" for p in output.iterdir()):
            raise ValueError("Batch output is not empty; choose a new folder")
        evaluator = Evaluator(paths["dataset"], paths["environments"], paths["cache"])
        contexts = _preflight(evaluator, paths)
        identity = {
            "schema_version": 1,
            "paths": {key: str(value) for key, value in paths.items()},
            "dataset_sha256": digest(paths["dataset"]),
            "environments_sha256": digest(paths["environments"]),
            "references_sha256": digest(paths["references"]),
            "contexts": contexts,
            "methods": list(config.methods),
            "workers": config.workers,
            "max_sweeps": config.max_sweeps,
            "budget": {
                "rounds": config.max_rounds,
                "trials": config.max_trials,
                "sites": config.max_sites,
                "min_gain": config.min_gain,
            },
            "code_sha256": {
                str(p.relative_to(REPOSITORY)): digest(p)
                for p in sorted((REPOSITORY / "src").rglob("*.py"))
            },
        }
        if old is not None and old["config"] != identity:
            raise ValueError(
                "Batch code, inputs, environments or budgets changed; choose a new folder"
            )
        manifest = {
            "schema_version": 1,
            "config": identity,
            "status": "running",
            "started_at": old["started_at"] if old else _now(),
            "stages": [],
            "sweeps": [],
        }
        write_json(manifest_path, manifest)
        stages, previous, candidates = [], None, None

        def stage(folder, method):
            nonlocal previous, candidates
            destination = output / folder
            manifest["active_stage"] = str(destination)
            write_json(manifest_path, manifest)
            command = [
                sys.executable,
                "-m",
                "proof_eval.optimization.runner",
                "--method",
                method,
                "--output",
                str(destination),
                "--dataset",
                str(paths["dataset"]),
                "--environments",
                str(paths["environments"]),
                "--cache",
                str(paths["cache"]),
                "--workers",
                str(config.workers),
                "--max-rounds",
                str(config.max_rounds),
                "--max-trials",
                str(config.max_trials),
                "--max-sites",
                str(config.max_sites),
                "--min-gain",
                str(config.min_gain),
            ]
            if candidates is not None:
                command.extend(["--input", str(candidates)])
            # The stage runner checks its exact configuration and resumes its
            # checkpoints, including completed results, before returning.
            returncode = _run_stage(command)
            if returncode == 2:
                manifest.update(status="unavailable", stop_reason="stage_unavailable")
                return None
            if returncode != 0:
                raise RuntimeError(f"Stage {method} exited with code {returncode}")
            summary = _read(destination / "summary.json")
            if summary["full_benchmark_combined_pct"] is None:
                raise ValueError(f"Incomplete benchmark coverage in {destination}")
            write_stage_report(
                destination,
                previous,
                dataset=paths["dataset"],
                baseline=stages[0] if stages else destination,
            )
            stages.append(destination)
            previous, candidates = destination, destination / "candidates.jsonl"
            manifest["stages"].append(
                {
                    "path": str(destination),
                    "method": method,
                    "combined_pct": summary["full_benchmark_combined_pct"],
                    "delta_pp": summary["full_benchmark_delta_pp"],
                }
            )
            manifest["selected_stage_candidates"] = str(candidates)
            write_json(manifest_path, manifest)
            return summary

        try:
            for method in config.methods:
                if stage(FOLDERS[method], method) is None:
                    return manifest
            repeat = tuple(method for method in REPEAT if method in config.methods)
            for sweep in range(1, config.max_sweeps + 1):
                changes, delta = 0, 0.0
                for index, method in enumerate(repeat, 1):
                    summary = stage(
                        f"11_repeated_sweeps/sweep_{sweep:02d}/{index:02d}_{method}",
                        method,
                    )
                    if summary is None:
                        return manifest
                    changes += summary["changed_problems"]
                    delta += summary["full_benchmark_delta_pp"]
                manifest["sweeps"].append(
                    {
                        "sweep": sweep,
                        "delta_pp": delta,
                        "changed_problem_stages": changes,
                    }
                )
                if changes == 0:
                    manifest["stop_reason"] = (
                        "no_improvement_in_bounded_portfolio_sweep"
                    )
                    break
            else:
                manifest["stop_reason"] = "sweep_limit"
            audited = audit(
                stages,
                dataset=paths["dataset"],
                references=paths["references"],
                check_code=True,
                check_cache=True,
                cache=paths["cache"],
                code_root=REPOSITORY,
            )
            write_json(output / "audit.json", audited)
            comparison = write_comparison(
                stages, output_root=output, dataset=paths["dataset"], baseline=stages[0]
            )
            selected = candidates.read_bytes()
            temporary = output / "submission.jsonl.tmp"
            temporary.write_bytes(selected)
            temporary.replace(output / "submission.jsonl")
            manifest.update(
                status="finished",
                submission=str(output / "submission.jsonl"),
                submission_sha256=hashlib.sha256(selected).hexdigest(),
                problem_count=len(evaluator.dataset.names),
                passed_version_checks=audited["stages"][-1]["passed_version_checks"],
                expected_version_checks=audited["stages"][-1][
                    "expected_version_checks"
                ],
                scores=comparison["stages"][-1]["full_benchmark_final_mean"],
            )
            manifest.pop("active_stage", None)
            return manifest
        except BaseException as exc:
            manifest.update(status="interrupted", error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            manifest["updated_at"] = _now()
            write_json(manifest_path, manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dataset", "environments", "cache", "references", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name, default in (
        ("workers", 4),
        ("max-rounds", 6),
        ("max-trials", 64),
        ("max-sites", 6),
        ("max-sweeps", 2),
    ):
        parser.add_argument("--" + name, type=int, default=default)
    parser.add_argument("--min-gain", type=float, default=0.05)
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    args = vars(parser.parse_args(argv))
    args["methods"] = tuple(args["methods"])
    try:
        result = run_batch(BatchConfig(**args))
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["status"] == "finished" else 2


if __name__ == "__main__":
    raise SystemExit(main())
