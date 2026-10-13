"""Reuse a same-condition host certificate without remeasuring its proof."""

from __future__ import annotations

from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, read
from proof_eval.verification.feedback import all_versions_passed
from proof_eval.verification.references import (
    REFERENCE_FIELDS,
    require_valid,
    required_versions,
)


def freeze_incumbents(source: Path | None, config: dict, packs: dict) -> dict:
    """Pin prior results from this exact model, theorem context and reference cache."""
    if source is None:
        return {}
    source = source.resolve()
    path = source / "config.json"
    previous = read(path)
    if previous.get("first_attempt_condition") != config.get("first_attempt_condition"):
        raise ValueError("Incumbent source has another attempt schedule")
    for field in (
        "provider",
        "mode",
        "dataset_sha256",
        "environment_config_sha256",
        "base_config_sha256",
    ):
        if (
            previous.get(field, "codex" if field == "provider" else None)
            != config[field]
        ):
            raise ValueError(
                "Incumbent source changed the fixed configuration: " + field
            )
    pins = {}
    for name, pack in packs.items():
        if previous["input_sha256"].get(name) != config["input_sha256"][name]:
            raise ValueError("Incumbent source changed the prepared theorem: " + name)
        for model, effort in config["conditions"]:
            if [model, effort] not in previous["conditions"]:
                raise ValueError("Incumbent source has another model condition")
            key = fingerprint((name, model, effort, config["mode"]))
            result_path = source / "cells" / key / "result.json"
            if not result_path.exists():
                raise ValueError(
                    "No saved result for the same model condition: " + name
                )
            pins[key] = {
                "result_path": str(result_path),
                "result_sha256": digest(result_path),
                "source_config_path": str(path),
                "source_config_sha256": digest(path),
            }
            saved_incumbent({**config, "incumbent_sources": pins}, pack, model, effort)
    return pins


def saved_incumbent(
    config: dict, pack: dict, model: str, effort: str
) -> tuple[str, dict] | None:
    """Verify provenance, all-version validity and unchanged reference identities."""
    key = fingerprint((pack["name"], model, effort, config["mode"]))
    pin = config.get("incumbent_sources", {}).get(key)
    if pin is None:
        return None
    if (
        digest(pin["result_path"]) != pin["result_sha256"]
        or digest(pin["source_config_path"]) != pin["source_config_sha256"]
    ):
        raise ValueError("Frozen incumbent source changed")
    result = read(pin["result_path"])
    if (result["name"], result["model"], result["effort"], result["mode"]) != (
        pack["name"],
        model,
        effort,
        config["mode"],
    ) or result.get("provider", "codex") != config.get("provider", "codex"):
        raise ValueError("Incumbent belongs to another theorem or model condition")
    code, evaluation = result["selected_proof"], result["selected_evaluation"]
    require_valid(evaluation, pack["row"], code)
    if not all_versions_passed(evaluation, required_versions(pack)):
        raise ValueError("Saved incumbent does not pass every required version")
    for version in required_versions(pack):
        previous = evaluation["per_version"][version]["reference"]
        reference = pack["incumbent"]["per_version"][version]["reference"]
        if any(previous.get(k) != reference.get(k) for k in REFERENCE_FIELDS):
            raise ValueError("Saved incumbent changed the cached reference: " + version)
    return code, evaluation


def select_seed(
    config: dict, pack: dict, model: str, effort: str, seed: tuple[str, dict]
) -> tuple[str, dict]:
    """A previous model proof cannot displace a better original/deterministic seed."""
    previous = saved_incumbent(config, pack, model, effort)
    if (
        previous
        and previous[1]["scores"]["combined_pct"]
        > seed[1]["scores"]["combined_pct"] + config["selection_margin_pp"]
    ):
        return previous
    return seed
