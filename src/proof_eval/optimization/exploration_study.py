"""Compare full deterministic searches on a frozen development cohort."""

from __future__ import annotations

import argparse
import fcntl
import json
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

from .exploration import explore
from .exploration_reporting import audit_cell, report_exploration
from .exploration_reuse import freeze_completed, reused_records
from .search_graph import SearchPlan, plans


def _cell(request_path: Path) -> None:
    request = read(request_path)
    config, folder = read(request["config"]), request_path.parent
    _verify(config)
    pack = request["pack"]
    if fingerprint(pack) != config["input_sha256"][pack["name"]]:
        raise ValueError("Search input changed")
    evaluator = Evaluator(
        config["dataset"], config["environments"], folder / "evaluation_cache"
    )
    local = private_evaluator(evaluator, folder, pack)
    proof, evaluation = measure_original(local, folder, pack, timeout_retries=1)
    result = explore(
        evaluator=local,
        row=pack["row"],
        proof=proof,
        evaluation=evaluation,
        folder=folder / "search",
        plan=SearchPlan.from_record(config["conditions"][request["condition"]]),
        provenance={
            "study_sha256": fingerprint(config),
            "input_sha256": fingerprint(pack),
        },
    )
    write_json(
        folder / "result.json",
        {
            **result,
            "condition": request["condition"],
            "elapsed_seconds": time.time() - read(folder / "started.json")["epoch"],
            "search_sha256": digest(folder / "search/result.json"),
            "measurement_sha256": digest(folder / "initial_measurement.json"),
        },
    )
    reference = next(
        r
        for r in map(json.loads, Path(config["references"]).read_text().splitlines())
        if r["name"] == pack["name"]
    )
    write_json(folder / "audit.json", audit_cell(folder, pack["row"], reference))


def _verify(config: dict) -> None:
    for condition in config["conditions"]:
        reused_records(config, condition)
    for key in ("dataset", "environments", "references"):
        if digest(config[key]) != config[key + "_sha256"]:
            raise ValueError("Frozen search input changed: " + key)
    for relative, expected in config["code_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("Frozen search code changed: " + relative)


def run_exploration_study(
    *,
    output: Path,
    base: Path,
    dataset: Path,
    environments: Path,
    cache: Path,
    references: Path,
    workers: int = 4,
    prepare_only: bool = False,
    reuse_completed_from: Path | None = None,
) -> dict:
    """Queue all cells directly, isolating every cache and continuing after failures."""
    if type(workers) is not int or workers < 1:
        raise ValueError("Positive worker count required")
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        packs, base_config = load_inputs(base), read(base / "config.json")
        evaluator = Evaluator(dataset, environments, cache)
        for pack in packs.values():
            check_references(evaluator, pack, base_config)
        config = {
            "schema_version": 1,
            "names": base_config["names"],
            "workers": workers,
            **{
                key: str(value.resolve())
                for key, value in {
                    "base": base,
                    "dataset": dataset,
                    "environments": environments,
                    "references": references,
                }.items()
            },
            **{
                key + "_sha256": digest(value)
                for key, value in {
                    "dataset": dataset,
                    "environments": environments,
                    "references": references,
                }.items()
            },
            "input_sha256": {name: fingerprint(pack) for name, pack in packs.items()},
            "code_sha256": {
                str(p.relative_to(ROOT)): digest(p)
                for p in sorted((ROOT / "src/proof_eval").rglob("*.py"))
            },
            "conditions": {key: value.record() for key, value in plans().items()},
            "overall_wall_seconds": None,
            "initial_measurement_timeout_retries": 1,
            "scope": "Warm-up development search; five globally fixed policies, fresh original proofs and private per-cell caches. No overall wall cap and no model calls. Finite work bounds and existing individual Lean/discovery watchdogs apply. Scores use canonical denominators. No held-out or global-optimality claim.",
        }
        if reuse_completed_from is not None:
            config["recovery_sources"] = freeze_completed(
                reuse_completed_from, config, packs
            )
            config[
                "scope"
            ] += " Explicit recovery: completed source cells are retained unchanged; failed or missing cells rerun from original proofs under the pinned repaired runtime. Aggregate timings combine source and recovery runs."
        path = output / "config.json"
        if path.exists() and read(path) != config:
            raise ValueError("Frozen search study changed")
        write_json(path, config)
        _verify(config)
        write_json(
            output / "preflight.json",
            {
                "status": "passed",
                "at": now(),
                "cached_references": len(packs),
                "compiler_calls": 0,
                "model_calls": 0,
                "config_sha256": digest(path),
            },
        )

        if prepare_only:
            report_exploration(output)
            return {
                "status": "prepared",
                "cells": len(packs) * len(config["conditions"]),
            }

        def run_cell(condition: str, name: str) -> None:
            if name in config.get("recovery_sources", {}).get("cells", {}).get(
                condition, {}
            ):
                return
            folder = output / "conditions" / condition / "cells" / fingerprint(name)
            folder.mkdir(parents=True, exist_ok=True)
            if (folder / "result.json").exists():
                reference = next(
                    r
                    for r in map(json.loads, references.read_text().splitlines())
                    if r["name"] == name
                )
                write_json(
                    folder / "audit.json",
                    audit_cell(folder, packs[name]["row"], reference),
                )
                return
            if (folder / "started.json").exists():
                raise RuntimeError("Started search cell is indeterminate; not replayed")
            write_json(
                folder / "started.json",
                {"epoch": time.time(), "name": name, "condition": condition},
            )
            request_path = folder / "request.json"
            write_json(
                request_path,
                {
                    "config": str(path.resolve()),
                    "pack": packs[name],
                    "condition": condition,
                },
            )
            try:
                with (folder / "worker.log").open("ab") as log:
                    subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "proof_eval.optimization.exploration_study",
                            "--cell-request",
                            str(request_path.resolve()),
                        ],
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        check=True,
                    )
            except Exception as exc:
                write_json(
                    folder / "failure.json",
                    {"at": now(), "error": f"{type(exc).__name__}: {exc}"},
                )
                raise

        write_json(output / "run.json", {"status": "running", "at": now()})
        report_exploration(output)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            # All 75 cells are admitted; ordering yields a complete control cohort first.
            futures = [
                pool.submit(run_cell, condition, name)
                for condition in config["conditions"]
                for name in config["names"]
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    with (output / "failures.jsonl").open("a") as stream:
                        stream.write(
                            json.dumps({"at": now(), "error": str(exc)}) + "\n"
                        )
                report_exploration(output)
        _verify(config)
        if reuse_completed_from is not None:
            if (
                freeze_completed(reuse_completed_from, config, packs)
                != config["recovery_sources"]
            ):
                raise ValueError("Recovery evidence changed during execution")
        report = report_exploration(output)
        write_json(output / "run.json", {"status": report["status"], "at": now()})
        return report


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 2 and argv[0] == "--cell-request":
        _cell(Path(argv[1]))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("output", "base", "dataset", "environments", "cache", "references"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--reuse-completed-from", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--preflight", dest="prepare_only", action="store_true")
    return (
        0
        if run_exploration_study(**vars(parser.parse_args(argv)))["status"]
        in {"complete", "prepared"}
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
