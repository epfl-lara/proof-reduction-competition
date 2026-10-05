"""Cached reference reconstruction and all-version selection policy.

Every function in this module reads existing measurements; none invokes Lean.
"""

from __future__ import annotations

import math
from copy import deepcopy

from proof_eval.evidence.io import sha
from proof_eval.protocol import FIELDS

from .feedback import all_versions_passed
from .metrics import token_count, validate_candidate

REFERENCE_FIELDS = (
    "measured_at",
    "heartbeats",
    "heartbeats_raw",
    "environment_fingerprint",
    "reference_code_sha256",
)


def versions(row):
    return [version for item in row["version_info"] for version in item]


def score(evaluation):
    value = evaluation.get("scores", {}).get("combined_pct")
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError("A finite combined score is required for selection")
    return value


def require_valid(evaluation, row, proof=None):
    if not all_versions_passed(evaluation, versions(row)):
        raise ValueError(
            "Proof did not pass the exact required version set: " + row["name"]
        )
    if evaluation.get("status") != "passed":
        raise ValueError(
            "Valid proof lacks a complete authoritative score: " + row["name"]
        )
    score(evaluation)
    if proof is not None and evaluation.get("candidate", {}).get("code_sha256") != sha(
        validate_candidate(row, proof)[0]
    ):
        raise ValueError("Evaluation/proof identity mismatch: " + row["name"])


def original_evaluation(pack):
    row = pack["row"]
    normalized, body = validate_candidate(row, row["src"])
    if token_count(body) != row["proof_length"]:
        raise ValueError("Original token count differs from the fixed denominator")
    ev = deepcopy(pack["incumbent"])
    ev.update(
        measurement="cached_reference_identity",
        candidate={"length": row["proof_length"], "code_sha256": sha(normalized)},
        scores=dict(zip(FIELDS, (0.0, 0.0, 100.0, 100 / 3))),
    )
    ev["diagnostics"] = []
    for version, previous in ev["per_version"].items():
        ref = previous["reference"]
        if ref["status"] != "prepared" or ref["reference_code_sha256"] != sha(
            row["src"]
        ):
            raise ValueError("Cached reference identity mismatch")
        ev["per_version"][version] = {
            "status": "passed",
            "passed": True,
            "heartbeats": ref["heartbeats"],
            "heartbeats_raw": ref["heartbeats_raw"],
            "reference": ref,
            "heartbeat_reduction_pct": 0.0,
            "environment_fingerprint": ref["environment_fingerprint"],
            "diagnostics": [],
            "cached": True,
            "evidence": "Existing prepared reference; no new compiler run or heartbeat measurement",
        }
    require_valid(ev, row, row["src"])
    return ev


def check_references(evaluator, pack, base_config):
    """Compare saved reference metadata; this function never compiles a proof."""
    name = pack["name"]
    current = evaluator.get_reference(name)["versions"]
    saved_checks = pack["incumbent"]["per_version"]
    if set(current) != set(saved_checks) or set(current) != set(
        base_config["contexts"][name]
    ):
        raise ValueError("Cached reference version cohort changed: " + name)
    for version, saved in saved_checks.items():
        if current[version].get("status") != "prepared":
            raise ValueError(f"Cached reference unavailable: {name}/{version}")
        if (
            evaluator._context(pack["row"], version)[2]
            != base_config["contexts"][name][version]
        ):
            raise ValueError(f"Environment changed: {name}/{version}")
        for key in REFERENCE_FIELDS:
            if current[version].get(key) != saved["reference"].get(key):
                raise ValueError(f"Cached reference changed: {name}/{version}/{key}")


def required_versions(pack):
    return [version for item in pack["row"]["version_info"] for version in item]
