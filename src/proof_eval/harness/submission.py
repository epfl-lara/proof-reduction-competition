"""Submission initialization and launch through the maintained local workflow."""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

from proof_eval.benchmark.submission import SubmissionSetup, admit_setup, setup
from proof_eval.evidence.io import digest, fingerprint, read, write_json
from proof_eval.evidence.submission import bundle_path, verify_bundle
from proof_eval.providers import local_profile, signal_scope, vllm_server

SERVING_VERSIONS = {
    "vllm": "0.31.0+cu129",
    "torch": "2.13.0+cu129",
    "transformers": "5.17.0",
}


@contextmanager
def _native_environment(bundle: Path):
    values = {
        "PATH": str(bundle / "bin") + os.pathsep + os.environ.get("PATH", ""),
        "PROOF_SIGNAL_SCOPE_BINARY": str(bundle / "bin/signal-scope"),
    }
    previous = {k: os.environ.get(k) for k in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _config(
    bundle: Path,
    work: Path,
    recipe: dict,
    prepared_reference_bundle: Path | None = None,
    prepared_reference_sha256: str | None = None,
) -> SubmissionSetup:
    if (
        recipe.get("track") != "open_local"
        or recipe.get("starting_proofs") != "organizer_originals"
    ):
        raise ValueError(
            "This submission recipe requires local open models and organizer original proofs"
        )
    if any(
        type(recipe.get(k)) is not bool
        for k in ("proof_history", "cleanup_before", "cleanup_after")
    ):
        raise ValueError("History and cleanup must be explicit booleans")
    if (
        prepared_reference_bundle is None
        and prepared_reference_sha256 is None
        and (work / "setup.json").exists()
    ):
        imported = read(work / "setup.json")["request"].get("prepared_reference_import")
        if imported:
            prepared_reference_bundle, prepared_reference_sha256 = (
                Path(imported["path"]),
                imported["sha256"],
            )
    return SubmissionSetup(
        dataset=bundle_path(bundle, recipe["dataset"]),
        environments=bundle_path(bundle, recipe["environments"]),
        work=work,
        workers=recipe["setup_workers"],
        cpus=recipe["setup_cpus"],
        verification_seconds=recipe["verification_seconds"],
        build_projects=prepared_reference_bundle is None,
        prepared_reference_bundle=prepared_reference_bundle,
        prepared_reference_sha256=prepared_reference_sha256,
    )


def _snapshot(python: Path, recipe: dict, cache: Path, *, download: bool) -> str:
    """Resolve/download a pinned snapshot without starting vLLM or allocating GPUs."""
    return subprocess.check_output(
        [
            str(python),
            "-c",
            "import sys; from huggingface_hub import snapshot_download; "
            "print(snapshot_download(sys.argv[1],revision=sys.argv[2],cache_dir=sys.argv[3],local_files_only=sys.argv[4]=='local'))",
            recipe["model"],
            recipe["revision"],
            str(cache / "hub"),
            "download" if download else "local",
        ],
        text=True,
    ).strip()


def initialize(
    bundle: Path,
    work: Path,
    *,
    prepared_reference_bundle: Path | None = None,
    prepared_reference_sha256: str | None = None,
) -> dict:
    """All model files, builds and original measurements precede optimization."""
    work.mkdir(parents=True, exist_ok=True)
    with (work / ".initialization.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _initialize(
            bundle,
            work,
            prepared_reference_bundle=prepared_reference_bundle,
            prepared_reference_sha256=prepared_reference_sha256,
        )


def _initialize(
    bundle: Path,
    work: Path,
    *,
    prepared_reference_bundle: Path | None = None,
    prepared_reference_sha256: str | None = None,
) -> dict:
    recipe = verify_bundle(bundle)
    config = _config(
        bundle, work, recipe, prepared_reference_bundle, prepared_reference_sha256
    )
    python, binary = work / "envs/serving/bin/python", work / "envs/serving/bin/vllm"
    if not python.is_file() or not binary.is_file():
        raise ValueError("Run install.sh to install the separate serving environment")
    with _native_environment(bundle):
        native = signal_scope.configured_identity()
    profile = work / "profile"
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
            binary=str(binary),
            server_python=str(python),
            proof_history=recipe["proof_history"],
            cleanup_before=recipe["cleanup_before"],
            cleanup_after=recipe["cleanup_after"],
            cleanup_workers=recipe.get("cleanup_workers", 32),
        )
    value, server = local_profile.load(profile)
    for key in ("model", "revision", "workers", "seconds", "context", "compaction"):
        if value[key] != recipe[key]:
            raise ValueError(
                "Prepared local profile differs from submission recipe: " + key
            )
    for key in ("proof_history", "cleanup_before", "cleanup_after"):
        if value.get(key, False) != recipe[key]:
            raise ValueError(
                "Prepared local policy differs from submission recipe: " + key
            )
    if value.get("cleanup_workers", 32) != recipe.get("cleanup_workers", 32):
        raise ValueError("Prepared cleanup workers differ from submission recipe")
    plugin = bundle / "integrations/vllm_ampere"
    runtime = vllm_server.metadata(server, plugin)
    if runtime["versions"] != SERVING_VERSIONS:
        raise ValueError(
            "Serving package versions differ from the validated submission stack; run install.sh"
        )
    # Runtime admission is cheap and must precede project builds/reference I/O.
    cpu = setup(config)
    from proof_eval.harness.submission_phases import prepare_search_profile

    search_profile = prepare_search_profile(bundle, work, recipe)
    # No server process, synthetic inference or benchmark optimization in setup.
    snapshot = _snapshot(python, recipe, work / "models", download=True)
    semantic = None
    if recipe["semantic_search"]:
        from proof_eval.harness.semantic import SemanticSearchConfig, freeze

        semantic = freeze(
            SemanticSearchConfig(
                bundle_path(bundle, recipe["semantic_index"]),
                bundle_path(bundle, recipe["embedding_model"]),
            )
        )
    receipt = {
        "schema_version": 1,
        "recipe_sha256": digest(bundle / "recipe.json"),
        "cpu_setup_identity": cpu["identity"],
        "snapshot": snapshot,
        "profile_sha256": digest(profile / "profile.json"),
        "search_profile_sha256": digest(search_profile / "profile.json"),
        "runtime": runtime,
        "signal_scope": native,
        "semantic": semantic,
        "optimization_calls": 0,
        "model_calls": 0,
    }
    git_config = work / "git-safe.config"
    if git_config.is_file():
        receipt["git_safe_config_sha256"] = digest(git_config)
    path = work / "initialized.json"
    if path.exists() and read(path) != receipt:
        raise ValueError("Initialized runtime changed; use a new work directory")
    if not path.exists():
        write_json(path, receipt)
    return {
        "status": "ready",
        "setup": str(work / "setup.json"),
        "initialization": str(path),
    }


