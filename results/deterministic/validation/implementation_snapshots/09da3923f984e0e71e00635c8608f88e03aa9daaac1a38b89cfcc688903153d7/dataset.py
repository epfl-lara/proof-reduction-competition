"""Read immutable benchmark inputs and the separately published heartbeat data."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


PUBLISHED_HEARTBEATS_REVISION = "d9e46ee13c822925fb3031b0a0eac53b51631198"
PUBLISHED_HEARTBEATS_URL = (
    "https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena/raw/"
    f"{PUBLISHED_HEARTBEATS_REVISION}/benchmark_heartbeats.jsonl"
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{number}: expected a JSON object")
            rows.append(value)
    return rows


class Dataset:
    """Load reference values without recomputing any reference measurement.

    By default, load ``benchmark_heartbeats.jsonl`` beside the dataset if it
    exists. Missing heartbeat entries remain ``None``; they are never filled by
    compiling the reference. Returned rows are copies so callers cannot mutate
    the reference data shared by later evaluations.
    """

    def __init__(
        self,
        dataset_path: str | Path,
        heartbeats_path: str | Path | None = None,
    ) -> None:
        self.path = Path(dataset_path).resolve()
        heartbeat_path = (
            Path(heartbeats_path).resolve()
            if heartbeats_path is not None
            else self.path.with_name("benchmark_heartbeats.jsonl")
        )
        heartbeats: dict[str, int] = {}
        if heartbeats_path is not None or heartbeat_path.exists():
            for row in _read_jsonl(heartbeat_path):
                name, count = row.get("name"), row.get("heartbeat")
                if not isinstance(name, str) or not name:
                    raise ValueError(f"{heartbeat_path}: heartbeat row needs a name")
                if name in heartbeats:
                    raise ValueError(f"{heartbeat_path}: duplicate name: {name}")
                if type(count) is not int or count < 0:
                    raise ValueError(f"{heartbeat_path}: invalid heartbeat for {name}")
                heartbeats[name] = count

        self._rows: dict[str, dict[str, Any]] = {}
        for row in _read_jsonl(self.path):
            name = row.get("name")
            if not isinstance(name, str) or not name:
                raise ValueError(f"{self.path}: benchmark row needs a name")
            if name in self._rows:
                raise ValueError(f"{self.path}: duplicate name: {name}")
            for key in ("statement", "src"):
                if not isinstance(row.get(key), str) or not row[key].strip():
                    raise ValueError(f"{self.path}: {name} needs a nonempty {key}")
            length = row.get("proof_length")
            if type(length) is not int or length <= 0:
                raise ValueError(f"{self.path}: invalid reference proof_length for {name}")
            versions = row.get("version_info")
            if not isinstance(versions, list) or not versions:
                raise ValueError(f"{self.path}: {name} needs nonempty version_info")
            seen_versions: set[str] = set()
            for entry in versions:
                if not isinstance(entry, dict) or len(entry) != 1:
                    raise ValueError(f"{self.path}: malformed version_info for {name}")
                version, commit = next(iter(entry.items()))
                if not all(isinstance(value, str) and value for value in (version, commit)):
                    raise ValueError(f"{self.path}: malformed version_info for {name}")
                if version in seen_versions:
                    raise ValueError(f"{self.path}: duplicate version {version} for {name}")
                seen_versions.add(version)
            row["published_heartbeats"] = heartbeats.get(name)
            self._rows[name] = row
        if not self._rows:
            raise ValueError(f"{self.path}: empty benchmark")

    @property
    def names(self) -> list[str]:
        return list(self._rows)

    def get(self, name: str) -> dict[str, Any]:
        try:
            return copy.deepcopy(self._rows[name])
        except KeyError:
            raise KeyError(f"Unknown benchmark problem: {name}") from None
