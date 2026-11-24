"""Separate prepared setup, local model search and CPU-only final cleanup."""

from __future__ import annotations

import fcntl
import json
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from proof_eval.evidence.io import digest, read, write_json, write_jsonl
from proof_eval.evidence.proof_states import export_proof_states, freeze_proof_states
from proof_eval.evidence.solutions import verified_model_solutions
from proof_eval.harness.configuration import load_inputs
from proof_eval.harness.submission import (
    _config,
    _native_environment,
    optimization_arguments,
    verify_initialization,
)
from proof_eval.providers import local_profile


def prepare_search_profile(bundle: Path, work: Path, recipe: dict) -> Path:
    """Freeze the identical search recipe with external, rather than inline, cleanup."""
    profile = work / "search-profile"
    if not profile.exists():
        local_profile.prepare(
            profile,
            model=recipe["model"],
            revision=recipe["revision"],
            workers=recipe["workers"],
            seconds=recipe["seconds"],
            context=recipe["context"],
            compaction=recipe["compaction"],
            verification_timeout_seconds=recipe["verification_seconds"],
            model_cache=work / "models",
            binary=str(work / "envs/serving/bin/vllm"),
            server_python=str(work / "envs/serving/bin/python"),
            proof_history=recipe["proof_history"],
            cleanup_before=False,
            cleanup_after=False,
            cleanup_workers=recipe.get("cleanup_workers", 32),
        )
    value, _ = local_profile.load(profile)
    for key in ("model", "revision", "workers", "seconds", "context", "compaction"):
        if value[key] != recipe[key]:
            raise ValueError("Search profile changed: " + key)
    if value.get("proof_history") != recipe["proof_history"] or any(
        value.get(key) for key in ("cleanup_before", "cleanup_after")
    ):
        raise ValueError(
            "Search profile must use the declared history and external cleanup"
        )
    return profile


@contextmanager
def _phase(output: Path, name: str, identity: dict):
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".submission-phase.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = output / (name + "-started.json")
        finished = output / (name + "-finished.json")
        if started.exists():
            raise ValueError(
                f"{name} already started; inspect its receipts instead of replaying it"
            )
        record = {"started_epoch": time.time(), "phase": name, **identity}
        write_json(started, record)
        result = {"status": "incomplete"}
        try:
            yield result
        finally:
            ended = time.time()
            write_json(
                finished,
                {
                    **record,
                    **result,
                    "finished_epoch": ended,
                    "elapsed_seconds": ended - record["started_epoch"],
                },
            )


def _identity(bundle: Path, work: Path) -> dict:
    from proof_eval.providers import readonly_mounts

    return {
        "recipe_sha256": digest(bundle / "recipe.json"),
        "initialization_sha256": digest(work / "initialized.json"),
        "filesystem_guard": readonly_mounts.identity(),
    }


def _timing(work: Path, output: Path, *, cleanup_requested: bool) -> None:
    write_json(
        output / "timing.json",
        {
            "setup": read(work / "preparation-finished.json"),
            "search": read(output / "search-timing.json"),
            "search_command": read(output / "search-finished.json"),
            "timed_run_finished": (
                read(output / "model-timer-finished.json")
                if (output / "model-timer-finished.json").exists()
                else None
            ),
            "cleanup": (
                read(output / "cleanup-finished.json")
                if cleanup_requested
                else {"status": "not_requested", "elapsed_seconds": 0}
            ),
            "scope": "Setup is outside the model budget. Optional CPU cleanup is separate; run it only when allowed outside the competition limit. All phase timings remain visible.",
        },
    )


def _ready(output: Path, name: str, identity: dict) -> dict | None:
    path = output / (name + "-ready.json")
    if not path.exists():
        return None
    receipt = read(path)
    if any(receipt.get(key) != value for key, value in identity.items()):
        raise ValueError("Saved phase belongs to another initialization")
    if digest(Path(receipt["submission"])) != receipt["sha256"]:
        raise ValueError("Saved phase submission changed")
    for file, key in (
        ("model-state.json", "proof_state_sha256"),
        ("model-certificates.json", "certificates_sha256"),
    ):
        if key in receipt and digest(output / file) != receipt[key]:
            raise ValueError("Saved phase proof evidence changed")
    finished = read(output / (name + "-finished.json"))
    if finished.get("status") != receipt.get("status") or finished.get(
        "status"
    ) not in {"complete", "incomplete"}:
        raise ValueError("Saved phase did not finish")
    return receipt