def verify_initialization(bundle: Path, work: Path) -> tuple[dict, dict]:
    recipe = verify_bundle(bundle)
    saved = read(work / "initialized.json")
    if (
        "git_safe_config_sha256" in saved
        and digest(work / "git-safe.config") != saved["git_safe_config_sha256"]
    ):
        raise ValueError("Prepared source ownership exceptions changed")
    cpu = admit_setup(_config(bundle, work, recipe))
    if (
        saved["recipe_sha256"] != digest(bundle / "recipe.json")
        or saved["cpu_setup_identity"] != cpu["identity"]
    ):
        raise ValueError("Submission initialization changed")
    _, server = local_profile.load(work / "profile")
    if saved["profile_sha256"] != digest(work / "profile/profile.json") or saved[
        "runtime"
    ] != vllm_server.metadata(server, bundle / "integrations/vllm_ampere"):
        raise ValueError("Serving profile or environment changed")
    if (
        _snapshot(Path(server.python), recipe, work / "models", download=False)
        != saved["snapshot"]
    ):
        raise ValueError("Pinned model snapshot changed")
    with _native_environment(bundle):
        if signal_scope.configured_identity() != saved["signal_scope"]:
            raise ValueError("Signal ownership runtime changed")
    if saved["semantic"] is not None:
        from proof_eval.harness.semantic import guard

        guard(saved["semantic"])
    return recipe, cpu


def optimization_arguments(
    bundle: Path, work: Path, output: Path, recipe: dict, cpu: dict
) -> list[str]:
    forwarded = [
        "--base",
        cpu["base"],
        "--references",
        cpu["references"],
        "--dataset",
        str(bundle_path(bundle, recipe["dataset"])),
        "--environments",
        str(bundle_path(bundle, recipe["environments"])),
        "--cache",
        str(cpu.get("cache", work / "reference_cache")),
        "--original-measurement-policy",
        "prepared",
        "--web-search" if recipe["web_search"] else "--no-web-search",
    ]
    if recipe["semantic_search"]:
        forwarded += [
            "--semantic-search",
            "--semantic-index",
            str(bundle_path(bundle, recipe["semantic_index"])),
            "--embedding-model",
            str(bundle_path(bundle, recipe["embedding_model"])),
        ]
    else:
        forwarded += ["--no-semantic-search"]
    return [
        "run",
        "--profile",
        str(work / "profile"),
        "--output",
        str(output),
        "--plugin",
        str(bundle / "integrations/vllm_ampere"),
        "--",
        *forwarded,
    ]


def run_submission(
    bundle: Path,
    work: Path,
    output: Path,
    *,
    preview: bool = False,
    prepared_reference_bundle: Path | None = None,
    prepared_reference_sha256: str | None = None,
) -> dict:
    """Run the unchanged full-cohort harness; setup never dispatches this action."""
    if prepared_reference_bundle is not None or prepared_reference_sha256 is not None:
        if preview:
            raise ValueError("Initialize imported references before previewing the run")
        initialize(
            bundle,
            work,
            prepared_reference_bundle=prepared_reference_bundle,
            prepared_reference_sha256=prepared_reference_sha256,
        )
    recipe, cpu = verify_initialization(bundle, work)
    argv = optimization_arguments(bundle, work, output, recipe, cpu)
    if preview:
        return {
            "argv": ["proof-local-vllm", *argv],
            "model_calls": 0,
            "starts_server": False,
        }
    output.mkdir(parents=True, exist_ok=True)
    runtime = local_profile.runtime_directory(output)
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / ".submission.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _optimize(bundle, work, output, recipe, cpu, argv)


