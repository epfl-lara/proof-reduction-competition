"""Two live cleanup jobs reused by the full matrix; run from repository root."""
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
from proof_eval import Evaluator
from run_combined_matrix import (
    prepare, read, digest, write_json, job_key, cleanup_proof,
    cleanup_provenance, check_references, now,
)

args = Namespace(
    input="results/one_shot/03_repaired_context_ablation",
    output="results/one_shot/04_combined_deterministic",
    dataset="data/benchmark_data_warmup.jsonl",
    environments="environments.local.json", cache=".proof-eval",
    workers=2, watch=True, poll_seconds=5.0,
)
base, repair_root, output, base_config, matrix, packs = prepare(args)
config_path = output / "matrix_config.json"
if config_path.exists() and read(config_path) != matrix:
    raise ValueError("Pilot configuration changed")
write_json(config_path, matrix)

cell_key = "cec7d783e27ac43ebb5639c8613400c577723bce2ef88f4be0774355828e88c0"
repair_path = repair_root / "cells" / cell_key / "result.json"
repair = read(repair_path)
pack = packs[repair["name"]]
assert repair["accepted"] and repair["final_valid"]
evaluator = Evaluator(args.dataset, args.environments, args.cache)

def guard():
    for path, expected in matrix["code_sha256"].items():
        if digest(ROOT / path) != expected:
            raise ValueError("Frozen implementation changed: " + path)
    if digest(repair_root / "matrix_config.json") != matrix["repair_matrix_config_sha256"]:
        raise ValueError("Repair configuration changed")
    check_references(evaluator, pack, base_config)

guard()
meta = {
    "status": "running", "started_at": now(), "name": pack["name"],
    "source_cell_key": cell_key, "source_result_sha256": digest(repair_path),
    "matrix_config_sha256": digest(config_path),
    "script_sha256": digest(Path(__file__)),
    "scope": "Engineering validation on the first accepted model proposal and its incumbent; two jobs reused in the complete matrix, not a full-benchmark comparison.",
}
manifest = output / "validation" / "engineering_pilot.json"
write_json(manifest, meta)

def work(item):
    label, proof = item
    key = job_key(pack["name"], proof)
    result = cleanup_proof(
        evaluator=evaluator, row=pack["row"], proof=proof,
        folder=output / "jobs" / key,
        provenance=cleanup_provenance(matrix, pack["name"]), guard=guard,
    )
    print(label, result["status"], result["evaluation"]["scores"], flush=True)
    return label, {"job_key": key, "status": result["status"],
                   "initial": result["initial_evaluation"]["scores"],
                   "final": result["evaluation"]["scores"],
                   "counters": result["counters"],
                   "result_sha256": digest(output / "jobs" / key / "result.json")}

try:
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = dict(pool.map(work, [("control", pack["proof"]), ("proposal", repair["final_proof"])]))
    guard()
    meta.update(status="complete" if all(r["status"] == "complete" for r in results.values()) else "incomplete", results=results, finished_at=now())
    write_json(manifest, meta)
except BaseException as exc:
    meta.update(status="interrupted", error=type(exc).__name__ + ": " + str(exc), finished_at=now())
    write_json(manifest, meta)
    raise
