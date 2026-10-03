"""Copy completed original cleanup evidence into the parallel continuation.

Requires the real continuation repair manifest and a naturally drained original
combined run. Copies jobs only; the frozen runner rebuilds selections/manifests.
No model, Lean, environment setup, or reference measurement calls occur here.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import shutil
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from audit_combined_matrix import audit_cleanup_job
from proof_eval.one_shot import fingerprint
from run_combined_matrix import BUDGET, METHODS, cleanup_provenance, job_key, prepare, sha, versions
from run_deterministic import digest, write_json


def read(path):
    return json.loads(Path(path).read_text())


def files(folder):
    """Hash ordinary evidence files; process lock files are never copied."""
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Cleanup evidence must be an ordinary directory")
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlink in cleanup evidence: " + str(path))
        if path.name.endswith(".lock"):
            continue
        if path.is_file():
            result[str(path.relative_to(folder))] = digest(path)
        elif not path.is_dir():
            raise ValueError("Non-ordinary cleanup evidence: " + str(path))
    return result


def expected_spec(matrix, pack, proof):
    return {"schema_version": 1, "name": pack["name"], "row_sha256": fingerprint(pack["row"]),
        "input_proof_sha256": sha(proof), "methods": list(METHODS), "budget": asdict(BUDGET),
        "required_versions": versions(pack["row"]), "provenance": cleanup_provenance(matrix, pack["name"])}


def verify_job(folder, matrix, pack, reference, proof):
    spec = expected_spec(matrix, pack, proof)
    if read(folder / "job_config.json") != spec:
        raise ValueError("Cleanup job configuration differs from the continuation: " + pack["name"])
    result = read(folder / "result.json")
    if result["status"] != "complete" or not result["all_versions_valid"]:
        raise ValueError("Cleanup is not complete and all-version valid")
    if result["input_proof"] != proof or result["input_proof_sha256"] != sha(proof):
        raise ValueError("Cleanup input proof identity differs")
    if result["job_config_sha256"] != fingerprint(spec):
        raise ValueError("Cleanup result/configuration identity changed")
    expected_paths = {f"stages/{i:02d}_{method}/result.json" for i, method in enumerate(METHODS, 1)}
    if set(result["stage_result_sha256"]) != expected_paths:
        raise ValueError("Cleanup lacks all ten method result hashes")
    for relative, value in result["stage_result_sha256"].items():
        if digest(folder / relative) != value:
            raise ValueError("Cleanup stage result hash changed")
    audited = audit_cleanup_job(folder, pack["row"], reference, initial=proof,
                                provenance=spec["provenance"], complete=True)
    if audited["status"] != "complete" or audited["checked_stages"] != len(METHODS):
        raise ValueError("Cleanup failed its complete saved-evidence audit")
    return result, audited


def run(args):
    # Actual preparation checks the actual repair manifest and frozen inputs.
    base, repair, output, base_config, matrix, packs = prepare(args)
    source = Path(args.source).resolve()
    if output == source or output in source.parents or source in output.parents:
        raise ValueError("Source and destination matrices must be separate")
    if len(packs) != 15 or len(matrix["cells"]) != 225:
        raise ValueError("Expected the original fifteen-problem, 225-cell cohort")
    references = {row["name"]: row for row in (json.loads(line) for line in Path(args.references).read_text().splitlines() if line.strip())}
    if set(references) != set(packs):
        raise ValueError("Reference export cohort differs")
    for name, pack in packs.items():
        reference = references[name]
        if reference["dataset_sha256"] != base_config["dataset_sha256"] or reference["status"] != "prepared":
            raise ValueError("Reference export identity changed")
        if set(reference["per_version"]) != set(pack["incumbent"]["per_version"]):
            raise ValueError("Reference version cohort differs")
        for version, item in pack["incumbent"]["per_version"].items():
            expected, exported = item["reference"], reference["per_version"][version]
            for field in ("heartbeats", "heartbeats_raw"):
                if exported[field] != expected[field]:
                    raise ValueError("Reference denominator changed")
            for field in ("measured_at", "environment_fingerprint", "reference_code_sha256"):
                if exported["provenance"][field] != expected[field]:
                    raise ValueError("Reference provenance changed")
    output.mkdir(parents=True, exist_ok=True)
    (output / "validation").mkdir(exist_ok=True)
    manifest_path = output / "validation/cleanup_reuse.json"
    # The source lock establishes that its runner has exited, not merely written
    # a terminal status while it still owns the evidence tree.
    with (source / ".run.lock").open("a") as source_run_lock, (output / ".run.lock").open("a") as output_lock:
        fcntl.flock(source_run_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(output_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source_run = read(source / "run.json")
        if source_run["status"] != "incomplete_repair_terminal":
            raise ValueError("Original combined run has not naturally drained after repair shutdown")
        source_matrix = read(source / "matrix_config.json")
        if source_matrix["cells"] != matrix["cells"] or source_matrix["controls"] != matrix["controls"]:
            raise ValueError("Original and continuation cohorts differ")
        jobs = read(source / "jobs.json")["jobs"]
        summary = source_run["summary"]
        if summary["active_cleanup_jobs"] != 0 or summary["terminal_cleanup_jobs"] != len(jobs) or summary["unique_cleanup_jobs"] != len(jobs):
            raise ValueError("Original cleanup jobs have not all finished")
        if not set(matrix["controls"].values()).issubset(jobs):
            raise ValueError("Original cleanup is missing a control job")
        identity = {"schema_version": 1, "source_matrix_directory": str(source), "destination_matrix_directory": str(output),
            "source_matrix_config_sha256": digest(source / "matrix_config.json"), "source_run_sha256": digest(source / "run.json"),
            "source_jobs_sha256": digest(source / "jobs.json"), "destination_matrix_config_fingerprint": fingerprint(matrix),
            "repair_matrix_config_sha256": digest(repair / "matrix_config.json"), "reference_export_sha256": digest(args.references),
            "helper_sha256": digest(__file__), "expected_jobs": len(jobs), "expected_controls": 15,
            "accounting": "Copied historical original control/proposal work. Saved trial/check/cache/time counters are not newly executed continuation work.",
            "calls": {"model": 0, "lean": 0, "reference_measurements": 0}}
        if (output / "matrix_config.json").exists() and read(output / "matrix_config.json") != matrix:
            raise ValueError("Existing destination matrix configuration differs")
        manifest = read(manifest_path) if manifest_path.exists() else {
            "identity": identity, "started_at": datetime.now(timezone.utc).isoformat(), "jobs": {}, "status": "copying"}
        if manifest["identity"] != identity:
            raise ValueError("Cleanup-copy identity changed")
        for key, job in jobs.items():
            name, proof = job["name"], job["proof"]
            if key != job_key(name, proof) or job["proof_sha256"] != sha(proof):
                raise ValueError("Source job identity differs")
            if cleanup_provenance(source_matrix, name) != cleanup_provenance(matrix, name):
                raise ValueError("Source and destination cleanup provenance differs")
            verify_job(source / "jobs" / key, matrix, packs[name], references[name], proof)
            # Reject both ordinary and dangling destination symlinks.
            if (output / "jobs" / key).is_symlink():
                raise ValueError("Destination job is a symlink")
        write_json(output / "matrix_config.json", matrix)
        write_json(manifest_path, manifest)
        for key, job in jobs.items():
            name, proof = job["name"], job["proof"]
            src, dst = source / "jobs" / key, output / "jobs" / key
            with (src / ".job.lock").open("a") as source_lock:
                fcntl.flock(source_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result, audited = verify_job(src, matrix, packs[name], references[name], proof)
                before = files(src)
                if dst.exists() or dst.is_symlink():
                    if files(dst) != before:
                        raise ValueError("Existing destination differs; refusing to overwrite: " + key)
                else:
                    dst.parent.mkdir(exist_ok=True)
                    temporary = Path(tempfile.mkdtemp(prefix=".cleanup-copy-", dir=output / "validation"))
                    try:
                        shutil.copytree(src, temporary / "job", copy_function=shutil.copy2,
                                        ignore=lambda path, names: [entry for entry in names if entry.endswith(".lock")])
                        if files(temporary / "job") != before or files(src) != before:
                            raise ValueError("Cleanup evidence changed while copying")
                        if dst.exists() or dst.is_symlink():
                            raise ValueError("Destination appeared during locked copy")
                        (temporary / "job").rename(dst)
                    finally:
                        shutil.rmtree(temporary)
                if files(src) != before or files(dst) != before:
                    raise ValueError("Copied cleanup bytes differ")
                verify_job(dst, matrix, packs[name], references[name], proof)
                record = {"name": name, "job_key": key, "input_proof_sha256": sha(proof),
                    "is_control": key in matrix["controls"].values(), "source_origins": job["origins"],
                    "source_directory": str(src), "destination_directory": str(dst),
                    "job_config_sha256": digest(src / "job_config.json"), "result_sha256": digest(src / "result.json"),
                    "file_sha256": before, "file_count": len(before), "byte_count": sum((src / relative).stat().st_size for relative in before),
                    "source_audit": audited, "historical_counters": result["counters"], "new_model_or_lean_calls": 0}
                if key in manifest["jobs"] and manifest["jobs"][key] != record:
                    raise ValueError("Previously copied cleanup evidence changed")
                manifest["jobs"][key] = record
                write_json(manifest_path, manifest)
        manifest["status"] = "complete"
        manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
        manifest["copied_jobs"] = len(manifest["jobs"])
        manifest["copied_controls"] = sum(job["is_control"] for job in manifest["jobs"].values())
        write_json(manifest_path, manifest)
        return {"status": "complete", "copied_jobs": manifest["copied_jobs"], "copied_controls": manifest["copied_controls"],
            "manifest": str(manifest_path), "calls": identity["calls"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "results/one_shot/04_combined_deterministic")
    parser.add_argument("--input", type=Path, default=ROOT / "results/one_shot/06_parallel_continuation/03_repaired_context_ablation")
    parser.add_argument("--output", type=Path, default=ROOT / "results/one_shot/06_parallel_continuation/04_combined_deterministic")
    parser.add_argument("--references", type=Path, default=ROOT / "results/deterministic/00_reference_baseline/reference_values.jsonl")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/benchmark_data_warmup.jsonl")
    parser.add_argument("--environments", type=Path, default=ROOT / "environments.local.json")
    parser.add_argument("--cache", type=Path, default=ROOT / ".proof-eval")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--poll-seconds", type=float, default=5)
    parser.set_defaults(watch=True)
    print(json.dumps(run(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