def _normal_search_outcomes(model_root: Path, recipe: dict) -> dict:
    """Proof delivery alone does not establish a normal full-window search."""
    from .limits import native_deadline_reached

    normal = []
    for cell in sorted((model_root / "cells").iterdir()):
        paths = [
            cell / n for n in ("result.json", "budget_started.json", "budget_end.json")
        ]
        if not all(path.is_file() for path in paths):
            continue
        result, clock, stopped = map(read, paths)
        cleanup = stopped.get("cleanup", {})
        closed = (
            cleanup.get("complete") is True
            and cleanup.get("freeze_complete") is True
            and cleanup.get("remaining_pids") == []
        ) or (
            not cleanup
            and stopped.get("worker_reaped_before_deadline_recovery") is True
            and native_deadline_reached(cell)
        )
        if (
            result.get("status") == "complete"
            and result.get("name") in recipe["names"]
            and (result.get("stop") or {}).get("kind") == "time_limit"
            and (result.get("time_budget") or {}).get("exhausted") is True
            and clock.get("timeout_seconds") == recipe["seconds"]
            and clock.get("deadline_epoch")
            == clock["started_epoch"] + recipe["seconds"]
            and stopped.get("exhausted") is True
            and stopped.get("work_stopped_epoch", 0) >= clock["deadline_epoch"]
            and closed
        ):
            normal.append(result["name"])
    if len(normal) != len(set(normal)):
        raise ValueError("Duplicate normally completed search problem")
    return {
        "normal_completed_names": normal,
        "normal_completed": len(normal),
        "incomplete_names": [name for name in recipe["names"] if name not in normal],
        "expected_problems": len(recipe["names"]),
    }


def prepare(bundle: Path, work: Path, **kwargs) -> dict:
    """Prepare assets and measure originals before any search clock starts."""
    from proof_eval.benchmark.submission_assets import prepare as prepare_assets
    from proof_eval.harness.submission import initialize

    finished = work / "preparation-finished.json"
    if finished.exists() and read(finished).get("status") == "complete":
        recipe, _ = verify_initialization(bundle, work)
        return {"status": "ready", "problems": len(recipe["names"]), "reused": True}
    with _phase(
        work, "preparation", {"recipe_sha256": digest(bundle / "recipe.json")}
    ) as phase:
        prepare_assets(bundle, work)
        result = initialize(bundle, work, **kwargs)
        phase.update(status="complete", model_calls=0, proof_search_calls=0)
        return result


