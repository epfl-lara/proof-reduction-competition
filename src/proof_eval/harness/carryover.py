"""Carry spent budgets and verified proofs into a new runtime without resetting."""

from __future__ import annotations

from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, read, write_json
from proof_eval.providers.costs import CostConfig, generations_cost


def _key(config: dict, name: str, model: str, effort: str) -> str:
    return fingerprint((name, model, effort, config["mode"]))


def source_records(pin: dict) -> tuple[dict, dict, dict | None]:
    """Read only pinned host evidence; a changed prior attempt blocks recovery."""
    for stem in ("result", "source_config", "budget"):
        if stem == "budget" and pin.get("budget_path") is None:
            continue
        if digest(pin[stem + "_path"]) != pin[stem + "_sha256"]:
            raise ValueError("Carried budget evidence changed: " + stem)
    return tuple(
        read(pin[stem + "_path"]) if pin.get(stem + "_path") is not None else None
        for stem in ("source_config", "result", "budget")
    )


def carried_generations(config: dict, name: str, model: str, effort: str) -> list[dict]:
    """Include every billed prior attempt, including failed terminal responses."""
    pin = config.get("budget_carryover", {}).get(_key(config, name, model, effort))
    if pin is None:
        return []
    previous, result, _ = source_records(pin)
    if (result["name"], result["model"], result["effort"], result["mode"]) != (
        name,
        model,
        effort,
        config["mode"],
    ):
        raise ValueError("Carried budget belongs to another theorem or condition")
    return carried_generations(previous, name, model, effort) + result["generations"]


def freeze_carryover(source: Path | None, config: dict, packs: dict) -> dict:
    """Audit a stopped run and freeze costs/deadlines for its existing cells."""
    if source is None:
        return {}
    from .audit import audit

    source = source.resolve()
    previous_path = source / "config.json"
    previous = read(previous_path)
    run = read(source / "run.json")
    if run["status"] == "running":
        raise ValueError("Cannot carry budgets from a running batch")
    audit(source)
    for field in (
        "provider",
        "mode",
        "dataset_sha256",
        "environment_config_sha256",
        "base_config_sha256",
        "cost_assumptions",
        "rate_card",
        "budget_tracking",
        "budget_usd_per_problem",
        "problem_timeout_seconds",
    ):
        if previous.get(field) != config[field]:
            raise ValueError("Carried budget changed the fixed configuration: " + field)
    if config["budget_tracking"] != "cost":
        raise ValueError("Budget carryover requires cost tracking")
    if any(
        previous["cli"][field] != config["cli"][field]
        for field in ("sha256", "version")
    ):
        raise ValueError("Carried budget changed the native executable")
    pins = {}
    for name, pack in packs.items():
        if previous["input_sha256"].get(name) != config["input_sha256"][name]:
            raise ValueError("Carried budget changed the prepared theorem: " + name)
        for model, effort in config["conditions"]:
            key = _key(config, name, model, effort)
            folder = source / "cells" / key
            result_path = folder / "result.json"
            if not result_path.exists():
                if (folder / "cell_process.json").exists():
                    raise ValueError(
                        "Prior started cell has no terminal result; not resampled"
                    )
                continue
            result = read(result_path)
            generations = (
                carried_generations(previous, name, model, effort)
                + result["generations"]
            )
            cost = generations_cost(
                CostConfig(model, effort, **config["cost_assumptions"]),
                generations,
                budget_usd=config["budget_usd_per_problem"],
            )
            if cost["total_usd"] is None:
                raise ValueError(
                    "Cannot carry a budget with unknown cumulative spending"
                )
            budget_path = folder / "budget_started.json"
            pins[key] = {
                "result_path": str(result_path),
                "result_sha256": digest(result_path),
                "source_config_path": str(previous_path),
                "source_config_sha256": digest(previous_path),
                "budget_path": str(budget_path) if budget_path.exists() else None,
                "budget_sha256": digest(budget_path) if budget_path.exists() else None,
            }
    return pins


def restore_deadlines(output: Path, config: dict) -> None:
    """Use the original start and deadline; time spent on recovery still counts."""
    for key, pin in config.get("budget_carryover", {}).items():
        _, _, budget = source_records(pin)
        path = output / "cells" / key / "budget_started.json"
        if budget is None:
            if path.exists():
                raise ValueError("Carried cost-only budget acquired a deadline")
            continue
        if path.exists():
            if read(path) != budget:
                raise ValueError("Carried problem deadline was replenished")
        else:
            write_json(path, budget)


def audit_deadline(config: dict, result: dict, folder: Path) -> None:
    key = _key(config, result["name"], result["model"], result["effort"])
    pin = config.get("budget_carryover", {}).get(key)
    if pin is not None:
        _, _, previous_budget = source_records(pin)
        if previous_budget is None:
            if (folder / "budget_started.json").exists():
                raise ValueError("Carried cost-only budget acquired a deadline")
            return
        if read(folder / "budget_started.json") != previous_budget:
            raise ValueError("Carried problem deadline was replenished")
