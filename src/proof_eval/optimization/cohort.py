"""Independent cohort-wide one-sweep cleanup before or after model search."""

from __future__ import annotations

import fcntl
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import mean

from proof_eval.evidence.audit import _evaluation, _implementation, _require
from proof_eval.evidence.io import digest, fingerprint, now, read, sha, write_json
from proof_eval.evidence.proof_states import (
    export_proof_states,
    freeze_proof_states,
    guard_proof_states,
)
from proof_eval.harness.configuration import load_inputs
from proof_eval.paths import ROOT, SNAPSHOTS
from proof_eval.verification.api import Evaluator
from proof_eval.verification.initial import (
    audit_measurement_attempts,
    measure_original,
    private_evaluator,
)
from proof_eval.verification.references import check_references, require_valid, score

from .exploration import explore, terminal_status, verify_manifest
from .search_graph import plans
from .supervision import interruption_signals, run_owned_worker


def _references(path: Path) -> dict:
    return {
        row["name"]: row
        for row in (
            json.loads(line) for line in path.read_text().splitlines() if line.strip()
        )
    }


def _cleanup_lineage(selected: dict) -> dict:
    lineage = selected["lineage"]
    return {
        **lineage,
        "origin_kind": lineage.get("origin_kind", lineage["kind"]),
        "kind": "deterministic",
    }


