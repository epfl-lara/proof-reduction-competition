"""Cohort barriers between deterministic preparation, model search and cleanup."""

from __future__ import annotations

import fcntl
import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, now, read, write_json
from proof_eval.evidence.proof_states import (
    export_proof_states,
    freeze_proof_states,
    guard_proof_states,
    validate_lineage,
)
from proof_eval.optimization.cohort import run_cleanup
from proof_eval.optimization.search_graph import plans
from proof_eval.paths import ROOT

from .audit import audit as audit_model
from .config import RunConfig
from .configuration import load_inputs
from .pipeline_reporting import audit_pipeline, report_pipeline
from .runner import run as run_model


class _IncompleteCleanup(Exception):
    """A terminal incomplete phase blocks the next cohort barrier."""


@dataclass(frozen=True)
class PipelineConfig:
    """Independent worker pools; model budgets exclude the two cleanup phases."""

    model: RunConfig
    cleanup_before: bool = True
    cleanup_after: bool = True
    cleanup_workers: int = 8
    before_workers: int | None = None
    after_workers: int | None = None

    def __post_init__(self) -> None:
        for key in ("cleanup_before", "cleanup_after"):
            if type(getattr(self, key)) is not bool:
                raise ValueError(key + " must be a boolean")
        for key in ("cleanup_workers", "before_workers", "after_workers"):
            value = getattr(self, key)
            if value is not None and (type(value) is not int or value < 1):
                raise ValueError(key + " must be a positive integer")
        if self.model.action not in {"run", "prepare"}:
            raise ValueError("A pipeline supports run or prepare")
        if self.model.names:
            raise ValueError("Prepare a separate full-cohort base for a subset")
        if self.model.deterministic or self.model.deterministic_checkpoint:
            raise ValueError("Pipeline cleanup is external; use starting_proofs")


def _serializable(value):
    if isinstance(value, Path):
        return str(value.expanduser().resolve())
    if isinstance(value, dict):
        return {key: _serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializable(item) for item in value]
    return value


def _configuration(args: PipelineConfig, packs: dict) -> dict:
    model = args.model
    source = freeze_proof_states(model.starting_proofs, packs, model.references)
    for condition in model.conditions:
        validate_lineage(source, condition)
    fields = asdict(model)
    fields.pop("action")
    return {
        "cohort_pipeline_version": 1,
        "names": list(packs),
        "conditions": [list(c) for c in model.conditions],
        "model": _serializable(fields),
        "cleanup_before": args.cleanup_before,
        "cleanup_after": args.cleanup_after,
        "before_workers": args.before_workers or args.cleanup_workers,
        "after_workers": args.after_workers or args.cleanup_workers,
        "model_workers": model.workers,
        "cleanup_plan": plans()["one_sweep"].record(),
        "starting_proofs": source,
        "input_sha256": {name: fingerprint(pack) for name, pack in packs.items()},
        "file_sha256": {
            str(Path(path).resolve()): digest(path)
            for path in (model.dataset, model.environments, model.references)
        },
        "code_sha256": {
            str(p.relative_to(ROOT)): digest(p)
            for p in sorted((ROOT / "src/proof_eval").rglob("*.py"))
        },
        "budget_scope": "model_phase",
        "timing_scope": "Whole workflow wall time includes cleanup and phase transitions; model timers include model-phase verification and tools only",
    }


def _guard(config: dict, packs: dict) -> None:
    for path, expected in config["file_sha256"].items():
        if digest(path) != expected:
            raise ValueError("Frozen pipeline input changed: " + path)
    for path, expected in config["code_sha256"].items():
        if digest(ROOT / path) != expected:
            raise ValueError("Frozen pipeline runtime changed: " + path)
    if config["input_sha256"] != {n: fingerprint(p) for n, p in packs.items()}:
        raise ValueError("Frozen pipeline packs changed")
    guard_proof_states(
        config["starting_proofs"], packs, Path(config["model"]["references"])
    )


