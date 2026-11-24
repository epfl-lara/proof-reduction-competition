"""Read immutable discovery chains from host-owned evidence; no execution hooks."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from proof_eval.evidence.io import digest, read


@dataclass(frozen=True)
class CheckNode:
    number: int
    at: float
    origin: str
    accepted: bool
    all_versions_passed: bool
    combined_pct: float
    code_sha256: str


@dataclass(frozen=True)
class AttemptNode:
    number: int
    started: float
    ended: float
    incumbent_sha256: str | None
    checks: tuple[CheckNode, ...]
    cost_usd: float | None
    stop_kind: str | None = None
    end_basis: str = "attempt_marker"


@dataclass(frozen=True)
class ProblemTree:
    name: str
    condition: tuple[str, str]
    run: str
    schema_version: int
    problem_start: float
    deadline: float | None
    seed_combined_pct: float
    attempts: tuple[AttemptNode, ...]
    start_basis: str
    seed_sha256: str | None = None
    recorded_raw_pct: float | None = None
    status: str = "complete"
    input_files: tuple[tuple[str, str], ...] = ()
    post_terminal_checks: tuple[CheckNode, ...] = ()


class EvidenceReader:
    """Record precisely the files consulted and reject concurrent byte changes."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}

    def record(self, path: Path) -> None:
        key = str(path.resolve())
        value = digest(path)
        if key in self.files and self.files[key] != value:
            raise ValueError(f"Input changed while reading: {path}")
        self.files[key] = value

    def json(self, path: Path) -> dict:
        self.record(path)
        value = read(path)
        self.record(path)
        return value

    def ledger(self, path: Path) -> list[dict]:
        self.record(path)
        value = [json.loads(line) for line in path.read_text().splitlines() if line]
        self.record(path)
        return value

    def verify(self) -> None:
        for path, expected in self.files.items():
            if digest(path) != expected:
                raise ValueError(f"Input changed during replay: {path}")


