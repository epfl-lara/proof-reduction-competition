"""Repository paths for the editable research workspace."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
SNAPSHOTS = ROOT / "results/deterministic/validation/implementation_snapshots"
