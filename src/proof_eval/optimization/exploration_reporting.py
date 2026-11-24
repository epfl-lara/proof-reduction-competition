"""Audit and report a deterministic search study without dispatching computation."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from proof_eval.evidence.audit import _evaluation, _require
from proof_eval.evidence.io import digest, read, sha, write_json
from proof_eval.verification.initial import audit_measurement_attempts
from proof_eval.verification.references import require_valid, score

from .exploration import terminal_status, verify_manifest
from .exploration_reuse import reused_records


def audit_cell(folder: Path, row: dict, reference: dict) -> dict:
    """Check every branch certificate, lineage, selection, score and sealed log."""
    result = read(folder / "result.json")
    search = folder / "search"
    sealed = read(search / "result.json")
    verify_manifest(search, sealed)
    _require(
        all(
            result.get(key) == value
            for key, value in sealed.items()
            if key != "elapsed_seconds"
        ),
        "Cell summary disagrees with sealed search",
    )
    _require(
        result["search_sha256"] == digest(search / "result.json"), "Search changed"
    )
    _require(
        result["measurement_sha256"] == digest(folder / "initial_measurement.json"),
        "Original measurement changed",
    )
    audit_measurement_attempts(folder, row, 1)
    original = read(folder / "initial_measurement.json")
    nodes = {p.stem: read(p) for p in (search / "nodes").glob("*.json")}
    first = sha(row["src"])
    _require(
        nodes[first]["evaluation"] == original["evaluation"]
        and nodes[first]["proof"] == row["src"]
        and nodes[first]["parent"] is None,
        "Search seed changed",
    )
    progress = read(search / "progress.json")
    _require(
        progress["started_epoch"] >= original["finished_epoch"],
        "Unaccounted preprocessing",
    )
    spec = read(search / "spec.json")
    _require(
        digest(search / "spec.json") == sealed["spec_sha256"], "Search spec changed"
    )
    outcomes = 0
    for key, node in nodes.items():
        _require(sha(node["proof"]) == key, "Node identity changed")
        require_valid(node["evaluation"], row, node["proof"])
        outcomes += _evaluation(
            row, reference, node["proof"], node["evaluation"], "search node"
        )
        if key != first:
            _require(
                node["parent"] in nodes and node["method"] in spec["plan"]["methods"],
                "Unknown search parent/method",
            )
            _require(
                score(node["evaluation"])
                > score(nodes[node["parent"]]["evaluation"])
                + spec["plan"]["budget"]["min_gain"],
                "Non-improving search edge",
            )
    prior = score(nodes[first]["evaluation"])
    best = first
    elapsed = 0
    for item in progress["improvements"]:
        best = item["node"]
        value = score(nodes[best]["evaluation"])
        _require(
            value == item["score"]
            and value > prior + spec["plan"]["budget"]["min_gain"]
            and item["elapsed_seconds"] >= elapsed,
            "Invalid best-proof trace",
        )
        prior, elapsed = value, item["elapsed_seconds"]
    _require(
        progress["best"] == sealed["best"] == best
        and sealed["evaluation"] == nodes[best]["evaluation"]
        and sealed["proof"] == nodes[best]["proof"]
        and abs(sealed["gain_pp"] - (prior - score(original["evaluation"]))) < 1e-9,
        "Selected best proof changed",
    )
    statuses, counters = [], {key: 0 for key in sealed["counters"]}
    certified_children = {first}
    for key in progress["expansions"]:
        expansion = search / "expansions" / key
        record = read(expansion / "result.json")
        for relative, expected in record["evidence_sha256"].items():
            _require(digest(expansion / relative) == expected, "Expansion changed")
        events = [
            json.loads(line)
            for line in (expansion / "trials.jsonl").read_text().splitlines()
        ]
        optimizer = read(expansion / "optimizer.json")
        _require(
            record["status"]
            == terminal_status(optimizer, events[-1] if events else {}),
            "Discovery outcome changed",
        )
        parent = record["identity"]["parent"]
        _require(
            parent in nodes and record["identity"]["plan"] == spec["plan"],
            "Expansion input changed",
        )
        candidate_hashes = {
            sha(e["proof"])
            for e in events
            if e.get("kind") == "candidate" and e.get("all_versions_requested")
        }
        _require(
            set(record["children"]) <= candidate_hashes
            and sha(optimizer["proof"]) == record["best"]
            and record["best"] in nodes,
            "Unrecorded search child",
        )
        certified_children.update(record["children"])
        statuses.append(record["status"])
        for counter in counters:
            _require(
                record["counters"][counter] == optimizer.get(counter, 0),
                "Counter changed",
            )
            counters[counter] += record["counters"][counter]
    _require(set(nodes) == certified_children, "Unlinked search certificate")
    _require(
        sealed["status"] == ("incomplete" if "incomplete" in statuses else "complete")
        and sealed["expansions"] == len(statuses)
        and all(
            abs(sealed["counters"][key] - value) < 1e-9
            for key, value in counters.items()
        ),
        "Search completeness or accounting changed",
    )
    return {
        "status": "passed",
        "nodes": len(nodes),
        "checked_version_outcomes": outcomes,
    }


def report_exploration(output: Path) -> dict:
    """Expose progress immediately, but means only for a full audited cohort."""
    config = read(output / "config.json")
    conditions = {}
    for condition in config["conditions"]:
        folder = output / "conditions" / condition
        records = [read(p) for p in folder.glob("cells/*/result.json")]
        reused = reused_records(config, condition)
        records += reused
        audited = list(folder.glob("cells/*/audit.json"))
        complete = (
            len(records) == len(config["names"])
            and {r["name"] for r in records} == set(config["names"])
            and len(audited) + len(reused) == len(records)
            and all(read(p)["status"] == "passed" for p in audited)
            and all(r["status"] == "complete" for r in records)
        )
        conditions[condition] = {
            "complete": complete,
            "terminal": len(records),
            "expected": len(config["names"]),
            **({"reused_cells": len(reused)} if config.get("recovery_sources") else {}),
            "failures": len(list(folder.glob("cells/*/failure.json"))),
            "active": sum(
                not (p.parent / "result.json").exists()
                and not (p.parent / "failure.json").exists()
                for p in folder.glob("cells/*/started.json")
            ),
            "mean_gain_pp": mean(r["gain_pp"] for r in records) if complete else None,
            "mean_combined_pct": (
                mean(r["evaluation"]["scores"]["combined_pct"] for r in records)
                if complete
                else None
            ),
            "mean_seconds": (
                mean(r["elapsed_seconds"] for r in records) if complete else None
            ),
            "mean_lean_candidate_checks": (
                mean(r["counters"]["lean_candidate_checks"] for r in records)
                if complete
                else None
            ),
            "work_limited_expansions": sum(
                r["work_limited_expansions"] for r in records
            ),
            "discovery_limited_expansions": sum(
                r["discovery_limited_expansions"] for r in records
            ),
        }
    ranking = sorted(
        (name for name, row in conditions.items() if row["complete"]),
        key=lambda name: (
            -conditions[name]["mean_gain_pp"],
            conditions[name]["mean_seconds"],
            name,
        ),
    )
    result = {
        "status": (
            "complete"
            if all(c["complete"] for c in conditions.values())
            else "incomplete"
        ),
        "conditions": conditions,
        "ranking": ranking,
        "best_observed": ranking[0] if len(ranking) == len(conditions) else None,
        "scope": config["scope"],
    }
    write_json(output / "report.json", result)
    lines = [
        "# Deterministic search exploration",
        "",
        config["scope"],
        "",
        "Means require a full audited cohort. Work and discovery limits do not establish optimality.",
        "",
        "| Search | Terminal | Mean gain (pp) | Mean score (%) | Mean minutes | Mean candidate checks | Failures |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in conditions.items():

        def fmt(key, divisor=1):
            return f"{row[key] / divisor:.3f}" if row[key] is not None else "pending"

        lines.append(
            f"| {name} | {row['terminal']}/{row['expected']} | {fmt('mean_gain_pp')} | {fmt('mean_combined_pct')} | {fmt('mean_seconds', 60)} | {fmt('mean_lean_candidate_checks')} | {row['failures']} |"
        )
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")
    return result