def search(bundle: Path, work: Path, output: Path, *, preview: bool = False) -> dict:
    """Run only model search. The vLLM server is closed before this returns."""
    command_started = time.time()
    if not preview:
        print(
            json.dumps(
                {
                    "event": "SUBMISSION_STARTUP",
                    "started_epoch": command_started,
                    "search_timer_started": False,
                    "next": "verify prepared inputs, load model, complete host preflight",
                }
            ),
            flush=True,
        )
    recipe, cpu = verify_initialization(bundle, work)
    profile = work / "search-profile"
    initialized = read(work / "initialized.json")
    if initialized.get("search_profile_sha256") != digest(profile / "profile.json"):
        raise ValueError("Run this release's setup.sh before search")
    search_root = output / "search"
    model_root = search_root / "model"
    argv = optimization_arguments(bundle, work, search_root, recipe, cpu)
    argv[argv.index("--profile") + 1] = str(profile)
    if preview:
        return {
            "argv": ["proof-local-vllm", *argv],
            "model_calls": 0,
            "starts_server": False,
        }
    identity = _identity(bundle, work)
    ready = _ready(output, "search", identity)
    if ready is not None:
        return ready
    if output.exists() and any(output.iterdir()):
        raise ValueError(
            "Choose a fresh output directory; existing search is not replayed"
        )
    from proof_eval.providers.host_support import require_supported

    print(
        json.dumps(
            {
                "event": "HOST_KERNEL_CHECK",
                **require_supported(work / "host-checks"),
                "search_timer_started": False,
            }
        ),
        flush=True,
    )
    with _phase(output, "search", identity) as phase:
        from proof_eval.harness.pipeline_reporting import audit_pipeline
        from proof_eval.interfaces.local import main as local_main

        diagnostics = []
        try:
            with _native_environment(bundle):
                code = local_main(argv)
            if code:
                diagnostics.append({"stage": "search", "exit_code": code})
        except Exception as error:
            diagnostics.append(
                {"stage": "search", "error": f"{type(error).__name__}: {error}"}
            )
        # The certificate exporter rejects an active/indeterminate batch and any
        # missing or invalid proof, independently of native trace bookkeeping.
        rows, certificates = verified_model_solutions(model_root, recipe["names"])
        if (certificates["model"], certificates["effort"]) != (
            recipe["model"],
            recipe["effort"],
        ):
            raise ValueError("Saved proofs belong to another model condition")
        try:
            write_json(search_root / "audit.json", audit_pipeline(search_root))
        except Exception as error:
            diagnostics.append(
                {"stage": "trace_audit", "error": f"{type(error).__name__}: {error}"}
            )
        write_jsonl(output / "model-submission.jsonl", rows)
        records = {
            row["name"]: {
                "proof": row["proof"],
                "evaluation": certificates["certificates"][row["name"]]["evaluation"],
            }
            for row in rows
        }
        export_proof_states(
            output / "model-state.json",
            load_inputs(Path(cpu["base"])),
            Path(cpu["references"]),
            records,
            lineage={
                "kind": "model",
                "model": recipe["model"],
                "effort": recipe["effort"],
            },
        )
        write_json(output / "model-certificates.json", certificates)
        clocks = [
            read(path) for path in (model_root / "cells").glob("*/budget_started.json")
        ]
        terminal = read(model_root / "run.json")
        outcomes = _normal_search_outcomes(model_root, recipe)
        complete = (
            not diagnostics
            and terminal.get("status") in {"complete", "finished"}
            and outcomes["normal_completed"] == len(recipe["names"])
        )
        first_clock = min((clock["started_epoch"] for clock in clocks), default=None)
        terminal_epoch = (
            datetime.fromisoformat(terminal["at"].replace("Z", "+00:00")).timestamp()
            if terminal.get("at")
            else None
        )
        timing = {
            "command_started_epoch": command_started,
            "first_problem_clock_epoch": first_clock,
            "startup_before_search_seconds": (
                first_clock - command_started if first_clock is not None else None
            ),
            "model_batch_terminal_epoch": terminal_epoch,
            "model_search_wall_seconds": (
                terminal_epoch - first_clock
                if terminal_epoch is not None and first_clock is not None
                else None
            ),
            "problem_clock_seconds": {
                str(path.parent.name): read(path)["timeout_seconds"]
                for path in (model_root / "cells").glob("*/budget_started.json")
            },
            "problem_clock_seconds_kind": "configured_limit_not_observed_elapsed",
            "actual_problem_elapsed_seconds": {
                str(path.parent.name): (
                    read(path.parent / "budget_end.json")["work_stopped_epoch"]
                    if (path.parent / "budget_end.json").exists()
                    else terminal_epoch
                )
                - read(path)["started_epoch"]
                for path in (model_root / "cells").glob("*/budget_started.json")
                if (path.parent / "budget_end.json").exists()
                or terminal_epoch is not None
            },
            "setup_excluded": True,
            "cleanup_excluded": True,
            "search_tools_and_candidate_verification_included": True,
        }
        write_json(output / "search-timing.json", timing)
        receipt = {
            **identity,
            "status": "complete" if complete else "incomplete",
            "search_completed": complete,
            "proof_delivery_completed": True,
            "optimization_status": terminal.get("status"),
            "outcomes": outcomes,
            "phase": "search",
            "problems": len(rows),
            "submission": str(output / "model-submission.jsonl"),
            "sha256": digest(output / "model-submission.jsonl"),
            "proof_state_sha256": digest(output / "model-state.json"),
            "certificates_sha256": digest(output / "model-certificates.json"),
            "diagnostics": diagnostics,
            "timing": timing,
            "GPU_server_stopped": True,
            "verification": "Saved host all-required-version certificates",
        }
        write_json(output / "search-ready.json", receipt)
        write_jsonl(output / "submission.jsonl", rows)
        write_json(
            output / "submission-ready.json",
            {
                **receipt,
                "phase": "model_delivery",
                "submission": str(output / "submission.jsonl"),
                "model_submission_sha256": receipt["sha256"],
                "proof_source": "verified_model",
                "cleanup_requested": False,
                "cleanup_completed": False,
            },
        )
        phase.update(
            status=receipt["status"],
            search_completed=complete,
            proof_delivery_completed=True,
            submission_sha256=receipt["sha256"],
            diagnostics=diagnostics,
        )
    finished = {
        "event": "MODEL_SEARCH_FINISHED",
        "finished_epoch": time.time(),
        "status": receipt["status"],
        "search_completed": complete,
        "proof_delivery_completed": True,
        "GPU_server_stopped": True,
        "submission_sha256": receipt["sha256"],
        "CPU_cleanup_started": False,
    }
    write_json(output / "model-timer-finished.json", finished)
    _timing(work, output, cleanup_requested=False)
    print(json.dumps(finished), flush=True)
    return receipt