def _optimize(
    bundle: Path, work: Path, output: Path, recipe: dict, cpu: dict, argv: list[str]
) -> dict:
    from proof_eval.harness.cli import main as harness_main
    from proof_eval.interfaces.local import main as local_main

    marker = local_profile.runtime_directory(output) / "optimization_started.json"
    intent = {
        "recipe_sha256": digest(bundle / "recipe.json"),
        "setup_identity": cpu["identity"],
        "argv_sha256": fingerprint(argv),
    }
    if marker.exists():
        saved = read(marker)
        if saved["intent"] != intent:
            raise ValueError(
                "Optimization configuration changed; use a new output directory"
            )
    else:
        saved = {"started_epoch": time.time(), "intent": intent}
        write_json(marker, saved)
    code = 1
    diagnostics = []
    try:
        try:
            with _native_environment(bundle):
                native_code = local_main(argv)
            if native_code:
                raise RuntimeError(f"Optimization command exited {native_code}")
        except Exception as error:
            diagnostics.append(
                {"stage": "optimization", "error": f"{type(error).__name__}: {error}"}
            )
        try:
            if harness_main(["audit", "--output", str(output)]) != 0:
                raise ValueError("Saved execution trace audit did not pass")
        except Exception as error:
            diagnostics.append(
                {"stage": "trace_audit", "error": f"{type(error).__name__}: {error}"}
            )
        if diagnostics:
            # Native usage/logging faults cannot withhold fully verified proofs.
            # A missing or invalid proof certificate still prevents publication.
            from proof_eval.evidence.solutions import verified_model_solutions

            try:
                rows, proof_receipt = verified_model_solutions(
                    output / "model", recipe["names"]
                )
            except (OSError, KeyError, ValueError) as error:
                raise ValueError(
                    "Cannot publish a complete submission: verified proof evidence is missing or invalid"
                ) from error
            if recipe.get("cleanup_after", False):
                diagnostics.append(
                    {
                        "stage": "cleanup",
                        "error": "Retained verified model proofs because the requested workflow did not complete",
                    }
                )
        elif recipe.get("cleanup_after", False):
            report = read(output / "report.json")
            conditions = report["conditions"]
            if len(conditions) != 1 or not conditions[0]["complete"]:
                raise ValueError("Expected one complete post-cleanup condition")
            from proof_eval.evidence.proof_states import freeze_proof_states

            state = freeze_proof_states(
                Path(conditions[0]["selected_state"]),
                read(output / "packs.json"),
                Path(cpu["references"]),
            )
            rows = [
                {"name": name, "proof": state["cells"][name]["proof"]}
                for name in recipe["names"]
            ]
        else:
            candidates = list(
                (output / "model/conditions").glob("*/selected_candidates.jsonl")
            )
            if len(candidates) != 1:
                raise ValueError("Expected one complete model condition")
            rows = [
                json.loads(line)
                for line in candidates[0].read_text().split("\n")
                if line.strip()
            ]
        if len(rows) != len(recipe["names"]) or {r["name"] for r in rows} != set(
            recipe["names"]
        ):
            raise ValueError("Selected proof export does not cover the full benchmark")
        from proof_eval.evidence.io import write_jsonl

        by_name = {row["name"]: row for row in rows}
        rows = [by_name[name] for name in recipe["names"]]
        write_jsonl(output / "submission.jsonl", rows)
        receipt = {
            "status": "ready",
            "problems": len(rows),
            "submission": str(output / "submission.jsonl"),
            "sha256": digest(output / "submission.jsonl"),
            "verification": (
                "Saved host all-version proof certificates"
                if diagnostics
                else "Passed saved-evidence audit"
            ),
            "diagnostics": diagnostics,
        }
        if diagnostics:
            receipt["proof_certificates"] = proof_receipt
        write_json(output / "submission-ready.json", receipt)
        code = 0
        return {
            "status": "complete",
            "submission": str(output / "submission.jsonl"),
            "sha256": digest(output / "submission.jsonl"),
        }
    finally:
        # The pipeline requires a fresh output at entry. Publish its original
        # launch clock only after the native invocation has returned.
        write_json(output / "optimization_started.json", saved)
        write_json(
            output / "optimization_finished.json",
            {
                "finished_epoch": time.time(),
                "elapsed_seconds": time.time() - saved["started_epoch"],
                "exit_code": code,
                "setup_excluded": True,
                "status": "complete" if code == 0 else "incomplete",
                "submission_ready": code == 0,
                "diagnostics": diagnostics,
                "timing_scope": "Optimization command, server startup/shutdown and final export/audit; resume gaps included",
            },
        )
