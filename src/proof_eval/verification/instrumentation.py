"""Diagnostic source assembly for the explicitly selected module-safe backend."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import backend as legacy
from .backend_v2 import MEASUREMENT_WRAPPER, _source


def implementation_hash() -> str:
    """Bind diagnostic caches to this source assembly implementation."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def module_observation_source(
    row: dict,
    code: str,
    project: Path,
    nonce: str,
    support: str,
    command: str,
    *,
    replacement: str | None = None,
    measure: bool = False,
) -> tuple[str, int, str]:
    """Preserve declaration modifiers and UTF-8 offsets in diagnostic wrappers.

    This is observation-only assembly; candidate verification still uses the
    selected backend directly. The original wrapper's boundary identifies the
    supplied code even when its text also occurs in comments or source context.
    """
    source, mode = _source(row, code, project, nonce)
    prefix, separator, rest = source.partition("\n#proof_eval_measure_v2 ")
    if not separator:
        raise ValueError("Missing module-safe measurement boundary")
    header, newline, body = rest.partition("\n")
    if not newline or prefix.count(MEASUREMENT_WRAPPER) != 1:
        raise ValueError("Invalid module-safe instrumentation")
    measured_bytes = int(header.rsplit(" ", 1)[1]) - len(
        (prefix + separator + header + newline).encode()
    )
    end = len(legacy._masked_comments(code).rstrip())
    position = body.find(code)
    while (
        position >= 0 and len((body[:position] + code[:end]).encode()) != measured_bytes
    ):
        position = body.find(code, position + 1)
    if position < 0:
        raise ValueError("Diagnostic candidate does not match measured source")
    attached = body[:position]
    if attached and not attached.endswith("\n"):
        # Site edits use coordinates relative to code at column zero. Preserve
        # a pending modifier while keeping generated continuation indentation.
        attached = attached.rstrip() + "\n"
    candidate = attached + (code if replacement is None else replacement)
    prefix = prefix.replace(MEASUREMENT_WRAPPER, MEASUREMENT_WRAPPER + support, 1)
    outer = prefix + "\n" + command + "\n"
    if not measure:
        return outer + candidate + "\n", len((outer + attached).encode()), mode
    expected_end = 0
    candidate_end = len(legacy._masked_comments(candidate).rstrip())
    for _ in range(10):
        preamble = (
            outer
            + "#proof_eval_measure_v2 "
            + json.dumps("PROOF_EVAL_" + nonce)
            + " "
            + json.dumps(row["name"], ensure_ascii=False)
            + f" {expected_end}\n"
        )
        actual_end = len((preamble + candidate[:candidate_end]).encode())
        if actual_end == expected_end:
            return (
                preamble + candidate + "\n",
                len((preamble + attached).encode()),
                mode,
            )
        expected_end = actual_end
    raise ValueError("Could not establish diagnostic command boundary")