def _epoch(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _score(evaluation: dict) -> float:
    value = float(evaluation["scores"]["combined_pct"])
    if not math.isfinite(value):
        raise ValueError("Nonfinite saved score")
    return value


def _cost(record: dict) -> float | None:
    value = record.get("total_usd")
    return float(value) if value is not None else None


def _check(record: dict) -> CheckNode:
    return CheckNode(
        int(record["number"]),
        _epoch(record["at"]),
        record["origin"],
        record["accepted"] is True,
        record["all_versions_passed"] is True,
        _score(record["evaluation"]),
        record["code_sha256"],
    )


def _load_cell(
    path: Path, config: dict, reader: EvidenceReader, *, allow_incomplete: bool
) -> ProblemTree:
    result = reader.json(path / "result.json")
    if result["status"] != "complete" and not allow_incomplete:
        raise ValueError(f"Incomplete terminal cell: {result['status']}")
    raw = result.get("before_final_cleanup")
    if raw is None:
        marker = path / "before_final_cleanup.json"
        raw = reader.json(marker) if marker.exists() else None
    if raw is None:
        raise ValueError("No saved raw incumbent before cleanup")
    ledger = reader.ledger(path / "evidence/checks.jsonl")
    checks = tuple(_check(row) for row in ledger)
    seed = result.get("seed_evaluation")
    if seed is None:
        seed = reader.json(path / "input.json")["seed_evaluation"]
    seed_pct = _score(seed)
    seed_sha = seed.get("candidate", {}).get("code_sha256")
    budget_path = path / "budget_started.json"
    budget = reader.json(budget_path) if budget_path.exists() else None
    deadline = float(budget["deadline_epoch"]) if budget else None
    records = [reader.json(p) for p in sorted(path.glob("attempt_*/attempt.json"))]
    attempts: list[AttemptNode] = []
    post_terminal_checks: tuple[CheckNode, ...] = ()
    if records:
        records.sort(key=lambda r: r["number"])
        expected_start = 0
        for number, record in enumerate(records):
            if record["number"] != number or record["check_start"] != expected_start:
                raise ValueError("Attempt numbers or check ranges are discontinuous")
            start = float(record["started_epoch"])
            end = record.get("ended_epoch")
            basis = "attempt_marker"
            check_end = record.get("check_end")
            if end is None:
                if (
                    deadline is None
                    or result.get("stop", {}).get("kind") != "time_limit"
                ):
                    raise ValueError(
                        "Indeterminate attempt without controlled deadline"
                    )
                end = deadline
                check_end = next(
                    (
                        i
                        for i, c in enumerate(checks)
                        if c.origin.startswith("deterministic_")
                    ),
                    len(checks),
                )
                basis = "saved_controlled_deadline_censored"
            end = float(end)
            if deadline is not None and end > deadline:
                end = deadline
                basis = "attempt_marker_clipped_to_saved_deadline"
            selected = checks[record["check_start"] : check_end]
            if any(c.origin.startswith("deterministic_") for c in selected):
                raise ValueError("Cleanup check inside recorded attempt")
            before = _cost(record.get("cost_before", {}))
            after = _cost(record.get("cost_after", {}))
            cost = after - before if before is not None and after is not None else None
            if cost is not None and cost < -1e-9:
                raise ValueError("Regressing cumulative cost")
            attempts.append(
                AttemptNode(
                    number,
                    start,
                    end,
                    record["incumbent_sha256"],
                    selected,
                    cost,
                    record.get("generation_status"),
                    basis,
                )
            )
            expected_start = int(check_end)
        post_terminal_checks = tuple(
            c
            for c in checks[expected_start:]
            if not c.origin.startswith("deterministic_")
        )
        if any(c.accepted or c.at < attempts[-1].ended for c in post_terminal_checks):
            raise ValueError("Unassigned accepted or pre-terminal raw check")
        problem_start = (
            float(budget["started_epoch"]) if budget else attempts[0].started
        )
        start_basis = "budget_started" if budget else "first_attempt_started_epoch"
        seed_sha = records[0]["incumbent_sha256"]
        seed_pct = _score(records[0]["incumbent_evaluation"])
    else:
        if len(list(path.glob("attempt_*"))) != 1:
            raise ValueError("Legacy cell is not a single recorded attempt")
        raw_checks = tuple(
            c for c in checks if not c.origin.startswith("deterministic_")
        )
        folder = path / "attempt_00"
        markers = []
        for name in ("request_started.json", "process.json"):
            if (folder / name).exists():
                marker = reader.json(folder / name)
                markers.append((_epoch(marker["started_at"]), name))
        generation = reader.json(folder / "generation.json")
        if (
            generation.get("finished_at")
            and generation.get("elapsed_seconds") is not None
        ):
            markers.append(
                (
                    _epoch(generation["finished_at"]) - generation["elapsed_seconds"],
                    "generation_finished_minus_elapsed",
                )
            )
        if not markers:
            raise ValueError("No legacy host start marker")
        problem_start, start_basis = min(markers)
        ended = max([_epoch(generation["finished_at"])] + [c.at for c in raw_checks])
        attempts.append(
            AttemptNode(
                0,
                problem_start,
                ended,
                seed_sha,
                raw_checks,
                _cost(result.get("cost", {})),
                generation.get("status"),
                "generation_end_and_last_raw_check",
            )
        )
    best, incumbent = seed_pct, seed_sha
    previous_end = problem_start
    for attempt in attempts:
        if attempt.started < previous_end - 1e-6 or attempt.ended < attempt.started:
            raise ValueError("Overlapping or reversed attempt timestamps")
        if attempt.incumbent_sha256 != incumbent:
            raise ValueError(
                "Recorded attempt parent SHA differs from accepted incumbent"
            )
        previous_at = attempt.started
        for check in attempt.checks:
            if check.at < previous_at - 1e-6 or check.at > attempt.ended + 1e-6:
                raise ValueError("Check outside recorded attempt timeline")
            previous_at = check.at
            if check.accepted:
                if (
                    not check.all_versions_passed
                    or check.combined_pct <= best + config["selection_margin_pp"]
                ):
                    raise ValueError(
                        "Saved acceptance violates all-version/margin contract"
                    )
                best, incumbent = check.combined_pct, check.code_sha256
        previous_end = attempt.ended
    if abs(best - _score(raw["evaluation"])) > 1e-9:
        raise ValueError("Ledger identity differs from saved raw incumbent")
    return ProblemTree(
        result["name"],
        (result["model"], result["effort"]),
        str(path.parent.parent),
        config["schema_version"],
        problem_start,
        deadline,
        seed_pct,
        tuple(attempts),
        start_basis,
        seed_sha,
        _score(raw["evaluation"]),
        result["status"],
        post_terminal_checks=post_terminal_checks,
    )


def load_run(
    path: Path, *, reader: EvidenceReader | None = None, allow_incomplete: bool = False
) -> tuple[list[ProblemTree], list[dict]]:
    """Load terminal cells with explicit exclusions; never dispatch evaluators."""
    path = path.resolve()
    reader = reader or EvidenceReader()
    config = reader.json(path / "config.json")
    trees, exclusions, seen = [], [], set()
    for cell in sorted((path / "cells").iterdir()):
        if not cell.is_dir():
            continue
        if not (cell / "result.json").exists():
            exclusions.append({"cell": str(cell), "reason": "no_terminal_result"})
            continue
        tree = _load_cell(cell, config, reader, allow_incomplete=allow_incomplete)
        key = tree.name, tree.condition
        if key in seen:
            raise ValueError(f"Duplicate terminal problem/condition: {key}")
        seen.add(key)
        trees.append(tree)
    for name in config["names"]:
        for condition in config["conditions"]:
            if (name, tuple(condition)) not in seen:
                exclusions.append(
                    {
                        "name": name,
                        "condition": condition,
                        "reason": "declared_cell_not_loaded",
                    }
                )
    reader.verify()
    return trees, exclusions
