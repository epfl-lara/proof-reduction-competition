"""Copy verified original control evidence into the prepared Qwen3.8 matrix.

Run only after the real extension repair matrix manifest exists. No model,
Lean, environment setup, or reference measurement calls occur here.
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
    """Hash ordinary files, excluding process locks; reject symlink evidence."""
    result = {}
    if folder.is_symlink():
        raise ValueError("Control source/destination must be an ordinary directory")
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlink in control evidence: " + str(path))
        if path.name.endswith(".lock"):
            continue
        if path.is_file():
            result[str(path.relative_to(folder))] = digest(path)
        elif not path.is_dir():
            raise ValueError("Non-ordinary control evidence: " + str(path))
    return result


def expected_spec(matrix, pack):
    return {"schema_version": 1, "name": pack["name"], "row_sha256": fingerprint(pack["row"]),
        "input_proof_sha256": sha(pack["proof"]), "methods": list(METHODS), "budget": asdict(BUDGET),
        "required_versions": versions(pack["row"]), "provenance": cleanup_provenance(matrix, pack["name"])}


def verify_job(folder, matrix, pack, reference):
    spec = expected_spec(matrix, pack)
    if read(folder / "job_config.json") != spec:
        raise ValueError("Control job configuration does not match the actual extension: " + pack["name"])
    result = read(folder / "result.json")
    if result["status"] != "complete" or not result["all_versions_valid"]:
        raise ValueError("Control cleanup is not complete and valid")
    if result["job_config_sha256"] != fingerprint(spec):
        raise ValueError("Control result/configuration identity changed")
    expected_stage_paths = {f"stages/{i:02d}_{method}/result.json" for i, method in enumerate(METHODS, 1)}
    if set(result["stage_result_sha256"]) != expected_stage_paths:
        raise ValueError("Control lacks the complete ten-method result hash manifest")
    for relative, value in result["stage_result_sha256"].items():
        if digest(folder / relative) != value:
            raise ValueError("Control stage result hash changed")
    audited = audit_cleanup_job(folder, pack["row"], reference, initial=pack["proof"],
                                provenance=spec["provenance"], complete=True)
    if audited["status"] != "complete" or audited["checked_stages"] != len(METHODS):
        raise ValueError("Control job did not pass its complete saved-evidence audit")
    return result, audited


def run(args):
    # This invokes the actual preparation code, not a forecast of a future
    # repair manifest. It fails if that real manifest/index is not ready.
    base, repair, output, base_config, matrix, packs = prepare(args)
    source = Path(args.source).resolve()
    if output == source or output in source.parents or source in output.parents:
        raise ValueError("Source and destination matrices must be separate")
    source_matrix = read(source / "matrix_config.json")
    if len(packs) != 15 or len(matrix["cells"]) != 75 or matrix["models"] != ["Qwen/Qwen3.8-27B"]:
        raise ValueError("Expected the separately declared fifteen-problem Qwen3.8 cohort")
    references = {row["name"]: row for row in (json.loads(line) for line in Path(args.references).read_text().splitlines() if line.strip())}
    if set(references) != set(packs):
        raise ValueError("Reference export cohort differs from the controls")
    for name, pack in packs.items():
        if references[name]["dataset_sha256"] != base_config["dataset_sha256"] or references[name]["status"] != "prepared":
            raise ValueError("Reference export identity changed")
        if set(references[name]["per_version"]) != set(pack["incumbent"]["per_version"]):
            raise ValueError("Reference version cohort differs")
        for version, item in pack["incumbent"]["per_version"].items():
            expected = item["reference"]
            exported = references[name]["per_version"][version]
            for field in ("heartbeats", "heartbeats_raw"):
                if exported[field] != expected[field]:
                    raise ValueError("Reference denominator changed")
            for field in ("measured_at", "environment_fingerprint", "reference_code_sha256"):
                if exported["provenance"][field] != expected[field]:
                    raise ValueError("Reference provenance changed")
    output.mkdir(parents=True, exist_ok=True)
    (output / "validation").mkdir(exist_ok=True)
    manifest_path = output / "validation/control_reuse.json"
    identity = {"schema_version": 1, "source_matrix_directory": str(source), "destination_matrix_directory": str(output),
        "source_matrix_config_sha256": digest(source / "matrix_config.json"), "destination_matrix_config_fingerprint": fingerprint(matrix),
        "repair_matrix_config_sha256": digest(repair / "matrix_config.json"), "reference_export_sha256": digest(args.references),
        "helper_sha256": digest(__file__), "expected_controls": 15,
        "accounting": "Copied historical original-control evidence. Its recorded trials/checks/cache hits/time are not newly executed extension work.",
        "calls": {"model": 0, "lean": 0, "reference_measurements": 0}}
    with (output / ".run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (output / "matrix_config.json").exists() and read(output / "matrix_config.json") != matrix:
            raise ValueError("Existing destination matrix configuration differs")
        manifest = read(manifest_path) if manifest_path.exists() else {
            "identity": identity, "started_at": datetime.now(timezone.utc).isoformat(), "controls": {}, "status": "copying"}
        if manifest["identity"] != identity:
            raise ValueError("Control-copy identity changed")
        # Verify every source first, so no mismatching cohort is partly copied.
        for name, pack in packs.items():
            key = job_key(name, pack["proof"])
            if source_matrix["controls"].get(name) != key or matrix["controls"].get(name) != key:
                raise ValueError("Source/destination control key mismatch")
            verify_job(source / "jobs" / key, matrix, pack, references[name])
        write_json(output / "matrix_config.json", matrix)
        write_json(manifest_path, manifest)
        for name, pack in packs.items():
            key = matrix["controls"][name]
            src, dst = source / "jobs" / key, output / "jobs" / key
            # The source jobs are complete; this lock prevents even a cache
            # reader from racing the snapshot. Busy jobs are not interrupted.
            with (src / ".job.lock").open("a") as source_lock:
                fcntl.flock(source_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result, audited = verify_job(src, matrix, pack, references[name])
                before = files(src)
                if dst.exists():
                    if files(dst) != before:
                        raise ValueError("Existing destination differs; refusing to overwrite: " + name)
                else:
                    dst.parent.mkdir(exist_ok=True)
                    temporary = Path(tempfile.mkdtemp(prefix=".control-copy-", dir=output / "validation"))
                    try:
                        shutil.copytree(src, temporary / "job", copy_function=shutil.copy2,
                                        ignore=lambda path, names: [entry for entry in names if entry.endswith(".lock")])
                        if files(temporary / "job") != before or files(src) != before:
                            raise ValueError("Control evidence changed while copying")
                        if dst.exists():
                            raise ValueError("Destination appeared during locked copy")
                        (temporary / "job").rename(dst)
                    finally:
                        shutil.rmtree(temporary)
                if files(src) != before or files(dst) != before:
                    raise ValueError("Copied control bytes differ")
                verify_job(dst, matrix, pack, references[name])
                record = {"name": name, "job_key": key, "source_directory": str(src), "destination_directory": str(dst),
                    "job_config_sha256": digest(src / "job_config.json"), "result_sha256": digest(src / "result.json"),
                    "file_sha256": before, "file_count": len(before), "byte_count": sum((src / relative).stat().st_size for relative in before),
                    "source_audit": audited, "historical_counters": result["counters"], "new_model_or_lean_calls": 0}
                if name in manifest["controls"] and manifest["controls"][name] != record:
                    raise ValueError("Previously copied control evidence changed")
                manifest["controls"][name] = record
                write_json(manifest_path, manifest)
        manifest["status"] = "complete"
        manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
        manifest["copied_controls"] = len(manifest["controls"])
        write_json(manifest_path, manifest)
        return {"status": "complete", "copied_controls": len(manifest["controls"]), "manifest": str(manifest_path), "calls": identity["calls"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "results/one_shot/04_combined_deterministic")
    parser.add_argument("--input", type=Path, default=ROOT / "results/one_shot/05_qwen38_extension/03_repaired_context_ablation")
    parser.add_argument("--output", type=Path, default=ROOT / "results/one_shot/05_qwen38_extension/04_combined_deterministic")
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