def cleanup(bundle: Path, work: Path, output: Path) -> dict:
    """Use the existing 32-worker one-sweep on this search's verified proofs; no GPU/model."""
    from proof_eval.evidence.submission import bundle_path, verify_bundle
    from proof_eval.optimization.cohort import audit_cleanup, run_cleanup

    recipe = verify_bundle(bundle)
    identity = _identity(bundle, work)
    ready = _ready(output, "cleanup", identity)
    if ready is not None:
        return ready
    source = _ready(output, "search", identity)
    if source is None or source.get("status") != "complete":
        raise ValueError(
            "Search must finish and publish its verified proofs before cleanup"
        )
    if (
        digest(output / "model-state.json") != source["proof_state_sha256"]
        or digest(output / "model-certificates.json") != source["certificates_sha256"]
    ):
        raise ValueError("Search proof state/certificates changed")
    from proof_eval.benchmark.submission import admit_setup

    cpu = admit_setup(_config(bundle, work, recipe))
    base = Path(cpu["base"])
    references = Path(cpu["references"])
    certificates = read(output / "model-certificates.json")
    state = read(output / "model-state.json")
    verified = {
        name: {
            "name": name,
            "selected_proof": row["proof"],
            "selected_evaluation": certificates["certificates"][name]["evaluation"],
        }
        for name, row in state["cells"].items()
    }
    with _phase(output, "cleanup", identity) as phase:
        delivery = read(output / "submission-ready.json")
        write_json(
            output / "submission-ready.json",
            {**delivery, "cleanup_requested": True, "cleanup_completed": False},
        )
        diagnostics = list(source["diagnostics"])
        report, audit = None, None
        cleanup_completed = False
        try:
            report = run_cleanup(
                base=base,
                dataset=bundle_path(bundle, recipe["dataset"]),
                environments=bundle_path(bundle, recipe["environments"]),
                cache=Path(cpu.get("cache", work / "reference_cache")),
                references=references,
                output=output / "cleanup",
                workers=recipe["cleanup_workers"],
                starting_proofs=output / "model-state.json",
                condition=(recipe["model"], recipe["effort"]),
                verified_starting_proofs=verified,
            )
            if report["status"] != "complete":
                raise ValueError("Cleanup did not complete")
            audit = audit_cleanup(output / "cleanup")
            if audit["status"] != "passed":
                raise ValueError("Cleanup audit did not pass")
            write_json(output / "cleanup/audit.json", audit)
            frozen = freeze_proof_states(
                output / "cleanup/state.json", load_inputs(base), references
            )
            cleanup_completed = True
        except Exception as error:
            # The already sealed, complete model proof set remains deliverable.
            # Keep the actual cleanup failure; never claim it passed or replay it.
            diagnostics.append(
                {"stage": "cleanup", "error": f"{type(error).__name__}: {error}"}
            )
            frozen = state
        rows = [
            {"name": name, "proof": frozen["cells"][name]["proof"]}
            for name in recipe["names"]
        ]
        write_jsonl(output / "submission.jsonl", rows)
        receipt = {
            **identity,
            "status": "complete" if cleanup_completed else "incomplete",
            "phase": "cleanup",
            "problems": len(rows),
            "submission": str(output / "submission.jsonl"),
            "sha256": digest(output / "submission.jsonl"),
            "model_submission_sha256": source["sha256"],
            "model_calls": 0,
            "GPU_required": False,
            "search_time_excluded": True,
            "cleanup_report": report,
            "cleanup_requested": True,
            "cleanup_completed": cleanup_completed,
            "proof_source": (
                "cleaned" if cleanup_completed else "verified_model_fallback"
            ),
            "audit": audit,
            "diagnostics": diagnostics,
        }
        write_json(output / "cleanup-ready.json", receipt)
        write_json(output / "submission-ready.json", receipt)
        phase.update(
            status=receipt["status"],
            submission_sha256=receipt["sha256"],
            cleanup_completed=cleanup_completed,
            diagnostics=diagnostics,
        )
    _timing(work, output, cleanup_requested=True)
    return receipt


def run(
    bundle: Path,
    work: Path,
    output: Path,
    *,
    preview: bool = False,
    final_cleanup: bool | None = None,
) -> dict:
    """Search, stop the model server, then default CPU cleanup unless disabled."""
    result = search(bundle, work, output, preview=preview)
    if preview:
        return result
    if final_cleanup is None:
        final_cleanup = read(bundle / "recipe.json").get("cleanup_after", True)
    if final_cleanup and result.get("status") == "complete":
        return cleanup(bundle, work, output)
    final = _ready(output, "cleanup", _identity(bundle, work))
    if final is not None:
        return final
    ready = read(output / "submission-ready.json")
    if (
        any(ready.get(key) != value for key, value in _identity(bundle, work).items())
        or ready["sha256"] != result["sha256"]
        or digest(output / "submission.jsonl") != result["sha256"]
    ):
        raise ValueError("Saved submission delivery changed")
    return ready
