"""Run a paired, fixed-incumbent one-shot prompt/context ablation through RCP.

One request per cell, no automatic transport retries, repairs, or proof search.
Durable request-start markers prevent duplicate sampling after interruption.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import threading
import time

from proof_eval import Evaluator
from proof_eval.lean_backend import _source, MEASUREMENT_WRAPPER
from proof_eval.model_context import build_context
from proof_eval.one_shot import ARMS, FIELDS, build_messages, extract_declaration, fingerprint, summarize, zero_evaluation
from proof_eval.optimizer import score_improves
from proof_eval.rcp import MODELS, RCPClient, map_rcp_reasoning
from run_deterministic import digest, write_json
from run_experiments import initial_proofs


ROOT = Path(__file__).resolve().parent.parent


def now():
    return datetime.now(timezone.utc).isoformat()


def write_jsonl(path, rows):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(''.join(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n' for row in rows))
    temporary.replace(path)


def prepare(args, evaluator, proofs, names):
    folder = args.output / "inputs"
    folder.mkdir(exist_ok=True)
    def work(name):
        row, code = evaluator.dataset.get(name), proofs[name]
        reference = evaluator.get_reference(name)
        if any(v.get("status") != "prepared" for v in reference["versions"].values()):
            raise ValueError(f"Reference unavailable for {name}; prepare separately")
        path = folder / (hashlib.sha256(name.encode()).hexdigest()[:16] + ".json")
        if path.exists():
            pack = json.loads(path.read_text())
            if pack['row'] != row or pack['proof'] != code:
                raise ValueError(f"Saved input changed: {name}")
            for version, saved in pack['incumbent']['per_version'].items():
                current = reference['versions'][version]
                for key in ('measured_at', 'heartbeats', 'heartbeats_raw', 'environment_fingerprint', 'reference_code_sha256'):
                    if current[key] != saved['reference'][key]:
                        raise ValueError(f"Reference changed since input preparation: {name}/{version}/{key}")
            return name, pack
        incumbent = evaluator.evaluate(name, code)
        if incumbent["status"] != "passed" or incumbent["scores"]["combined_pct"] is None:
            raise ValueError(f"Incumbent unavailable or invalid: {name}")
        primary = incumbent["primary_version"]
        project = evaluator._context(row, primary)[0]
        source, _ = _source(row, code, project, "one_shot_context")
        prefix = source.split("\n#proof_eval_measure ", 1)[0].replace(MEASUREMENT_WRAPPER, "")
        pack = {"name": name, "row": row, "proof": code, "incumbent": incumbent,
                "source_context": prefix[-6000:], "source_excerpt_characters": min(len(prefix), 6000)}
        if any("goals" in arm for arm in args.arms):
            pack["context"] = build_context(evaluator, row, code, max_sites=6, measure_costs=True,
                                            max_goal_chars=1000, max_snippet_chars=300)
        write_json(path, pack)
        print(json.dumps({"prepared": name, "context": pack.get("context", {}).get("status", "not_requested")}), flush=True)
        return name, pack
    with ThreadPoolExecutor(max_workers=3) as pool:
        return dict(pool.map(work, names))


def publish(args, inputs, cells, models, names):
    baseline = {f: sum(inputs[n]["incumbent"]["scores"][f] for n in names) / len(names) for f in FIELDS}
    report = {"created_at": now(), "baseline_mean": baseline, "problem_count": len(names),
              "planned_cells": len(models) * len(args.arms) * len(names), "recorded_cells": len(cells), "conditions": []}
    for model in models:
        for arm in args.arms:
            records = [r for r in cells if r["model"] == model and r["arm"] == arm]
            records.sort(key=lambda r: names.index(r["name"]))
            summary = {"model": model, "arm": arm, **summarize(records, len(names), baseline)}
            report["conditions"].append(summary)
            folder = args.output / "conditions" / (model.split('/')[-1] + "__" + arm)
            folder.mkdir(parents=True, exist_ok=True)
            write_json(folder / "summary.json", summary)
            if len(records) == len(names):
                write_jsonl(folder / "selected_candidates.jsonl", [{"name": r["name"], "proof": r["selected_proof"]} for r in records])
    write_json(args.output / "summary.json", report)
    return report


def run(args):
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    evaluator = Evaluator(args.dataset, args.environments, args.cache)
    proofs = initial_proofs(evaluator, args.input)
    names = args.name or evaluator.dataset.names
    if not names or len(set(names)) != len(names) or set(names) - set(proofs):
        raise ValueError("Choose unique dataset names")
    models = args.models
    bank = json.loads(args.bank.read_text())
    system = args.system.read_text()
    source_paths = ["src/run_one_shot.py", "src/run_deterministic.py", "src/run_experiments.py"] + [
        str(p.relative_to(ROOT)) for p in sorted((ROOT / "src/proof_eval").glob("*.py"))]
    config = {"schema_version": 1, "dataset_sha256": digest(args.dataset), "input_sha256": digest(args.input),
              "environment_config_sha256": digest(args.environments), "names": names, "models": models,
              "arms": args.arms, "system_sha256": digest(args.system), "bank_sha256": digest(args.bank),
              "temperature": 0.3, "reasoning": True, "reasoning_effort": "high", "max_tokens": args.max_tokens,
              "request_timeout_seconds": args.timeout, "min_gain_pp": 0.05,
              "contexts": {n: {v: evaluator._context(evaluator.dataset.get(n), v)[2]
                               for v in evaluator.get_reference(n)["versions"]} for n in names},
              "code_sha256": {p: digest(ROOT / p) for p in source_paths},
              "design": "One independent request per model/arm/incumbent; no repairs/retries/postprocessing; incumbent fallback only after scoring."}
    with (args.output / ".run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config_path = args.output / "config.json"
        if config_path.exists() and json.loads(config_path.read_text()) != config:
            raise ValueError("Experiment configuration changed; use a new output folder")
        write_json(config_path, config)
        inputs = prepare(args, evaluator, proofs, names)
        input_hashes = {n: fingerprint(pack) for n, pack in inputs.items()}
        input_manifest = args.output / 'input_hashes.json'
        if input_manifest.exists() and json.loads(input_manifest.read_text()) != input_hashes:
            raise ValueError('Prepared input bytes changed; refusing to resample')
        write_json(input_manifest, input_hashes)
        unavailable = [n for n in names if any('goals' in a for a in args.arms) and inputs[n]['context']['status'] != 'ok']
        if unavailable:
            raise ValueError(f"Context extraction unavailable before any generation: {unavailable}")
        if args.prepare_only:
            return {"status": "prepared", "problems": len(inputs)}
        client = RCPClient(env_path=ROOT / ".env", timeout=args.timeout)
        available = client.list_models(timeout=30)
        if set(models) - set(available):
            raise ValueError("Requested models unavailable: " + str(set(models) - set(available)))
        model_slots = {model: threading.Semaphore(args.per_model) for model in models}
        evaluation_slots = threading.Semaphore(4)
        records, jobs, index = [], [], {}
        cells = args.output / "cells"
        cells.mkdir(exist_ok=True)
        # Interleave models and arms; every request reads the same immutable proof.
        for name in names:
            for arm in args.arms:
                for model in models:
                    pack = inputs[name]
                    messages = build_messages(system, pack["row"], pack["proof"], pack["incumbent"],
                                              pack["source_context"], arm, bank, pack.get("context"))
                    request = {"model": model, "messages": messages, "temperature": 0.3,
                               "reasoning": True, "reasoning_effort": "high", "max_tokens": args.max_tokens,
                               "reasoning_payload": map_rcp_reasoning(model, True, "high")[1]}
                    key = fingerprint(request)
                    index[json.dumps([name, arm, model])] = key
                    folder = cells / key
                    folder.mkdir(exist_ok=True)
                    write_json(folder / "request.json", {"name": name, "arm": arm, "request_sha256": key, **request})
                    if (folder / "result.json").exists():
                        records.append(json.loads((folder / "result.json").read_text()))
                    else:
                        jobs.append((name, arm, model, folder, request))
        index_path = args.output / 'cell_index.json'
        if index_path.exists() and json.loads(index_path.read_text()) != index:
            raise ValueError('A cell request changed since this experiment started; refusing to resample')
        write_json(index_path, index)
        if args.max_calls is not None:
            jobs = jobs[:args.max_calls]
        run_record = {"status": "running", "started_at": now(), "scheduled_cells": len(jobs), "existing_cells": len(records)}
        write_json(args.output / "run.json", run_record)

        def work(job):
            name, arm, model, folder, request = job
            pack = inputs[name]
            record = {"name": name, "source": pack["row"]["source"], "model": model, "arm": arm,
                      "request_sha256": fingerprint(request), "accepted": False, "all_versions_passed": False,
                      "selected_proof": pack["proof"], "selected_evaluation": pack["incumbent"]}
            generation_path = folder / "generation.json"
            if generation_path.exists():
                generation = json.loads(generation_path.read_text())
            elif (folder / "request_started.json").exists():
                generation = {"status": "indeterminate", "error": "Request started before interruption; not resampled"}
                write_json(generation_path, generation)
            else:
                with model_slots[model]:
                    write_json(folder / "request_started.json", {"started_at": now()})
                    started = time.monotonic()
                    try:
                        response = client.create_chat_completion(
                            messages=request["messages"], model=model, temperature=0.3, reasoning=True,
                            reasoning_effort="high", max_tokens=args.max_tokens, timeout=args.timeout)
                        generation = {"status": "received", "content": response.content,
                                      "finish_reason": response.finish_reason, "usage": response.usage,
                                      "returned_model": response.model, "response_id": response.raw.get("id"),
                                      "reasoning_characters": len(response.reasoning_content or ""),
                                      "elapsed_seconds": round(time.monotonic() - started, 3)}
                    except Exception as exc:
                        generation = {"status": "transport_error", "error": str(exc).replace(client.api_key, "[REDACTED]"),
                                      "elapsed_seconds": round(time.monotonic() - started, 3)}
                    write_json(generation_path, generation)
            record["generation"] = generation
            if generation["status"] == "received":
                try:
                    code = extract_declaration(generation["content"], generation["finish_reason"])
                    record["extracted_proof"] = code
                except ValueError as exc:
                    record["evaluation"] = zero_evaluation(str(exc))
                else:
                    with evaluation_slots:
                        record["evaluation"] = evaluator.evaluate(name, code, versions="all")
                    final = record["evaluation"]
                    record["all_versions_passed"] = (len(final["per_version"]) == len(pack["row"]["version_info"])
                                                        and all(v.get("passed") for v in final["per_version"].values()))
                    if score_improves(pack["incumbent"], final, 0.05):
                        record.update(accepted=True, selected_proof=code, selected_evaluation=final)
            else:
                record["evaluation"] = {"status": "unavailable", "scores": dict.fromkeys(FIELDS, None), "per_version": {}}
            write_json(folder / "result.json", record)
            print(json.dumps({"model": model, "arm": arm, "name": name, "generation": generation['status'],
                              "status": record['evaluation']['status'], "accepted": record['accepted'],
                              "score": record['evaluation']['scores']['combined_pct']}), flush=True)
            return record
        try:
            with ThreadPoolExecutor(max_workers=len(models) * args.per_model) as pool:
                for future in as_completed([pool.submit(work, job) for job in jobs]):
                    records.append(future.result())
                    publish(args, inputs, records, models, names)
            summary = publish(args, inputs, records, models, names)
            run_record.update(status="finished" if len(records) == summary['planned_cells'] else "paused_at_call_budget",
                              finished_at=now(), recorded_cells=len(records))
            return summary
        except BaseException as exc:
            run_record.update(status="interrupted", error=str(exc))
            raise
        finally:
            write_json(args.output / "run.json", run_record)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/benchmark_data_warmup.jsonl")
    parser.add_argument("--input", type=Path, default=ROOT / "results/deterministic/selected_candidates.jsonl")
    parser.add_argument("--environments", type=Path, default=ROOT / "environments.local.json")
    parser.add_argument("--cache", type=Path, default=ROOT / ".proof-eval")
    parser.add_argument("--bank", type=Path, default=ROOT / "prompts/strategy_bank.json")
    parser.add_argument("--system", type=Path, default=ROOT / "prompts/one_shot_system.md")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name", action="append")
    parser.add_argument("--models", nargs='+', default=list(MODELS.values())[:3])
    parser.add_argument("--arms", choices=ARMS, nargs='+', default=list(ARMS))
    parser.add_argument("--per-model", type=int, default=2)
    parser.add_argument("--max-tokens", type=int, default=32768)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.per_model < 1 or args.max_tokens < 1 or args.timeout <= 0 or (args.max_calls is not None and args.max_calls < 1):
        parser.error("Budgets must be positive")
    if len(set(args.models)) != len(args.models) or len(set(args.arms)) != len(args.arms):
        parser.error("Models and arms must be unique")
    result = run(args)
    print(json.dumps({k: result[k] for k in result if k != 'conditions'}), flush=True)


if __name__ == "__main__":
    main()
