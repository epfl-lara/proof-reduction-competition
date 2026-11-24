"""Paths within the materialized inference source workspace."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
SNAPSHOTS = ROOT / "results/deterministic/validation/implementation_snapshots"
