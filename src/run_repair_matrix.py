"""Apply the frozen validity-repair protocol to an entire arriving one-shot matrix.

One initial proposal is reused per cell. At most three correctness-only repair
calls follow, with independently bounded concurrency per model. No initial
generation is requested, references are never prepared, and pilot evidence is
copied only when its exact cell configuration matches.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import fcntl
import json
import math
from pathlib import Path
import shutil
import tempfile
import time

from proof_eval import Evaluator
from proof_eval.one_shot import fingerprint
from proof_eval.rcp import RCPClient
from run_deterministic import digest, write_json
from run_validity_repair import ROOT, SYSTEM, repair_cell


FROZEN_REPAIR_FILES = ("src/run_validity_repair.py", "src/validity_feedback.py")
IMPLEMENTATION_FILES = (*FROZEN_REPAIR_FILES, "src/run_repair_matrix.py")
REFERENCE_FIELDS = ("measured_at", "heartbeats", "heartbeats_raw", "environment_fingerprint", "reference_code_sha256")


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def check_references(evaluator, pack, base_config):
    """Compare saved reference metadata; this function never compiles a proof."""
    name = pack["name"]
    current = evaluator.get_reference(name)["versions"]
    saved_checks = pack["incumbent"]["per_version"]
    if set(current) != set(saved_checks) or set(current) != set(base_config["contexts"][name]):
        raise ValueError("Cached reference version cohort changed: " + name)
    for version, saved in saved_checks.items():
        if current[version].get("status") != "prepared":
            raise ValueError(f"Cached reference unavailable: {name}/{version}")
        if evaluator._context(pack["row"], version)[2] != base_config["contexts"][name][version]:
            raise ValueError(f"Environment changed: {name}/{version}")
        for key in REFERENCE_FIELDS:
            if current[version].get(key) != saved["reference"].get(key):
                raise ValueError(f"Cached reference changed: {name}/{version}/{key}")


def _cell_spec(base_record, request, pack, config):
    return {"initial_result_sha256": fingerprint(base_record), "initial_request_sha256": fingerprint(request),
            "input_sha256": fingerprint(pack), "max_rounds": config["max_rounds"], "timeout": config["timeout"],
            "system_sha256": config["system_sha256"],
            "implementation_sha256": {p: config["code_sha256"][p] for p in FROZEN_REPAIR_FILES}}


def reuse_completed_cell(destination, sources, key, expected):
    """Never overwrite a destination or consume partial pilot attempts."""
    destination = Path(destination)
    if destination.exists():
        return None
    for source in sources:
        folder = Path(source) / "cells" / key
        if not (folder / "result.json").exists():
            continue
        if not (folder / "cell_config.json").exists() or read(folder / "cell_config.json") != expected:
            raise ValueError("Completed pilot cell configuration mismatch: " + str(folder))
        if fingerprint(read(folder / "initial_result.json")) != expected["initial_result_sha256"]:
            raise ValueError("Completed pilot initial evidence changed: " + str(folder))
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".reuse-", dir=destination.parent))
        try:
            shutil.copytree(folder, temporary / "cell")
            # The matrix-wide lock is held; no worker has this cell yet.
            if destination.exists():
                return None
            (temporary / "cell").rename(destination)
        finally:
            shutil.rmtree(temporary)
        return {"source_directory": str(folder.resolve()), "result_sha256": digest(destination / "result.json")}
    return None


def _validate(args):
    if type(args.max_rounds) is not int or not 0 <= args.max_rounds <= 3:
        raise ValueError("Use 0–3 correctness-only repair rounds")
    if type(args.per_model) is not int or args.per_model < 1:
        raise ValueError("per_model must be a positive integer")
    for label in ("timeout", "poll_seconds"):
        value = getattr(args, label)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(label + " must be finite and positive")
    if args.poll_seconds > 60:
        raise ValueError("poll_seconds must be at most 60")


def prepare(args):
    """Freeze the complete registered matrix before considering any outcome."""
    _validate(args)
    base, output = Path(args.input).resolve(), Path(args.output).resolve()
    if output == base or output in base.parents or base in output.parents:
        raise ValueError("Output must be separate from the base run")
    if any(not Path(path).is_dir() for path in args.reuse):
        raise ValueError("Every reuse directory must exist")
    config = read(base / "config.json")
    for dimension in ("names", "models", "arms"):
        values = config[dimension]
        if not values or len(set(values)) != len(values):
            raise ValueError("Base matrix dimensions must be nonempty and unique")
    for path, expected in config["code_sha256"].items():
        if digest(ROOT / path) != expected:
            raise ValueError("Frozen base implementation changed: " + path)
    if digest(args.dataset) != config["dataset_sha256"] or digest(args.environments) != config["environment_config_sha256"]:
        raise ValueError("Base dataset or environment configuration changed")
    packs, files = {}, {}
    for path in sorted((base / "inputs").glob("*.json")):
        pack = read(path)
        if pack["name"] in packs:
            raise ValueError("Duplicate prepared input")
        packs[pack["name"]] = pack
        files[str(path.relative_to(base))] = digest(path)
    hashes = read(base / "input_hashes.json")
    if set(packs) != set(config["names"]) or set(hashes) != set(packs):
        raise ValueError("Prepared input cohort differs from the base matrix")
    if any(fingerprint(pack) != hashes[name] for name, pack in packs.items()):
        raise ValueError("Frozen prepared input changed")
    index = read(base / "cell_index.json")
    expected = {(name, arm, model) for name in config["names"] for arm in config["arms"] for model in config["models"]}
    parsed = {tuple(json.loads(logical)): key for logical, key in index.items()}
    if set(parsed) != expected or len(set(parsed.values())) != len(expected):
        raise ValueError("Base cell index is not the full declared matrix")
    cells = [{"key": parsed[(name, arm, model)], "logical": [name, arm, model]}
             for name in config["names"] for arm in config["arms"] for model in config["models"]]
    if any(not isinstance(cell["key"], str) or len(cell["key"]) != 64
           or set(cell["key"]) - set("0123456789abcdef") for cell in cells):
        raise ValueError("Invalid base request key")
    matrix = {"schema_version": 1, "base_directory": str(base), "base_config_sha256": digest(base / "config.json"),
        "base_index_sha256": digest(base / "cell_index.json"), "base_input_hashes_sha256": digest(base / "input_hashes.json"),
        "base_names": config["names"], "models": config["models"], "arms": config["arms"], "cells": cells,
        "input_sha256": hashes, "input_files_sha256": files,
        "max_rounds": args.max_rounds, "timeout": args.timeout, "per_model": args.per_model,
        "poll_seconds": args.poll_seconds, "system_sha256": fingerprint(SYSTEM),
        "code_sha256": {path: digest(ROOT / path) for path in IMPLEMENTATION_FILES},
        "reuse_directories": [str(Path(path).resolve()) for path in args.reuse],
        "protocol": "Full registered matrix; one saved initial proposal plus at most three correctness-only repairs; no initial regeneration or score feedback."}
    return base, output, config, matrix, packs


def snapshot_cell(base, cell, pack):
    folder = base / "cells" / cell["key"]
    path = folder / "result.json"
    if not path.exists():
        return None
    record, request = read(path), read(folder / "request.json")
    payload = {key: value for key, value in request.items() if key not in ("name", "arm", "request_sha256")}
    if (fingerprint(payload) != cell["key"] or request["request_sha256"] != cell["key"]
            or record["request_sha256"] != cell["key"]
            or [request["name"], request["arm"], request["model"]] != cell["logical"]
            or [record["name"], record["arm"], record["model"]] != cell["logical"]):
        raise ValueError("Initial cell identity changed: " + cell["key"])
    return {**cell, "result_sha256": digest(path), "request_sha256": digest(folder / "request.json"),
            "input_sha256": fingerprint(pack)}


def final_config(matrix, snapshots):
    if set(snapshots) != {cell["key"] for cell in matrix["cells"]}:
        return None
    return {"schema_version": 1, "base_directory": matrix["base_directory"],
        "base_config_sha256": matrix["base_config_sha256"], "base_names": matrix["base_names"],
        "cells": [snapshots[cell["key"]] for cell in matrix["cells"]],
        "max_rounds": matrix["max_rounds"], "timeout": matrix["timeout"],
        "system_sha256": matrix["system_sha256"], "code_sha256": matrix["code_sha256"],
        "protocol": matrix["protocol"]}


def publish(output, matrix, snapshots, records, reused, active, status, base_status):
    expected = len(matrix["cells"])
    summary = {"status": status, "recorded_cells": len(records), "planned_cells": expected,
        "initial_arrived_cells": len(snapshots), "pending_initial_cells": expected - len(snapshots),
        "pending_repair_cells": len(snapshots) - len(records) - len(active), "active_cells": len(active),
        "base_run_status": base_status, "max_repair_rounds": matrix["max_rounds"],
        "per_model_concurrency": matrix["per_model"], "reused_cells": len(reused),
        "initial_valid": sum(r["initial_valid"] for r in records.values()),
        "final_valid": sum(r["final_valid"] for r in records.values()),
        "repaired_valid": sum(r["outcome"] == "repaired_valid" for r in records.values()),
        "returned_incumbent": sum(r["returned_incumbent"] for r in records.values()),
        "accepted_improvements": sum(r["accepted"] for r in records.values()),
        "repair_requests": sum(r["round_count"] for r in records.values()),
        "repair_request_count_note": "Completed cells only; includes reused pilot requests. In-flight cell requests remain in per-round artifacts.",
        "scope": matrix["protocol"]}
    write_json(output / "summary.json", summary)
    write_json(output / "arrivals.json", {"cells": snapshots, "reused_cells": reused})
    lines = ["# Full-matrix correctness-only repair", "",
        f"**{status}**: {len(records)}/{expected} cells complete; {len(snapshots)}/{expected} initial proposals available.", "",
        "The full model × context × theorem cohort was declared before repair outcomes. Each cell reuses its original proposal and receives at most three correctness-only repair requests. Empty original responses are not regenerated. The first proof passing every required version stops repair, irrespective of score.", "",
        f"Additional repair concurrency is capped at {matrix['per_model']} per model. {len(reused)} completed pilot cells were reused without new sampling. The original one-shot run remains unchanged.", "",
        "Cached references and pinned inputs are checked before each repair. Missing initial results remain pending while the base run is running; a terminal partial base run leaves this matrix resumable and incomplete.", "",
        "Final score comparisons are reported separately in [README.md](README.md). This progress summary is not a full-cohort score. See `matrix_config.json` for the complete declared cohort and `arrivals.json` for received initial-result hashes.", ""]
    (output / "RUN_STATUS.md").write_text("\n".join(lines))
    return summary


def run(args, *, evaluator=None, client=None, sleep=time.sleep):
    base, output, base_config, matrix, packs = prepare(args)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config_path = output / "matrix_config.json"
        if config_path.exists() and read(config_path) != matrix:
            raise ValueError("Matrix configuration changed; use a new output directory")
        write_json(config_path, matrix)
        evaluator = evaluator or Evaluator(args.dataset, args.environments, args.cache)
        for pack in packs.values():
            check_references(evaluator, pack, base_config)
        client = client or RCPClient(env_path=ROOT / ".env", timeout=args.timeout)
        saved = read(output / "arrivals.json") if (output / "arrivals.json").exists() else {}
        snapshots, reused = saved.get("cells", {}), saved.get("reused_cells", {})
        records, active, submitted = {}, {}, set()
        run_record = {"status": "running", "started_at": now(), "planned_cells": len(matrix["cells"])}
        write_json(output / "run.json", run_record)

        def work(cell):
            key, name = cell["key"], cell["logical"][0]
            pack = packs[name]
            if any(digest(ROOT / path) != expected for path, expected in matrix["code_sha256"].items()):
                raise ValueError("Repair implementation changed during the matrix run")
            check_references(evaluator, pack, base_config)
            if snapshot_cell(base, cell, pack) != snapshots[key]:
                raise ValueError("Initial cell changed before repair: " + key)
            folder = base / "cells" / key
            return repair_cell(base_record=read(folder / "result.json"), base_request=read(folder / "request.json"),
                pack=pack, folder=output / "cells" / key, client=client, evaluator=evaluator,
                max_rounds=args.max_rounds, timeout=args.timeout)

        try:
            with ThreadPoolExecutor(max_workers=len(matrix["models"]) * args.per_model) as pool:
                while True:
                    for cell in matrix["cells"]:
                        key, name = cell["key"], cell["logical"][0]
                        current = snapshot_cell(base, cell, packs[name])
                        if key in snapshots and current != snapshots[key]:
                            raise ValueError("Saved initial cell snapshot changed: " + key)
                        if current is None:
                            continue
                        snapshot_path = output / "initial_snapshots" / (key + ".json")
                        if snapshot_path.exists() and read(snapshot_path) != current:
                            raise ValueError("Durable initial snapshot changed: " + key)
                        if not snapshot_path.exists():
                            snapshot_path.parent.mkdir(exist_ok=True)
                            write_json(snapshot_path, current)
                        snapshots[key] = current
                        if key in submitted:
                            continue
                        folder = output / "cells" / key
                        base_folder = base / "cells" / key
                        expected = _cell_spec(read(base_folder / "result.json"), read(base_folder / "request.json"), packs[name], matrix)
                        copied = reuse_completed_cell(folder, matrix["reuse_directories"], key, expected)
                        if copied is not None:
                            reused[key] = copied
                        if (folder / "result.json").exists():
                            if read(folder / "cell_config.json") != expected:
                                raise ValueError("Completed repair cell configuration changed: " + key)
                            records[key] = read(folder / "result.json")
                            submitted.add(key)
                    complete_config = final_config(matrix, snapshots)
                    if complete_config is not None:
                        path = output / "config.json"
                        if path.exists() and read(path) != complete_config:
                            raise ValueError("Final repair configuration changed")
                        write_json(path, complete_config)
                    model_active = Counter(cell["logical"][2] for cell in active.values())
                    for cell in matrix["cells"]:
                        key, model = cell["key"], cell["logical"][2]
                        if key not in snapshots or key in submitted or model_active[model] >= args.per_model:
                            continue
                        active[pool.submit(work, cell)] = cell
                        submitted.add(key)
                        model_active[model] += 1
                    base_status = read(base / "run.json").get("status") if (base / "run.json").exists() else "unknown"
                    if len(records) == len(matrix["cells"]):
                        status = "complete"
                    elif not active and len(snapshots) < len(matrix["cells"]) and base_status != "running":
                        status = "incomplete_base_terminal"
                    else:
                        status = "running" if active else "waiting_for_initial_results"
                    summary = publish(output, matrix, snapshots, records, reused, active, status, base_status)
                    run_record.update(status=status, updated_at=now(), recorded_cells=len(records),
                        initial_arrived_cells=len(snapshots), active_cell_keys=[cell["key"] for cell in active.values()],
                        base_run_status=base_status)
                    write_json(output / "run.json", run_record)
                    if status in ("complete", "incomplete_base_terminal"):
                        return summary
                    if active:
                        done, _ = wait(active, timeout=args.poll_seconds, return_when=FIRST_COMPLETED)
                        for future in done:
                            cell = active.pop(future)
                            records[cell["key"]] = future.result()
                            print(json.dumps({"completed": cell["key"], "model": cell["logical"][2],
                                "outcome": records[cell["key"]]["outcome"]}), flush=True)
                    else:
                        sleep(args.poll_seconds)
        except BaseException as exc:
            run_record.update(status="interrupted", updated_at=now(), error_type=type(exc).__name__)
            write_json(output / "run.json", run_record)
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "results/one_shot/03_repaired_context_ablation")
    parser.add_argument("--reuse", type=Path, action="append", default=[])
    parser.add_argument("--per-model", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--poll-seconds", type=float, default=5)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/benchmark_data_warmup.jsonl")
    parser.add_argument("--environments", type=Path, default=ROOT / "environments.local.json")
    parser.add_argument("--cache", type=Path, default=ROOT / ".proof-eval")
    print(json.dumps(run(parser.parse_args(argv))))


if __name__ == "__main__":
    main()
