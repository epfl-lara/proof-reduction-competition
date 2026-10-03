"""One separately recorded effort comparison against an exact saved request.

This does not modify or resume a frozen context matrix. One call is allowed;
saved start markers prevent resampling, and all HTTP goes through the shared
admission gate. The caller must first finish the user-directed high-effort stop.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import fcntl
import json
import math
from pathlib import Path
import sys

from proof_eval import Evaluator
from proof_eval.one_shot import FIELDS, extract_declaration, fingerprint, zero_evaluation
from proof_eval.optimizer import score_improves
from proof_eval.rcp import RCPClient, map_rcp_reasoning
from run_deterministic import digest, write_json
from run_repair_matrix import check_references
from run_validity_repair import generation_once, now, required_versions
from run_with_rcp_limit import AdmissionGate, legacy_initial_alive, wrap_client
from validity_feedback import all_versions_passed


ROOT = Path(__file__).resolve().parent.parent


def read(path):
    return json.loads(Path(path).read_text())


def derive_request(saved, effort):
    """Change exactly the requested effort and its recorded provider mapping."""
    if effort not in {"low", "medium"}:
        raise ValueError("This follow-up permits only low or medium effort")
    original = {k: v for k, v in saved.items() if k not in {"name", "arm", "request_sha256"}}
    if fingerprint(original) != saved["request_sha256"]:
        raise ValueError("Source request fingerprint differs")
    if (original["reasoning"] is not True or original["reasoning_effort"] != "high"
            or original["temperature"] != 0.3 or original["max_tokens"] != 32768):
        raise ValueError("Expected the frozen high-effort, 0.3-temperature, 32K request")
    if map_rcp_reasoning(original["model"], True, "high")[1] != original["reasoning_payload"]:
        raise ValueError("Original provider mapping changed")
    request = deepcopy(original)
    request["reasoning_effort"] = effort
    request["reasoning_payload"] = map_rcp_reasoning(request["model"], True, effort)[1]
    if request["reasoning_payload"] == original["reasoning_payload"]:
        raise ValueError("Requested effort does not change the provider payload")
    return request


def evaluate_generation(generation, pack, evaluator):
    result = {"name": pack["name"], "generation": generation,
              "all_versions_passed": False, "returned_incumbent": False,
              "changed_valid_proof": False, "accepted": False,
              "selected_proof": pack["proof"], "selected_evaluation": pack["incumbent"]}
    if generation["status"] != "received":
        result["evaluation"] = {"status": "unavailable", "scores": dict.fromkeys(FIELDS), "per_version": {}}
        return result
    try:
        proof = extract_declaration(generation["content"], generation["finish_reason"])
    except ValueError as exc:
        result["evaluation"] = zero_evaluation(str(exc))
        return result
    result["extracted_proof"] = proof
    evaluation = evaluator.evaluate(pack["name"], proof, versions="all")
    result["evaluation"] = evaluation
    valid = all_versions_passed(evaluation, required_versions(pack))
    result.update(all_versions_passed=valid,
                  returned_incumbent=valid and proof.strip() == pack["proof"].strip(),
                  changed_valid_proof=valid and proof.strip() != pack["proof"].strip())
    if valid and score_improves(pack["incumbent"], evaluation, 0.05):
        result.update(accepted=True, selected_proof=proof, selected_evaluation=evaluation)
    return result


def require_stopped(path, base):
    receipt = read(path)
    if receipt.get("status") != "stopped" or not receipt.get("barrier_released_at"):
        raise ValueError("High-effort stop and barrier release are not complete")
    if read(base / "run.json").get("status") != "interrupted" or legacy_initial_alive(base):
        raise ValueError("The high-effort initial process has not stopped")
    for label in ("initial_pid", "repair_pid"):
        pid = receipt.get(label)
        if type(pid) is not int or pid <= 1 or (Path("/proc") / str(pid)).exists():
            raise ValueError("Stopped worker identity is missing or still present: " + label)
    return receipt


def run(args):
    base, output = args.input.resolve(), args.output.resolve()
    if output == base or output in base.parents or base in output.parents:
        raise ValueError("Use a separate output directory")
    if (isinstance(args.timeout, bool) or not isinstance(args.timeout, (int, float))
            or not math.isfinite(args.timeout) or args.timeout <= 0):
        raise ValueError("Timeout must be finite and positive")
    require_stopped(args.stop_receipt, base)
    source_config = read(base / "config.json")
    index = read(base / "cell_index.json")
    logical = json.dumps([args.name, args.arm, args.model])
    if logical not in index:
        raise ValueError("No matching saved source request")
    source_cell = base / "cells" / index[logical]
    source_request = read(source_cell / "request.json")
    if [source_request[k] for k in ("name", "arm", "model")] != [args.name, args.arm, args.model]:
        raise ValueError("Source cell identity differs")
    if not (source_cell / "result.json").exists():
        raise ValueError("The engineering comparison requires a recorded high-effort result")
    request = derive_request(source_request, args.reasoning_effort)
    packs = [(path, read(path)) for path in (base / "inputs").glob("*.json")]
    matches = [(path, pack) for path, pack in packs if pack["name"] == args.name]
    if len(matches) != 1:
        raise ValueError("Expected exactly one saved input pack")
    pack_path, pack = matches[0]
    if fingerprint(pack) != read(base / "input_hashes.json")[args.name]:
        raise ValueError("Saved input pack differs")
    source_files = {ROOT / path: expected for path, expected in source_config["code_sha256"].items()}
    for path in (
        "src/run_reasoning_probe.py", "src/run_with_rcp_limit.py", "src/run_validity_repair.py",
        "src/run_repair_matrix.py", "src/validity_feedback.py"):
        source_files.setdefault(ROOT / path, digest(ROOT / path))
    evidence_files = {path: digest(path) for path in (
        args.stop_receipt.resolve(), base / "config.json", base / "cell_index.json",
        base / "input_hashes.json", pack_path, source_cell / "request.json", source_cell / "result.json")}
    if (digest(args.dataset) != source_config["dataset_sha256"]
            or digest(args.environments) != source_config["environment_config_sha256"]):
        raise ValueError("Dataset or environment configuration differs")
    evidence_files.update({args.dataset.resolve(): source_config["dataset_sha256"],
                           args.environments.resolve(): source_config["environment_config_sha256"]})
    evaluator = Evaluator(args.dataset, args.environments, args.cache)

    def guard():
        if any(digest(path) != expected for path, expected in {**source_files, **evidence_files}.items()):
            raise ValueError("Pinned source or evidence changed")
        check_references(evaluator, pack, source_config)

    guard()
    config = {"schema_version": 1, "name": args.name, "arm": args.arm, "model": args.model,
              "source_directory": str(base), "source_cell_key": index[logical],
              "source_request_fingerprint": source_request["request_sha256"],
              "request_fingerprint": fingerprint(request), "request": request,
              "request_timeout_seconds": args.timeout,
              "admission_settings": {key: str(getattr(args, key).resolve()) for key in (
                  "gate", "legacy_initial", "legacy_repair", "admission")},
              "source_sha256": {str(p): h for p, h in source_files.items()},
              "evidence_sha256": {str(p): h for p, h in evidence_files.items()},
              "design": "One separate effort-only engineering comparison; exact saved messages; no retries, repair, cleanup, or performance feedback; historical high-effort comparator."}
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        target = output / "config.json"
        if target.exists() and read(target) != config:
            raise ValueError("Probe configuration changed; use a new output directory")
        write_json(target, config)
        if (output / "result.json").exists():
            return read(output / "result.json")
        run_record = {"status": "running", "started_at": now(), "planned_calls": 1}
        write_json(output / "run.json", run_record)
        try:
            guard()
            if (output / "generation.json").exists() or (output / "request_started.json").exists():
                # No HTTP or new admission invocation when recovering saved work.
                invocation = read(output / "admission.json")["invocation"] if (output / "admission.json").exists() else None
                generation = generation_once(output, request, None, args.timeout)
            else:
                gate = AdmissionGate(directory=args.gate, legacy_initial=args.legacy_initial,
                                     legacy_repair=args.legacy_repair, log_directory=args.admission)
                gate.require_initial_drained()
                invocation = gate.invocation
                write_json(output / "admission.json", {"invocation": invocation})
                write_json(args.admission / (invocation + ".command.json"),
                           {"wrapped_script": str(Path(__file__).resolve()), "wrapped_script_sha256": digest(__file__),
                            "arguments": sys.argv[1:], "wrapper_sha256": digest(ROOT / "src/run_with_rcp_limit.py"),
                            "invocation": invocation,
                            "note": "Probe directly uses the unchanged AdmissionGate and wrap_client; elapsed time includes gate waits."})
                client = RCPClient(env_path=ROOT / ".env", timeout=args.timeout)
                with wrap_client(RCPClient, gate):
                    generation = generation_once(output, request, client, args.timeout)
            guard()
            result = evaluate_generation(generation, pack, evaluator)
            guard()
            result.update(model=args.model, arm=args.arm, reasoning_effort=args.reasoning_effort,
                          request_fingerprint=fingerprint(request),
                          historical_high_result=read(source_cell / "result.json"),
                          admission_invocation=invocation, reference_guard_passed=True)
            write_json(output / "result.json", result)
            run_record.update(status="finished", finished_at=now())
            return result
        except BaseException as exc:
            run_record.update(status="interrupted", error_type=type(exc).__name__, finished_at=now())
            raise
        finally:
            write_json(output / "run.json", run_record)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stop-receipt", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--arm", default="plain")
    parser.add_argument("--model", default="Qwen/Qwen3.8-27B")
    parser.add_argument("--reasoning-effort", choices=("low", "medium"), default="medium")
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/benchmark_data_warmup.jsonl")
    parser.add_argument("--environments", type=Path, default=ROOT / "environments.local.json")
    parser.add_argument("--cache", type=Path, default=ROOT / ".proof-eval")
    parser.add_argument("--gate", type=Path, default=ROOT / ".proof-eval/rcp-admission")
    parser.add_argument("--legacy-initial", type=Path, default=ROOT / "results/one_shot/01_context_ablation")
    parser.add_argument("--legacy-repair", type=Path, default=ROOT / "results/one_shot/03_repaired_context_ablation")
    parser.add_argument("--admission", type=Path, required=True)
    result = run(parser.parse_args())
    print(json.dumps({k: result[k] for k in (
        "name", "model", "reasoning_effort", "all_versions_passed", "changed_valid_proof", "accepted")}))


if __name__ == "__main__":
    main()
