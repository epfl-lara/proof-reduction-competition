"""Compare frozen initial-transform portfolios with fresh per-cell measurements."""

from __future__ import annotations

import argparse
import fcntl
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, now, read, write_json
from proof_eval.harness.configuration import load_inputs
from proof_eval.paths import ROOT
from proof_eval.verification.api import Evaluator
from proof_eval.verification.initial import measure_original, private_evaluator
from proof_eval.verification.references import check_references

from .bounded import ALL_METHODS, run_bounded, validate_methods
from .cleanup import METHODS, PROOF_THEORY_METHODS
from .study_reporting import audit_study, report_study


def portfolios() -> dict[str, tuple[str, ...]]:
    """Predeclared single-method screens and combinations, without theorem tuning."""
    return {
        **{"single_" + method: (method,) for method in ALL_METHODS},
        "old_ten": METHODS,
        "new_six": PROOF_THEORY_METHODS,
        "all_old_first": ALL_METHODS,
        "all_new_first": PROOF_THEORY_METHODS + METHODS,
        "cheap_first": (
            "golf",
            "wrappers",
            "reuse",
            "collapse",
            "consolidate",
            "proof_theory",
            "relax",
            "delete",
            "lint",
            "simp",
            "facts",
            "menu",
            "search",
            "simp_min",
            "arith_min",
            "rw_min",
        ),
        "historical_gain_first": (
            "simp",
            "menu",
            "facts",
            "search",
            "arith_min",
            "golf",
        ),
    }


def select_combinations(report: dict) -> dict[str, tuple[str, ...]]:
    """Choose top-four lists by gain and by gain/second, using complete screens."""
    singles = [report["conditions"]["single_" + method] for method in ALL_METHODS]
    if not all(row["complete"] for row in singles):
        return {}
    positive = [row for row in singles if row["mean_gain_pp"] > 0]
    by_gain = sorted(
        positive,
        key=lambda row: (
            -row["mean_gain_pp"],
            row["mean_optimization_seconds"],
            row["methods"][0],
        ),
    )
    by_rate = sorted(
        positive,
        key=lambda row: (
            -row["mean_gain_pp"] / max(1.0, row["mean_optimization_seconds"]),
            -row["mean_gain_pp"],
            row["methods"][0],
        ),
    )
    return {
        "selected_top4_gain": tuple(row["methods"][0] for row in by_gain[:4]),
        "selected_top4_rate": tuple(row["methods"][0] for row in by_rate[:4]),
    }