def _phase(output: Path, name: str, action) -> dict:
    path = output / "phases" / (name + ".json")
    prior = read(path) if path.exists() else {}
    if prior.get("status") == "complete":
        # Revalidate/reuse the sealed stage without rewriting its historical
        # boundary to a time after a downstream phase already started.
        result = action()
        if result["status"] != "complete":
            raise ValueError("Previously complete phase became incomplete: " + name)
        return result
    record = {
        "name": name,
        "started_epoch": prior.get("started_epoch", time.time()),
        "status": "running",
    }
    write_json(path, record)
    try:
        result = action()
        record.update(status=result["status"])
        return result
    except Exception as error:
        record.update(status="incomplete", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        record["finished_epoch"] = time.time()
        record["elapsed_seconds"] = record["finished_epoch"] - record["started_epoch"]
        write_json(path, record)


def run_pipeline(args: PipelineConfig) -> dict:
    """Run all preparation before any model request, then clean each model cohort."""
    invocation_started = time.time()
    model, output = args.model, args.model.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".pipeline.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        packs = load_inputs(model.base)
        config = _configuration(args, packs)
        path = output / "config.json"
        if path.exists() and read(path) != config:
            raise ValueError("Frozen pipeline changed; use a new output directory")
        if not path.exists() and any(
            p.name != ".pipeline.lock" for p in output.iterdir()
        ):
            raise ValueError("Pipeline output is not empty; use a new output directory")
        packs_path = output / "packs.json"
        if packs_path.exists() and read(packs_path) != packs:
            raise ValueError("Frozen pipeline packs changed")
        write_json(path, config)
        write_json(packs_path, packs)
        _guard(config, packs)
        if (output / "run.json").exists() and read(output / "run.json")[
            "status"
        ] == "complete":
            audit_pipeline(output)
            return report_pipeline(output)

        cleanup = {
            key: getattr(model, key)
            for key in ("base", "dataset", "environments", "cache", "references")
        }
        seed_condition = (
            tuple(model.conditions[0]) if len(model.conditions) == 1 else None
        )
        # Preflight freezes provider/tool assets without dispatching Lean or models.
        run_model(
            replace(model, output=output / "preflight" / "model", action="prepare")
        )
        if args.cleanup_before:
            run_cleanup(
                output=output / "before",
                workers=config["before_workers"],
                starting_proofs=model.starting_proofs,
                condition=seed_condition,
                prepare_only=True,
                **cleanup,
            )
        if model.action == "prepare":
            write_json(
                output / "preflight.json",
                {
                    "status": "passed",
                    "at": now(),
                    "compiler_calls": 0,
                    "model_calls": 0,
                },
            )
            return {
                "status": "prepared",
                "planned_cells": len(packs) * len(model.conditions),
            }

        prior = read(output / "run.json") if (output / "run.json").exists() else {}
        started = prior.get("started_epoch", invocation_started)
        write_json(
            output / "run.json",
            {"status": "running", "started_epoch": started, "at": now()},
        )
        failure = None
        try:
            source = model.starting_proofs
            if args.cleanup_before:
                before = _phase(
                    output,
                    "before",
                    lambda: run_cleanup(
                        output=output / "before",
                        workers=config["before_workers"],
                        starting_proofs=source,
                        condition=seed_condition,
                        **cleanup,
                    ),
                )
                if before["status"] != "complete":
                    raise _IncompleteCleanup
                source = output / "before" / "state.json"
            _guard(config, packs)
            model_args = replace(model, output=output / "model", starting_proofs=source)
            try:
                _phase(output, "model", lambda: run_model(model_args))
            except RuntimeError:
                # The batch has already continued all queued theorems. Completed
                # conditions can still receive their own cleanup; others stay incomplete.
                saved_report = output / "model" / "report.json"
                if not saved_report.exists() or all(
                    item["complete"] for item in read(saved_report)["conditions"]
                ):
                    raise
            model_audit = audit_model(output / "model")
            write_json(output / "model" / "audit.json", model_audit)
            model_report = read(output / "model" / "report.json")
            records = [
                read(p) for p in (output / "model" / "cells").glob("*/result.json")
            ]
            for summary in model_report["conditions"]:
                if not summary["complete"]:
                    continue
                condition = (summary["model"], summary["effort"])
                key = fingerprint(condition)
                selected = {
                    r["name"]: r
                    for r in records
                    if (r["model"], r["effort"]) == condition
                }
                state_path = output / "model_states" / (key + ".json")
                export_proof_states(
                    state_path,
                    packs,
                    model.references,
                    selected,
                    lineage={
                        "kind": "model",
                        "model": condition[0],
                        "effort": condition[1],
                    },
                )
                if args.cleanup_after:
                    _phase(
                        output,
                        "after_" + key,
                        lambda: run_cleanup(
                            output=output / "after" / key,
                            workers=config["after_workers"],
                            starting_proofs=state_path,
                            condition=condition,
                            **cleanup,
                        ),
                    )
            _guard(config, packs)
            result = report_pipeline(output)
            if result["status"] == "complete":
                write_json(output / "audit.json", audit_pipeline(output))
        except _IncompleteCleanup:
            pass
        except BaseException as error:
            failure = f"{type(error).__name__}: {error}"
            raise
        finally:
            report_error = None
            try:
                result = report_pipeline(output)
            except Exception as error:
                report_error = error
                result = {"status": "incomplete"}
                failure = failure or f"{type(error).__name__}: {error}"
            write_json(
                output / "run.json",
                {
                    "status": "incomplete" if failure else result["status"],
                    "started_epoch": started,
                    "finished_epoch": time.time(),
                    **({"error": failure} if failure else {}),
                    "at": now(),
                },
            )
            if report_error is None:
                result = report_pipeline(output)
            else:
                result["error"] = failure
            write_json(output / "report.json", result)
            if (
                report_error is not None
                and failure == f"{type(report_error).__name__}: {report_error}"
            ):
                # Preserve an original exception if reporting also failed.
                if sys.exc_info()[0] is None:
                    raise report_error
        return result
