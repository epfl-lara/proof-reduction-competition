"""Explicit CPU setup for a submission; no optimization or model requests."""

from __future__ import annotations

import fcntl
import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from proof_eval import Evaluator
from proof_eval.evidence.io import digest, fingerprint, read, write_json, write_jsonl
from proof_eval.paths import PACKAGE, ROOT
from proof_eval.verification.dataset import Dataset
from proof_eval.verification.reference_transfer import (
    export_references,
    import_references,
)

from .preparation import freeze_prepared_inputs, load_prepared
from .process import process_benchmark
from .setup import provision


@dataclass(frozen=True)
class SubmissionSetup:
    dataset: Path
    environments: Path
    work: Path
    build_projects: bool = True
    workers: int = 1
    cpus: int = 8
    verification_seconds: float = 600
    prepared_reference_bundle: Path | None = None
    prepared_reference_sha256: str | None = None


def project_rows(dataset: Dataset) -> dict[tuple[str, str], list[dict]]:
    """Reject inconsistent source pins before building or measuring anything."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for name in dataset.names:
        row = dataset.get(name)
        for entry in row["version_info"]:
            version = next(iter(entry))
            key = row["source"], version
            prior = groups.setdefault(key, [])
            if prior and (
                entry not in prior[0]["version_info"]
                or row.get("url") != prior[0].get("url")
            ):
                raise ValueError(f"Conflicting source/version pins: {key}")
            prior.append(row)
    return groups


def runtime_pins() -> dict[str, str]:
    """Freeze the maintained runtime and prompts, excluding saved experiments."""
    paths = [*PACKAGE.rglob("*.py"), *PACKAGE.rglob("*.c")]
    paths += [p for p in (ROOT / "prompts").rglob("*") if p.is_file()]
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}


def _request(config: SubmissionSetup) -> dict:
    dataset = Dataset(config.dataset)
    imported = None
    if (
        config.prepared_reference_bundle is not None
        or config.prepared_reference_sha256 is not None
    ):
        if (
            config.prepared_reference_bundle is None
            or not config.prepared_reference_sha256
        ):
            raise ValueError("Prepared reference import needs its path and SHA256")
        if (
            config.build_projects
            or digest(config.prepared_reference_bundle)
            != config.prepared_reference_sha256
        ):
            raise ValueError(
                "Prepared references require unchanged built environments and the exact bundle hash"
            )
        imported = {
            "path": str(config.prepared_reference_bundle.resolve()),
            "sha256": config.prepared_reference_sha256,
        }
    request = {
        "schema_version": 1,
        "dataset": str(config.dataset.resolve()),
        "dataset_sha256": digest(config.dataset),
        "environments": str(config.environments.resolve()),
        "environments_sha256": digest(config.environments),
        "published_heartbeats_sha256": (
            digest(dataset.path.with_name("benchmark_heartbeats.jsonl"))
            if dataset.path.with_name("benchmark_heartbeats.jsonl").exists()
            else None
        ),
        "names": dataset.names,
        "required_version_checks": sum(len(v) for v in project_rows(dataset).values()),
        "verification_seconds": config.verification_seconds,
        "build_projects": config.build_projects,
        "workers": config.workers,
        "cpus": config.cpus,
        "runtime_sha256": runtime_pins(),
        "starting_proofs": "organizer_originals",
        "optimization_calls": 0,
        "model_calls": 0,
        "measurement_timeout_retries": 0,
    }
    if imported is not None:
        request["prepared_reference_import"] = imported
    return request


def verify_setup(
    config: SubmissionSetup, *, evaluator: Evaluator | None = None
) -> dict:
    """Validate prepared references and environment identities; never compile proofs."""
    saved = read(config.work / "setup.json")
    if saved["request"] != _request(config):
        raise ValueError(
            "Submission setup inputs or runtime changed; use a new work directory"
        )
    evaluator = evaluator or Evaluator(
        config.dataset,
        config.environments,
        config.work / "reference_cache",
        timeout=config.verification_seconds,
    )
    base = Path(saved["base"])
    load_prepared(base, evaluator)
    if digest(base / "config.json") != saved["prepared_config_sha256"]:
        raise ValueError("Prepared input configuration changed")
    return saved


def admit_setup(config: SubmissionSetup, *, evaluator: Evaluator | None = None) -> dict:
    """Admit a complete CPU setup on this host without compiling any proof."""
    saved = read(config.work / "setup.json")
    if saved["request"] != _request(config):
        raise ValueError("Submission setup inputs or runtime changed")
    original = Path(saved["base"])
    if digest(original / "config.json") != saved["prepared_config_sha256"]:
        raise ValueError("Prepared input configuration changed")
    original_config = read(original / "config.json")
    for relative, expected in original_config["artifact_sha256"].items():
        if digest(original / relative) != expected:
            raise ValueError("Prepared input artifact changed: " + relative)
    evaluator = evaluator or Evaluator(
        config.dataset,
        config.environments,
        config.work / "reference_cache",
        timeout=config.verification_seconds,
    )
    if saved.get("machine") == evaluator.machine or "reference_bundle" not in saved:
        return verify_setup(config, evaluator=evaluator)
    bundle = saved["reference_bundle"]
    if digest(bundle["path"]) != bundle["sha256"]:
        raise ValueError("Portable reference bundle changed")
    folder = (
        config.work
        / "host_admissions"
        / fingerprint(
            {"setup_identity": saved["identity"], "machine": evaluator.machine}
        )
    )
    folder.mkdir(parents=True, exist_ok=True)
    cache = folder / "reference_cache"
    receiver = Evaluator(
        config.dataset,
        config.environments,
        cache,
        timeout=config.verification_seconds,
        backend=evaluator.backend,
        version_workers=evaluator.version_workers,
    )
    receiver.machine = dict(evaluator.machine)
    with (folder / ".admission.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        imported = import_references(receiver, Path(bundle["path"]), bundle["sha256"])
        prepared = freeze_prepared_inputs(receiver, config.environments, cache)
        current = read(prepared.base / "config.json")
        if current["input_sha256"] != original_config["input_sha256"] or digest(
            prepared.references
        ) != digest(Path(saved["references"])):
            raise ValueError("Host admission changed proofs or scoring denominators")
        admission = {
            "setup_identity": saved["identity"],
            "reference_bundle": bundle,
            "receiver_machine": receiver.machine,
            "reference_import": imported,
            "base": str(prepared.base),
            "references": str(prepared.references),
            "cache": str(cache),
            "prepared_config_sha256": digest(prepared.base / "config.json"),
            "model_calls": 0,
            "Lean_calls": 0,
        }
        path = folder / "admitted.json"
        if path.exists() and read(path) != admission:
            raise ValueError("Frozen host admission changed")
        if not path.exists():
            write_json(path, admission)
    return {
        **saved,
        **{
            key: admission[key]
            for key in ("base", "references", "cache", "prepared_config_sha256")
        },
        "original_preparation": {
            key: saved[key] for key in ("base", "references", "prepared_config_sha256")
        },
        "host_admission": str(path),
    }


def setup(config: SubmissionSetup, *, evaluator: Evaluator | None = None) -> dict:
    """Build bundled sources, measure each original once, and freeze a full cohort.

    Successful repeats are read-only. An interrupted/failed setup cannot repeat
    measurement automatically, including a timeout or unknown compiler outcome.
    """
    if config.workers < 1 or config.cpus < 1:
        raise ValueError("Setup worker and CPU counts must be positive")
    request = _request(config)
    config.work.mkdir(parents=True, exist_ok=True)
    with (config.work / ".setup.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (config.work / "setup.json").exists():
            return admit_setup(config, evaluator=evaluator)
        intent = config.work / "setup_started.json"
        if intent.exists():
            raise RuntimeError(
                "Prior setup has no complete receipt; inspect it before any new measurement"
            )
        started = time.time()
        write_json(intent, {"started_epoch": started, "request": request})
        try:
            dataset = Dataset(config.dataset)
            if config.build_projects:
                projects = {
                    (p["source"], p["version"]): (
                        config.environments.resolve().parent / p["path"]
                    ).resolve()
                    for p in read(config.environments)["projects"]
                }
                groups = project_rows(dataset)
                if not groups.keys() <= projects.keys():
                    raise ValueError(
                        "Bundled environments do not cover the complete cohort"
                    )
                logs = config.work / "build_logs"
                logs.mkdir(exist_ok=True)
                # Resolve the small cloud-release prerequisites before the
                # larger source builds, and stop immediately on their failure.
                ordered = sorted(
                    groups.items(), key=lambda item: item[0][0] != "putnambench"
                )
                if config.workers == 1:
                    results = []
                    for key, rows in ordered:
                        result = provision(
                            key, rows, logs, config.cpus,
                            project_path=projects[key], install_toolchains=False,
                        )
                        results.append(result)
                        write_json(config.work / "projects.json", {"projects": results})
                        if result["status"] != "built":
                            raise ValueError(
                                "Lean project setup failed; see " + result["log"]
                            )
                else:
                    with ThreadPoolExecutor(max_workers=config.workers) as pool:
                        futures = [
                            pool.submit(
                                provision,
                                key,
                                rows,
                                logs,
                                config.cpus,
                                project_path=projects[key],
                                install_toolchains=False,
                            )
                            for key, rows in ordered
                        ]
                        results = [f.result() for f in futures]
                write_json(config.work / "projects.json", {"projects": results})
                if any(r["status"] != "built" for r in results):
                    raise ValueError(
                        "Lean project setup failed; see build_logs and projects.json"
                    )
            evaluator = evaluator or Evaluator(
                config.dataset,
                config.environments,
                config.work / "reference_cache",
                timeout=config.verification_seconds,
            )
            if config.prepared_reference_bundle is not None:
                imported = import_references(
                    evaluator,
                    config.prepared_reference_bundle,
                    config.prepared_reference_sha256,
                )
                write_json(config.work / "reference-import.json", imported)
                summary = {
                    "total_problems": len(dataset.names),
                    "prepared_versions": imported["checks"],
                    "unavailable_versions": 0,
                    "reference_source": "explicit_verified_original_reference_import",
                    "source_sha256": imported["source_sha256"],
                    "Lean_calls": 0,
                    "model_calls": 0,
                }
            else:
                summary = process_benchmark(
                    evaluator,
                    config.work / "reference_values.jsonl",
                    protected_paths=(config.environments,),
                )
            if summary["unavailable_versions"]:
                raise ValueError(
                    "Original reference preparation is incomplete; no automatic retries"
                )
            prepared = freeze_prepared_inputs(
                evaluator, config.environments, evaluator.store.root
            )
            if config.prepared_reference_bundle is not None:
                with prepared.references.open(encoding="utf-8") as stream:
                    write_jsonl(
                        config.work / "reference_values.jsonl",
                        [json.loads(line) for line in stream if line.strip()],
                    )
            portable = config.work / "references.bundle.json"
            if config.prepared_reference_bundle is None:
                reference_bundle = export_references(evaluator, portable)
            else:
                if config.prepared_reference_bundle.resolve() != portable.resolve():
                    shutil.copyfile(config.prepared_reference_bundle, portable)
                if digest(portable) != config.prepared_reference_sha256:
                    raise ValueError("Portable reference copy changed")
                reference_bundle = {
                    "path": str(portable),
                    "sha256": digest(portable),
                    "checks": summary["prepared_versions"],
                }
            receipt = {
                "status": "complete",
                "request": request,
                "started_epoch": started,
                "finished_epoch": time.time(),
                "setup_elapsed_seconds": time.time() - started,
                "base": str(prepared.base),
                "references": str(prepared.references),
                "prepared_config_sha256": digest(prepared.base / "config.json"),
                "identity": fingerprint(request),
                "machine": evaluator.machine,
                "reference_bundle": reference_bundle,
                "summary": summary,
                "timing_scope": "CPU setup before optimization; no search or candidate optimization",
            }
            write_json(config.work / "setup.json", receipt)
            return receipt
        except BaseException as error:
            write_json(
                config.work / "setup_failure.json",
                {
                    "at_epoch": time.time(),
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "automatic_retry": False,
                },
            )
            raise