def _run_cell(request_path: Path) -> None:
    """Measure and transform in a fresh process, never fork a threaded evaluator."""
    request = read(request_path)
    folder = request_path.parent
    config = read(request["config"])
    for relative, expected in config["code_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("Pinned study code changed")
    pack, name = request["pack"], request["name"]
    if fingerprint(pack) != config["input_sha256"][name]:
        raise ValueError("Pinned study input changed")
    evaluator = Evaluator(
        config["dataset"], config["environments"], folder / "evaluation_cache"
    )
    local = private_evaluator(evaluator, folder, pack)
    proof, evaluation = measure_original(
        local,
        folder,
        pack,
        timeout_retries=config.get("initial_measurement_timeout_retries", 0),
    )
    phase = run_bounded(
        evaluator=local,
        row=pack["row"],
        proof=proof,
        evaluation=evaluation,
        folder=folder / "optimization",
        methods=tuple(request["methods"]),
        seconds=config["seconds"],
        provenance={
            "study_sha256": fingerprint(config),
            "input_sha256": config["input_sha256"][name],
        },
    )
    write_json(
        folder / "result.json",
        {
            "name": name,
            "condition": request["condition"],
            "status": phase["status"],
            "proof": phase["proof"],
            "evaluation": phase["evaluation"],
            "gain_pp": phase["gain_pp"],
            "optimization_seconds": phase["elapsed_seconds"],
            "elapsed_seconds": time.time()
            - read(folder / "started.json")["started_epoch"],
            "measurement_sha256": digest(folder / "initial_measurement.json"),
            "optimization_sha256": digest(folder / "optimization/result.json"),
        },
    )


def run_study(
    *,
    output: Path,
    base: Path,
    dataset: Path,
    environments: Path,
    cache: Path,
    references: Path,
    workers: int = 6,
    seconds: float = 300,
) -> dict:
    """Run the complete development cohort; failures never cancel queued cells."""
    validate_methods(ALL_METHODS, seconds)
    if type(workers) is not int or workers < 1:
        raise ValueError("workers must be positive")
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        packs, base_config = load_inputs(base), read(base / "config.json")
        evaluator = Evaluator(dataset, environments, cache)
        for pack in packs.values():
            check_references(evaluator, pack, base_config)
        config = {
            "schema_version": 2,
            "initial_measurement_timeout_retries": 1,
            "discovery_limit_policy": "retain_verified_proof_on_terminal_timeout",
            "names": base_config["names"],
            "workers": workers,
            "seconds": seconds,
            "base": str(base),
            "dataset": str(dataset),
            "environments": str(environments),
            "references": str(references),
            "dataset_sha256": digest(dataset),
            "environments_sha256": digest(environments),
            "references_sha256": digest(references),
            "input_sha256": {n: fingerprint(p) for n, p in packs.items()},
            "code_sha256": {
                str(p.relative_to(ROOT)): digest(p)
                for p in sorted((ROOT / "src/proof_eval").rglob("*.py"))
            },
            "conditions": {key: list(value) for key, value in portfolios().items()},
            "selection_rule": "After all 16 single-method full cohorts: positive methods, top four by mean gain and separately by gain/max(1,mean phase seconds); ties by gain, elapsed time, name. Each selected combination is tested afresh.",
            "scope": "Warm-up development selection; no held-out claim or model inference. Fresh original measurement, private candidate/analysis caches, 300-second maximum initial phase.",
        }
        path = output / "config.json"
        if path.exists() and read(path) != config:
            raise ValueError("Frozen transform study changed")
        write_json(path, config)

        def cell(condition: str, methods: tuple[str, ...], name: str) -> dict:
            folder = output / "conditions" / condition / "cells" / fingerprint(name)
            folder.mkdir(parents=True, exist_ok=True)
            if (folder / "result.json").exists():
                return read(folder / "result.json")
            if (folder / "started.json").exists():
                raise RuntimeError("Started study cell is indeterminate; not replayed")
            started = time.time()
            write_json(
                folder / "started.json",
                {
                    "at": now(),
                    "started_epoch": started,
                    "name": name,
                    "methods": list(methods),
                },
            )
            try:
                request_path = folder / "request.json"
                write_json(
                    request_path,
                    {
                        "config": str(path.resolve()),
                        "name": name,
                        "pack": packs[name],
                        "condition": condition,
                        "methods": list(methods),
                    },
                )
                with (folder / "worker.log").open("ab") as log:
                    subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "proof_eval.optimization.study",
                            "--cell-request",
                            str(request_path.resolve()),
                        ],
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        check=True,
                    )
                return read(folder / "result.json")
            except Exception as error:
                write_json(
                    folder / "failure.json",
                    {"at": now(), "error": f"{type(error).__name__}: {error}"},
                )
                raise

        def batch(conditions: dict[str, tuple[str, ...]]) -> None:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [
                    pool.submit(cell, condition, methods, name)
                    for condition, methods in conditions.items()
                    for name in config["names"]
                ]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        pass  # Each cell owns its durable failure; other work continues.
                    report_study(output)

        write_json(output / "run.json", {"status": "running", "at": now()})
        batch(portfolios())
        selected = select_combinations(report_study(output))
        selection_path = output / "selection.json"
        selection = {
            "methods": {key: list(value) for key, value in selected.items()},
            "screen_result_sha256": {
                str(p.relative_to(output)): digest(p)
                for p in sorted(
                    (output / "conditions").glob("single_*/cells/*/result.json")
                )
            },
        }
        if selection_path.exists() and read(selection_path) != selection:
            raise ValueError("Frozen combination selection changed")
        write_json(selection_path, selection)
        batch(selected)
        report = report_study(output)
        write_json(output / "audit.json", audit_study(output))
        write_json(output / "run.json", {"status": report["status"], "at": now()})
        return report


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 2 and argv[0] == "--cell-request":
        _run_cell(Path(argv[1]))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in (
        "output",
        "base",
        "dataset",
        "environments",
        "cache",
        "references",
    ):
        parser.add_argument("--" + argument, type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seconds", type=float, default=300)
    args = parser.parse_args(argv)
    report = run_study(**vars(args))
    return 0 if report["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
