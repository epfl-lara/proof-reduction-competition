"""Explicit original-proof measurement with isolated candidate and analysis caches."""

from __future__ import annotations

import time
from copy import copy
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, now, read, write_json

from .api import Evaluator, _Store
from .references import original_evaluation, require_valid


def adopt_prepared_original(evaluator: Evaluator, folder: Path, pack: dict):
    """Admit an already verified original without another compiler invocation."""
    evaluation = original_evaluation(pack)
    require_valid(evaluation, pack["row"], pack["row"]["src"])
    references = {
        version: item["reference"]
        for version, item in pack["incumbent"]["per_version"].items()
    }
    pin = fingerprint(references)
    path = folder / "initial_measurement.json"
    if path.exists():
        saved = read(path)
        if (
            saved.get("reference_policy") != "prepared_original_reference_identity"
            or saved.get("prepared_reference_sha256") != pin
            or saved.get("compiler_calls") != 0
            or saved.get("evaluation") != evaluation
        ):
            raise ValueError("Prepared original admission changed")
        return pack["row"]["src"], evaluation
    marker = folder / "initial_measurement_started.json"
    if marker.exists():
        raise RuntimeError("Prepared original admission has an unknown prior intent")
    started = time.time()
    write_json(
        marker, {"started_epoch": started, "kind": "prepared_reference_admission"}
    )
    write_json(
        path,
        {
            "at": now(),
            "started_epoch": started,
            "finished_epoch": time.time(),
            "evaluation": evaluation,
            "reference_policy": "prepared_original_reference_identity",
            "prepared_reference_sha256": pin,
            "compiler_calls": 0,
            "timeout_retries": 0,
            "attempt_sha256": {},
        },
    )
    return pack["row"]["src"], evaluation


def private_evaluator(evaluator: Evaluator, folder: Path, pack: dict) -> Evaluator:
    """Share immutable projects and denominators, never prior candidate caches."""
    local = copy(evaluator)
    local.store = _Store(folder / "evaluation_cache")
    for version, check in pack["incumbent"]["per_version"].items():
        key = local._context(pack["row"], version)[2]
        reference = check["reference"]
        saved = local.store.read("references", key)
        if saved is not None and saved != reference:
            raise ValueError("Private reference denominator changed")
        if saved is None:
            local.store.write("references", key, reference)
    return local


def measure_original(
    evaluator: Evaluator, folder: Path, pack: dict, *, timeout_retries: int = 0
) -> tuple[str, dict]:
    """Explicit fresh candidate measurement; canonical score denominators stay fixed."""
    if type(timeout_retries) is not int or timeout_retries not in (0, 1):
        raise ValueError("Original measurement allows at most one timeout retry")
    path = folder / "initial_measurement.json"
    if path.exists():
        result = read(path)
        if result.get("timeout_retries", 0) != timeout_retries:
            raise ValueError("Original measurement recovery policy changed")
        require_valid(result["evaluation"], pack["row"], pack["row"]["src"])
        if any(
            v.get("cached") is not False
            for v in result["evaluation"]["per_version"].values()
        ):
            raise ValueError("Original measurement reused a candidate cache")
        if result.get("selected_attempt") == 1:
            evaluator.store = private_evaluator(
                evaluator, folder / "initial_measurements/retry_01", pack
            ).store
        return pack["row"]["src"], result["evaluation"]
    marker = folder / "initial_measurement_started.json"
    if marker.exists():
        raise RuntimeError("Original measurement is indeterminate; not restarted")
    started = time.time()
    write_json(marker, {"at": now(), "started_epoch": started})
    attempt_hashes = {}
    local = evaluator
    for attempt in range(timeout_retries + 1):
        if attempt:
            local = private_evaluator(
                evaluator, folder / "initial_measurements/retry_01", pack
            )
        attempt_started = time.time()
        attempt_path = folder / "initial_measurements" / f"{attempt:02d}.json"
        write_json(
            attempt_path.with_suffix(".started.json"),
            {"started_epoch": attempt_started, "attempt": attempt},
        )
        evaluation = local.evaluate(pack["name"], pack["row"]["src"], versions="all")
        write_json(
            attempt_path,
            {
                "started_epoch": attempt_started,
                "finished_epoch": time.time(),
                "evaluation": evaluation,
            },
        )
        attempt_hashes[str(attempt_path.relative_to(folder))] = digest(attempt_path)
        if not timeout_only(evaluation, pack["row"]):
            break
    result = {
        "at": now(),
        "started_epoch": started,
        "finished_epoch": time.time(),
        "evaluation": evaluation,
        "reference_policy": "fresh_original_measurement_fixed_denominators",
        "timeout_retries": timeout_retries,
        "selected_attempt": attempt,
        "attempt_sha256": attempt_hashes,
    }
    write_json(path, result)
    require_valid(evaluation, pack["row"], pack["row"]["src"])
    if any(v.get("cached") is not False for v in evaluation["per_version"].values()):
        raise ValueError("Original measurement reused a candidate cache")
    evaluator.store = local.store
    return pack["row"]["src"], evaluation


def timeout_only(evaluation: dict, row: dict) -> bool:
    """Only a returned wall timeout, with every other required version passed."""
    expected = {v for entry in row["version_info"] for v in entry}
    checks = evaluation.get("per_version", {})
    return (
        set(checks) == expected
        and any(v.get("status") == "timeout" for v in checks.values())
        and all(v.get("status") in ("timeout", "passed") for v in checks.values())
    )


def audit_measurement_attempts(folder: Path, row: dict, timeout_retries: int) -> None:
    """Verify terminal-only recovery and preserve its full elapsed time and evidence."""
    result = read(folder / "initial_measurement.json")
    if "attempt_sha256" not in result and timeout_retries == 0:
        return  # Historical single-measurement evidence.
    selected = result["selected_attempt"]
    if (
        result["timeout_retries"] != timeout_retries
        or not 0 <= selected <= timeout_retries
    ):
        raise ValueError("Original measurement retry count changed")
    expected = [f"initial_measurements/{i:02d}.json" for i in range(selected + 1)]
    if list(result["attempt_sha256"]) != expected:
        raise ValueError("Original measurement attempt evidence is missing")
    prior = result["started_epoch"]
    for index, relative in enumerate(expected):
        path = folder / relative
        attempt = read(path)
        if (
            digest(path) != result["attempt_sha256"][relative]
            or not prior
            <= attempt["started_epoch"]
            <= attempt["finished_epoch"]
            <= result["finished_epoch"]
            or any(
                v.get("cached") is not False
                for v in attempt["evaluation"]["per_version"].values()
            )
        ):
            raise ValueError("Original measurement attempt changed or was cached")
        if index < selected and not timeout_only(attempt["evaluation"], row):
            raise ValueError("Original measurement retried a non-timeout failure")
        prior = attempt["finished_epoch"]
    if attempt["evaluation"] != result["evaluation"]:
        raise ValueError("Original measurement does not match its last attempt")
