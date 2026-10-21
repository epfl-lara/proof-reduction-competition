"""Full-cohort summaries and saved-certificate audits for transform screening."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from statistics import mean

from proof_eval.evidence.audit import _evaluation, _require
from proof_eval.evidence.io import digest, read, write_json
from proof_eval.paths import ROOT
from proof_eval.verification.initial import audit_measurement_attempts

from .limits import audit_discovery_limit


def report_study(output: Path) -> dict:
    config = read(output / "config.json")
    selection = (
        read(output / "selection.json")
        if (output / "selection.json").exists()
        else {"methods": {}}
    )
    conditions = {**config["conditions"], **selection["methods"]}
    rows = {}
    for name, methods in conditions.items():
        folder = output / "conditions" / name
        records = [read(p) for p in sorted(folder.glob("cells/*/result.json"))]
        complete = len(records) == len(config["names"]) and all(
            r["status"] in ("complete", "time_limit", "discovery_limit", "disabled")
            for r in records
        )
        rows[name] = {
            "methods": methods,
            "completed": len(records),
            "expected": len(config["names"]),
            "failures": len(list(folder.glob("cells/*/failure.json"))),
            "complete": complete,
            "mean_gain_pp": mean(r["gain_pp"] for r in records) if complete else None,
            "mean_combined_pct": (
                mean(r["evaluation"]["scores"]["combined_pct"] for r in records)
                if complete
                else None
            ),
            "mean_optimization_seconds": (
                mean(r["optimization_seconds"] for r in records) if complete else None
            ),
            "mean_total_seconds": (
                mean(r["elapsed_seconds"] for r in records) if complete else None
            ),
            "improved_problems": sum(r["gain_pp"] > 0 for r in records),
            "capped_problems": sum(r["status"] == "time_limit" for r in records),
            "discovery_limited_problems": sum(
                r["status"] == "discovery_limit" for r in records
            ),
        }
    finished = bool(selection["methods"]) and all(
        row["complete"] for row in rows.values()
    )
    ranking = sorted(
        (name for name, row in rows.items() if row["complete"]),
        key=lambda name: (
            -rows[name]["mean_gain_pp"],
            rows[name]["mean_optimization_seconds"],
            name,
        ),
    )
    result = {
        "status": "complete" if finished else "incomplete",
        "conditions": rows,
        "ranking": ranking,
        "scope": config["scope"],
        "recommended_methods": rows[ranking[0]]["methods"] if finished else None,
    }
    write_json(output / "report.json", result)
    lines = [
        "# Five-minute initial transform study",
        "",
        config["scope"],
        "",
        "The cap covers transform discovery and Lean verification. Original measurement precedes the cap and is included in total pipeline time. All cells use private candidate and analysis caches; canonical score denominators stay fixed.",
        "",
        "Recorded discovery timeouts retain the best verified proof and are counted separately below; they do not establish exhaustive discovery. Other verification or discovery failures remain incomplete.",
        "",
        "| Condition | Complete | Mean gain (pp) | Mean transform seconds | Mean total seconds | Capped | Discovery limited |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ranking + [name for name in rows if name not in ranking]:
        row = rows[name]
        values = [
            f"{row[key]:.3f}" if row[key] is not None else "pending"
            for key in (
                "mean_gain_pp",
                "mean_optimization_seconds",
                "mean_total_seconds",
            )
        ]
        lines.append(
            f"| {name} | {row['completed']}/{row['expected']} | {' | '.join(values)} | {row['capped_problems']} | {row['discovery_limited_problems']} |"
        )
    if finished:
        lines.extend(
            [
                "",
                "Best observed development portfolio: `"
                + " ".join(result["recommended_methods"])
                + "`.",
                "This selection has not yet been validated with model search or on held-out theorems.",
            ]
        )
    (output / "REPORT.md").write_text("\n".join(lines) + "\n")
    return result


def audit_study(output: Path) -> dict:
    config = read(output / "config.json")
    for key in ("dataset", "environments", "references"):
        _require(digest(config[key]) == config[key + "_sha256"], "Study input changed")
    for relative, expected in config["code_sha256"].items():
        _require(digest(ROOT / relative) == expected, "Study runtime changed")
    rows = {
        r["name"]: r
        for r in map(json.loads, Path(config["dataset"]).read_text().splitlines())
    }
    references = {
        r["name"]: r
        for r in map(json.loads, Path(config["references"]).read_text().splitlines())
    }
    selection = read(output / "selection.json")
    for relative, expected in selection["screen_result_sha256"].items():
        _require(
            digest(output / relative) == expected,
            "Screen changed after combination selection",
        )
    conditions = {**config["conditions"], **selection["methods"]}
    cells, outcomes = 0, 0
    for path in sorted((output / "conditions").glob("*/cells/*/result.json")):
        result = read(path)
        name, folder = result["name"], path.parent
        measurement = read(folder / "initial_measurement.json")
        audit_measurement_attempts(
            folder, rows[name], config.get("initial_measurement_timeout_retries", 0)
        )
        phase = read(folder / "optimization/result.json")
        audit_discovery_limit(folder / "optimization", phase)
        certificates = read(folder / "optimization/certificates.json")
        _require(
            digest(folder / "initial_measurement.json") == result["measurement_sha256"]
            and digest(folder / "optimization/result.json")
            == result["optimization_sha256"]
            and digest(folder / "optimization/certificates.json")
            == phase["certificates_sha256"],
            "Study evidence changed",
        )
        _require(
            phase["spec"]["methods"] == conditions[result["condition"]]
            and 0 < phase["spec"]["seconds"] == config["seconds"] <= 300
            and phase["started_epoch"] >= measurement["finished_epoch"]
            and phase["deadline_epoch"] - phase["started_epoch"]
            <= config["seconds"] + 1e-5,
            "Transform portfolio or cap changed",
        )
        _require(
            certificates[0]["proof"] == rows[name]["src"]
            and certificates[0]["evaluation"] == measurement["evaluation"]
            and all(
                v.get("cached") is False
                for v in measurement["evaluation"]["per_version"].values()
            ),
            "Study did not freshly measure its original input",
        )
        previous = None
        for certificate in certificates:
            outcomes += _evaluation(
                rows[name],
                references[name],
                certificate["proof"],
                certificate["evaluation"],
                "transform study",
            )
            value = certificate["evaluation"]["scores"]["combined_pct"]
            if previous is not None:
                _require(
                    value > previous + 0.05
                    and datetime.fromisoformat(certificate["at"]).timestamp()
                    <= phase["deadline_epoch"],
                    "Late or regressive transform certificate",
                )
            previous = value
        _require(
            result["proof"] == phase["proof"] == certificates[-1]["proof"]
            and result["evaluation"]
            == phase["evaluation"]
            == certificates[-1]["evaluation"]
            and abs(
                result["gain_pp"]
                - (previous - measurement["evaluation"]["scores"]["combined_pct"])
            )
            < 1e-9,
            "Study selected proof or gain changed",
        )
        for relative, expected in phase["stage_result_sha256"].items():
            _require(
                digest(folder / "optimization" / relative) == expected,
                "Stage evidence changed",
            )
        cells += 1
    return {
        "status": "passed",
        "cells": cells,
        "checked_version_outcomes": outcomes,
        "scope": "Saved evidence only; cohort completeness is reported separately",
    }
