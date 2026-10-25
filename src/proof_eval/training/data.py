"""Exact RL reserve and disjoint held-out/source split checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

RL_SHA = "aa2b134604582982b89326eb1d5891b915dc81f887f8433c464e107a1e533403"


def load_rows(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def task_key(row: dict) -> tuple[str, str]:
    return row["source"], row["name"]


def validate_reserve(dataset_dir: str | Path) -> list[dict]:
    root = Path(dataset_dir)
    rl_path = root / "rl-reserved.jsonl"
    if hashlib.sha256(rl_path.read_bytes()).hexdigest() != RL_SHA:
        raise ValueError("The authorized 200-task reserve changed")
    rl = load_rows(rl_path)
    keys = {task_key(row) for row in rl}
    if len(rl) != 200 or len(keys) != 200:
        raise ValueError("RL reserve must contain 200 distinct source/name IDs")
    for file, expected in [("sft.jsonl", 1857), ("validation.jsonl", 50)]:
        rows = load_rows(root / file)
        if len(rows) != expected or keys.intersection(map(task_key, rows)):
            raise ValueError(f"RL overlap or wrong cohort size in {file}")
    return rl


def task_id(row: dict) -> str:
    return hashlib.sha256(
        json.dumps(task_key(row), ensure_ascii=False).encode()
    ).hexdigest()[:24]