def _verify(config: dict, packs: dict) -> None:
    for key in ("dataset", "environments", "references"):
        if digest(config[key]) != config[key + "_sha256"]:
            raise ValueError("Frozen cleanup input changed: " + key)
    if {name: fingerprint(pack) for name, pack in packs.items()} != config[
        "input_sha256"
    ]:
        raise ValueError("Frozen cleanup packs changed")
    for relative, expected in config["code_sha256"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError("Frozen cleanup runtime changed: " + relative)
    guard_proof_states(
        config["starting_proofs"],
        packs,
        Path(config["references"]),
        condition=tuple(config["condition"]) if config["condition"] else None,
    )


def _cell(request_path: Path) -> None:
    request, folder = read(request_path), request_path.parent
    config = read(request["config"])
    packs = read(Path(request["config"]).parent / "packs.json")
    _verify(config, packs)
    pack = packs[request["name"]]
    evaluator = Evaluator(config["dataset"], config["environments"], folder / "cache")
    local = private_evaluator(evaluator, folder, pack)
    proof, evaluation = measure_original(local, folder, pack, timeout_retries=1)
    selected = config["starting_proofs"]["cells"][pack["name"]]
    started = time.time()
    write_json(folder / "seed_started.json", {"epoch": started})
    if selected["proof"] != proof:
        proof = selected["proof"]
        evaluation = local.evaluate(pack["name"], proof, versions="all")
        require_valid(evaluation, pack["row"], proof)
        if any(
            v.get("cached") is not False for v in evaluation["per_version"].values()
        ):
            raise ValueError("Cleanup starting proof reused a candidate cache")
    if score(evaluation) + 0.05 < score(
        read(folder / "initial_measurement.json")["evaluation"]
    ):
        raise ValueError("Cleanup starting proof regresses below the measured original")
    write_json(
        folder / "seed.json",
        {
            "proof": proof,
            "evaluation": evaluation,
            "started_epoch": started,
            "finished_epoch": time.time(),
            "state_sha256": fingerprint(selected),
        },
    )
    result = explore(
        evaluator=local,
        row=pack["row"],
        proof=proof,
        evaluation=evaluation,
        folder=folder / "search",
        plan=plans()["one_sweep"],
        provenance={
            "config_sha256": fingerprint(config),
            "seed_sha256": digest(folder / "seed.json"),
        },
    )
    write_json(
        folder / "result.json",
        {
            **result,
            "lineage": _cleanup_lineage(selected),
            "input_score": score(evaluation),
            "elapsed_seconds": time.time() - read(folder / "started.json")["epoch"],
            "search_sha256": digest(folder / "search/result.json"),
            "measurement_sha256": digest(folder / "initial_measurement.json"),
            "seed_sha256": digest(folder / "seed.json"),
        },
    )
    write_json(
        folder / "audit.json",
        audit_cleanup_cell(
            folder,
            pack["row"],
            _references(Path(config["references"]))[pack["name"]],
            selected,
        ),
    )


def audit_cleanup_cell(
    folder: Path, row: dict, reference: dict, selected: dict
) -> dict:
    """Audit arbitrary verified starting states without weakening historical audits."""
    result, seed = read(folder / "result.json"), read(folder / "seed.json")
    search = folder / "search"
    sealed, spec = read(search / "result.json"), read(search / "spec.json")
    verify_manifest(search, sealed)
    _require(
        all(result.get(k) == v for k, v in sealed.items() if k != "elapsed_seconds")
        and sealed["name"] == row["name"]
        and result["search_sha256"] == digest(search / "result.json")
        and result["seed_sha256"] == digest(folder / "seed.json")
        and result["measurement_sha256"] == digest(folder / "initial_measurement.json")
        and result["lineage"] == _cleanup_lineage(selected)
        and seed["proof"] == selected["proof"]
        and seed["state_sha256"] == fingerprint(selected),
        "Cleanup starting state or sealed result changed",
    )
    audit_measurement_attempts(folder, row, 1)
    original = read(folder / "initial_measurement.json")
    require_valid(original["evaluation"], row, row["src"])
    started = read(folder / "started.json")["epoch"]
    progress = read(search / "progress.json")
    _require(
        started
        <= original["started_epoch"]
        <= original["finished_epoch"]
        <= seed["started_epoch"]
        <= seed["finished_epoch"]
        <= progress["started_epoch"]
        and seed["started_epoch"] == read(folder / "seed_started.json")["epoch"]
        and spec["plan"] == plans()["one_sweep"].record()
        and sealed["spec_sha256"] == digest(search / "spec.json")
        and spec["row_sha256"] == fingerprint(row)
        and spec["initial"] == sha(seed["proof"])
        and all(
            v.get("cached") is False for v in seed["evaluation"]["per_version"].values()
        ),
        "Cleanup measurement boundary or one-sweep plan changed",
    )
    outcomes = _evaluation(
        row, reference, row["src"], original["evaluation"], "original"
    )
    outcomes += _evaluation(
        row, reference, seed["proof"], seed["evaluation"], "cleanup seed"
    )
    require_valid(seed["evaluation"], row, seed["proof"])
    _require(
        score(seed["evaluation"]) + 0.05 >= score(original["evaluation"]),
        "Regressive cleanup seed",
    )
    nodes = {p.stem: read(p) for p in (search / "nodes").glob("*.json")}
    first = sha(seed["proof"])
    _require(
        nodes[first]["evaluation"] == seed["evaluation"]
        and nodes[first]["parent"] is None,
        "Cleanup root changed",
    )
    for key, node in nodes.items():
        _require(sha(node["proof"]) == key, "Cleanup node identity changed")
        require_valid(node["evaluation"], row, node["proof"])
        outcomes += _evaluation(
            row, reference, node["proof"], node["evaluation"], "cleanup node"
        )
        if key != first:
            _require(
                node["parent"] in nodes
                and node["method"] in spec["plan"]["methods"]
                and score(node["evaluation"])
                > score(nodes[node["parent"]]["evaluation"]) + 0.05,
                "Invalid cleanup improvement edge",
            )
    best, prior, elapsed = first, score(seed["evaluation"]), 0
    for item in progress["improvements"]:
        best = item["node"]
        value = score(nodes[best]["evaluation"])
        _require(
            value == item["score"]
            and value > prior + 0.05
            and item["elapsed_seconds"] >= elapsed,
            "Invalid cleanup best-proof trace",
        )
        prior, elapsed = value, item["elapsed_seconds"]
    _require(
        progress["best"] == sealed["best"] == best
        and sealed["proof"] == nodes[best]["proof"]
        and sealed["evaluation"] == nodes[best]["evaluation"]
        and result["input_score"] == score(seed["evaluation"])
        and abs(sealed["gain_pp"] - (prior - score(seed["evaluation"]))) < 1e-9,
        "Cleanup selected proof or gain changed",
    )
    statuses, counters, certified = [], {key: 0 for key in sealed["counters"]}, {first}
    scheduled_parent = first
    for index, key in enumerate(progress["expansions"]):
        expansion = search / "expansions" / key
        record, optimizer = read(expansion / "result.json"), read(
            expansion / "optimizer.json"
        )
        for relative, expected in record["evidence_sha256"].items():
            _require(
                digest(expansion / relative) == expected, "Cleanup expansion changed"
            )
        events = [
            json.loads(line)
            for line in (expansion / "trials.jsonl").read_text().splitlines()
        ]
        parent = record["identity"]["parent"]
        _require(
            record["status"] == terminal_status(optimizer, events[-1] if events else {})
            and parent == scheduled_parent
            and index < len(spec["plan"]["methods"])
            and record["identity"]["method"] == spec["plan"]["methods"][index]
            and key == fingerprint(record["identity"])
            and record["identity"]["plan"] == spec["plan"],
            "Cleanup expansion status or input changed",
        )
        candidates = {
            sha(e["proof"])
            for e in events
            if e.get("kind") == "candidate" and e.get("all_versions_requested")
        }
        _require(
            set(record["children"]) <= candidates
            and sha(optimizer["proof"]) == record["best"]
            and record["best"] in nodes,
            "Unrecorded cleanup child",
        )
        certified.update(record["children"])
        scheduled_parent = record["best"]
        statuses.append(record["status"])
        for counter in counters:
            _require(
                record["counters"][counter] == optimizer.get(counter, 0),
                "Cleanup counter changed",
            )
            counters[counter] += record["counters"][counter]
    _require(
        set(nodes) == certified
        and len(statuses) == sealed["expansions"] == len(spec["plan"]["methods"])
        and sealed["sweeps"] == 1
        and sealed["stop"] in {"one_sweep", "no_change_sweep"}
        and scheduled_parent == best
        and sealed["status"]
        == ("incomplete" if "incomplete" in statuses else "complete")
        and all(
            abs(sealed["counters"][key] - value) < 1e-9
            for key, value in counters.items()
        ),
        "Cleanup completeness or accounting changed",
    )
    return {
        "status": "passed",
        "nodes": len(nodes),
        "checked_version_outcomes": outcomes,
    }


def report_cleanup(output: Path) -> dict:
    """Read-only progress summary; publish cohort means only for audited completion."""
    output = Path(output)
    config = read(output / "config.json")
    packs, references = read(output / "packs.json"), _references(
        Path(config["references"])
    )
    records, failures, failed_seconds, active = [], [], 0.0, 0
    for name in config["names"]:
        folder = output / "cells" / fingerprint(name)
        if (folder / "result.json").exists():
            try:
                audit_cleanup_cell(
                    folder,
                    packs[name]["row"],
                    references[name],
                    config["starting_proofs"]["cells"][name],
                )
                records.append(read(folder / "result.json"))
            except Exception as exc:
                failures.append({"name": name, "error": str(exc)})
        elif (folder / "failure.json").exists():
            failure = read(folder / "failure.json")
            failures.append({"name": name, **failure})
            failed_seconds += failure.get("elapsed_seconds", 0.0)
        elif (folder / "started.json").exists():
            active += 1
    complete = len(records) == len(config["names"]) and all(
        r["status"] == "complete" for r in records
    )
    run = read(output / "run.json") if (output / "run.json").exists() else {}
    finish = run.get("finished_epoch", time.time())
    return {
        "status": "complete" if complete else "incomplete",
        "expected": len(config["names"]),
        "completed": sum(r["status"] == "complete" for r in records),
        "terminal": len(records),
        "active": active,
        "failures": failures,
        "workers": config["workers"],
        "mean_input_score": (
            mean(r["input_score"] for r in records) if complete else None
        ),
        "mean_output_score": (
            mean(score(r["evaluation"]) for r in records) if complete else None
        ),
        "mean_gain_pp": mean(r["gain_pp"] for r in records) if complete else None,
        "elapsed_seconds": max(0, finish - run["started_epoch"]) if run else 0,
        "sum_cell_seconds": sum(r["elapsed_seconds"] for r in records) + failed_seconds,
        "state": str((output / "state.json").resolve()) if complete else None,
    }


def audit_cleanup(output: Path) -> dict:
    """Validate the frozen cohort, each cell, and its portable selected-state export."""
    output = Path(output)
    config, packs = read(output / "config.json"), read(output / "packs.json")
    _require(
        config["cohort_cleanup_version"] == 1
        and config["plan"] == plans()["one_sweep"].record()
        and config["overall_wall_seconds"] is None
        and len(config["names"]) == len(packs)
        and set(config["names"]) == set(packs)
        and type(config["workers"]) is int
        and config["workers"] > 0,
        "Cleanup cohort policy changed",
    )
    for relative, expected in config["code_sha256"].items():
        _implementation(relative, expected, ROOT, SNAPSHOTS, "cleanup cohort")
    for key in ("dataset", "environments", "references"):
        _require(
            digest(config[key]) == config[key + "_sha256"], "Cleanup input changed"
        )
    _require(
        config["input_sha256"] == {n: fingerprint(p) for n, p in packs.items()},
        "Cleanup packs changed",
    )
    guard_proof_states(
        config["starting_proofs"],
        packs,
        Path(config["references"]),
        condition=tuple(config["condition"]) if config["condition"] else None,
    )
    report = report_cleanup(output)
    _require(report["status"] == "complete", "Cleanup cohort is incomplete")
    exported = freeze_proof_states(
        output / "state.json", packs, Path(config["references"])
    )
    for name in config["names"]:
        result = read(output / "cells" / fingerprint(name) / "result.json")
        _require(
            exported["cells"][name]["proof"] == result["proof"]
            and exported["cells"][name]["lineage"] == result["lineage"],
            "Cleanup state export changed",
        )
    return {
        "status": "passed",
        "cells": len(config["names"]),
        "config_sha256": digest(output / "config.json"),
    }


def run_cleanup(
    *,
    output: Path,
    base: Path,
    dataset: Path,
    environments: Path,
    cache: Path,
    references: Path,
    workers: int = 8,
    starting_proofs: Path | None = None,
    condition: tuple[str, str] | None = None,
    prepare_only: bool = False,
) -> dict:
    """Run one sweep per theorem with separate processes and private caches.

    Complete cells are audited and reused. Any started cell without a terminal
    result stays incomplete; it is never replayed automatically. Other cells keep
    running. Only a complete audited cohort produces a reusable state.json.
    """
    if type(workers) is not int or workers < 1:
        raise ValueError("Cleanup workers must be a positive integer")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        packs, base_config = load_inputs(Path(base)), read(Path(base) / "config.json")
        evaluator = Evaluator(dataset, environments, cache)
        for pack in packs.values():
            check_references(evaluator, pack, base_config)
        config = {
            "cohort_cleanup_version": 1,
            "names": list(packs),
            "workers": workers,
            "condition": list(condition) if condition else None,
            "plan": plans()["one_sweep"].record(),
            "overall_wall_seconds": None,
            "starting_proofs": freeze_proof_states(
                starting_proofs, packs, Path(references), condition=condition
            ),
            "input_sha256": {name: fingerprint(pack) for name, pack in packs.items()},
            "code_sha256": {
                str(p.relative_to(ROOT)): digest(p)
                for p in sorted((ROOT / "src/proof_eval").rglob("*.py"))
            },
        }
        for key, value in {
            "dataset": dataset,
            "environments": environments,
            "references": references,
        }.items():
            config[key], config[key + "_sha256"] = str(Path(value).resolve()), digest(
                value
            )
        path = output / "config.json"
        if path.exists():
            if read(path) != config:
                raise ValueError(
                    "Frozen cleanup configuration changed; use a new output"
                )
        elif any(p.name != ".lock" for p in output.iterdir()):
            raise ValueError("Cleanup output is not empty; use a new output")
        packs_path = output / "packs.json"
        if packs_path.exists() and read(packs_path) != packs:
            raise ValueError("Frozen cleanup packs changed")
        write_json(path, config)
        write_json(packs_path, packs)
        _verify(config, packs)
        if prepare_only:
            return {"status": "prepared", "expected": len(packs), "workers": workers}
        previous = read(output / "run.json") if (output / "run.json").exists() else {}
        if previous.get("status") == "complete":
            audit_cleanup(output)
            return report_cleanup(output)
        started = previous.get("started_epoch", time.time())
        write_json(
            output / "run.json",
            {"status": "running", "started_epoch": started, "at": now()},
        )

        cancellation = threading.Event()

        def run_one(name: str) -> None:
            if cancellation.is_set():
                raise RuntimeError("Cleanup cancelled before theorem admission")
            folder = output / "cells" / fingerprint(name)
            folder.mkdir(parents=True, exist_ok=True)
            if (folder / "result.json").exists():
                audit_cleanup_cell(
                    folder,
                    packs[name]["row"],
                    _references(Path(references))[name],
                    config["starting_proofs"]["cells"][name],
                )
                return
            if (folder / "started.json").exists():
                raise RuntimeError(
                    "Started cleanup cell is indeterminate or failed; not replayed"
                )
            write_json(folder / "started.json", {"epoch": time.time(), "name": name})
            request = folder / "request.json"
            write_json(request, {"config": str(path), "name": name})
            try:
                run_owned_worker(
                    [
                        sys.executable,
                        "-m",
                        "proof_eval.optimization.cohort",
                        str(request),
                    ],
                    folder=folder,
                    lock_fd=lock.fileno(),
                    cancellation=cancellation,
                )
            except Exception as exc:
                write_json(
                    folder / "failure.json",
                    {
                        "at": now(),
                        "error": f"{type(exc).__name__}: {exc}",
                        "elapsed_seconds": time.time()
                        - read(folder / "started.json")["epoch"],
                    },
                )
                raise

        failures, interrupted = [], None
        pool = ThreadPoolExecutor(max_workers=workers)
        futures = {}
        try:
            with interruption_signals():
                futures = {pool.submit(run_one, name): name for name in packs}
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as exc:
                        failures.append(
                            {
                                "name": futures[future],
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                        )
        except BaseException as error:
            interrupted = error
            cancellation.set()
            for future in futures:
                future.cancel()
            raise
        finally:
            pool.shutdown(wait=True, cancel_futures=cancellation.is_set())
            if interrupted is not None:
                write_json(
                    output / "run.json",
                    {
                        "status": "incomplete",
                        "started_epoch": started,
                        "finished_epoch": time.time(),
                        "error": f"{type(interrupted).__name__}: {interrupted}",
                        "failures": failures,
                        "at": now(),
                    },
                )
        _verify(config, packs)
        report = report_cleanup(output)
        write_json(
            output / "run.json",
            {
                "status": report["status"],
                "started_epoch": started,
                "finished_epoch": time.time(),
                "failures": failures,
                "at": now(),
            },
        )
        if report["status"] == "complete":
            records = {
                name: read(output / "cells" / fingerprint(name) / "result.json")
                for name in packs
            }
            export_proof_states(output / "state.json", packs, Path(references), records)
            write_json(output / "audit.json", audit_cleanup(output))
        report = report_cleanup(output)
        write_json(output / "report.json", report)
        return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Internal cleanup worker requires one request path")
    from proof_eval.providers.processes import enable_subreaper

    enable_subreaper()
    _cell(Path(sys.argv[1]))
