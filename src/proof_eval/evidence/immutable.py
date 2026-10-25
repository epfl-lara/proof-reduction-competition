"""Small durable records for a new training lineage."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from proof_eval.evidence.io import digest as sha
from proof_eval.evidence.io import read

__all__ = ["canonical", "immutable", "read", "sha"]


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode()


def immutable(path: str | Path, value: object) -> str:
    path = Path(path)
    raw = canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ValueError(f"An immutable record already differs: {path}") from None
    return hashlib.sha256(raw).hexdigest()
