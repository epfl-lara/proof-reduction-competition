"""Run a resumable, score-gated deterministic ablation on the warm-up data.

Examples (from the repository root, in the af environment)::

    proof-transform --method wrappers --workers 4 \
      --input results/02_explicit_simp/candidates.jsonl --output results/03_wrappers

The output directory is locked. Repeating the exact command resumes unfinished
problems and pending alternatives; it never prepares or refreshes references.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from proof_eval import Evaluator
from proof_eval.evidence.io import digest, write_json
from proof_eval.optimization.cleanup import AllVersionsEvaluator
from proof_eval.optimization.engine import METHOD_MODULES, Budget, optimize
from proof_eval.paths import PACKAGE, ROOT

from .summary import aggregate


def now():
    return datetime.now(timezone.utc).isoformat()


def initial_proofs(evaluator, path=None):
    initial = {
        name: evaluator.dataset.get(name)["src"] for name in evaluator.dataset.names
    }
    if path is not None:
        supplied = [
            json.loads(line)
            for line in Path(path).read_text().splitlines()
            if line.strip()
        ]
        if {r["name"] for r in supplied} != set(initial) or len(supplied) != len(
            initial
        ):
            raise ValueError(
                "Input must contain exactly one proof per benchmark problem"
            )
        if any(
            not isinstance(r.get("proof"), str) or not r["proof"].strip()
            for r in supplied
        ):
            raise ValueError("Each input proof must be a nonempty string")
        initial.update({r["name"]: r["proof"] for r in supplied})
    return initial


def eligibility_checker(evaluator, row, emit, require_all_versions):
    """The evaluator the engine sees: raw, or gated on every required version.

    Without the gate, the combined score may trade a failed secondary version
    for length or heartbeat gains. With it, such candidates are never accepted.
    """
    if not require_all_versions:
        return evaluator
    required = [version for item in row["version_info"] for version in item]
    return AllVersionsEvaluator(evaluator, required, emit)


def persist_summary(output, records, proofs, names):
    temporary = output / "candidates.jsonl.tmp"
    temporary.write_text(
        "".join(
            json.dumps({"name": name, "proof": proofs[name]}, ensure_ascii=False) + "\n"
            for name in names
        )
    )
    temporary.replace(output / "candidates.jsonl")
    summary = aggregate(records, len(names))
    summary.update(
        {
            key: sum(r.get(key, 0) for r in records)
            for key in (
                "accepted_edits",
                "accepted_transitions",
                "analysis_requests",
                "lean_candidate_checks",
                "cache_hits",
            )
        }
    )
    summary["stop_reasons"] = {
        reason: sum(r["stop_reason"] == reason for r in records)
        for reason in sorted({r["stop_reason"] for r in records})
    }
    summary["version_checks_passed"] = sum(
        v.get("passed") is True
        for r in records
        for v in r["final"]["per_version"].values()
    )
    summary["version_checks_recorded"] = sum(
        len(r["final"]["per_version"]) for r in records
    )
    write_json(output / "summary.json", summary)
    return summary


def run(args):
    evaluator = Evaluator(args.dataset, args.environments, args.cache)
    names = args.name or evaluator.dataset.names
    if len(names) != len(set(names)) or set(names) - set(evaluator.dataset.names):
        raise ValueError("Problem selection contains duplicate or unknown names")
    initial = initial_proofs(evaluator, args.input)
    proofs = initial.copy()
    budget = Budget(args.max_rounds, args.max_trials, args.max_sites, args.min_gain)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / ".run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another process owns this output directory") from exc
        contexts = {}
        for name in names:
            reference = evaluator.get_reference(name)
            unavailable = [
                v
                for v, item in reference["versions"].items()
                if item.get("status") != "prepared"
            ]
            if unavailable:
                raise ValueError(
                    f"Cached references unavailable for {name}: {unavailable}; prepare separately"
                )
            row = evaluator.dataset.get(name)
            contexts[name] = {
                v: evaluator._context(row, v)[2] for v in reference["versions"]
            }
        source_paths = [
            str(path.relative_to(ROOT)) for path in sorted(PACKAGE.rglob("*.py"))
        ]
        config = {
            "schema": 1,
            "method": args.method,
            "budget": asdict(budget),
            "names": names,
            "workers": args.workers,
            "contexts": contexts,
            "dataset_sha256": digest(args.dataset),
            "input_sha256": digest(args.input) if args.input else None,
            "input_path": str(args.input) if args.input else None,
            "environment_config_sha256": digest(args.environments),
            "code_sha256": {p: digest(p) for p in sorted(set(source_paths))},
        }
        if getattr(args, "require_all_versions", False):
            # Opt-in, so historical configurations stay byte-identical.
            config["require_all_versions"] = True
        config_path = args.output / "config.json"
        if config_path.exists() and json.loads(config_path.read_text()) != config:
            raise ValueError(
                "Output has different code, inputs, environments or budgets; choose a new folder"
            )
        write_json(config_path, config)
        run_path = args.output / "run.json"
        meta = (
            json.loads(run_path.read_text())
            if run_path.exists()
            else {"started_at": now(), "sessions": []}
        )
        session = {"started_at": now()}
        meta["sessions"].append(session)
        meta["status"] = "running"
        write_json(run_path, meta)
        started = time.monotonic()

        def work(name):
            row = evaluator.dataset.get(name)
            key = hashlib.sha256(name.encode()).hexdigest()[:16]
            path = args.output / f"problem_{key}.json"
            checkpoint = args.output / f"checkpoint_{key}.json"
            if path.exists():
                return json.loads(path.read_text())
            state = json.loads(checkpoint.read_text()) if checkpoint.exists() else None
            with (args.output / f"trials_{key}.jsonl").open("a") as log:

                def emit(event):
                    log.write(
                        json.dumps(
                            {"name": name, **event}, ensure_ascii=False, allow_nan=False
                        )
                        + "\n"
                    )
                    log.flush()

                checker = eligibility_checker(
                    evaluator, row, emit, getattr(args, "require_all_versions", False)
                )
                result = optimize(
                    checker,
                    row,
                    initial[name],
                    args.method,
                    budget,
                    emit,
                    lambda state: write_json(checkpoint, state),
                    state,
                )
            write_json(path, result)
            checkpoint.unlink(missing_ok=True)
            return result

        records = []
        try:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = {pool.submit(work, name): name for name in names}
                for future in as_completed(futures):
                    result = future.result()
                    records.append(result)
                    records.sort(key=lambda r: evaluator.dataset.names.index(r["name"]))
                    proofs[result["name"]] = result["proof"]
                    persist_summary(
                        args.output, records, proofs, evaluator.dataset.names
                    )
                    print(
                        json.dumps(
                            {
                                "method": args.method,
                                "name": result["name"],
                                "changed": result["changed"],
                                "trials": result["attempts"],
                                "score": result["final"]["scores"]["combined_pct"],
                                "stop": result["stop_reason"],
                            }
                        ),
                        flush=True,
                    )
            issues = [
                r["name"]
                for r in records
                if r["stop_reason"]
                in {"initial_evaluation_incomplete_or_failed", "discovery_unavailable"}
            ]
            meta.update(
                status="finished_with_unavailable" if issues else "finished",
                unavailable_names=issues,
            )
        except BaseException as exc:
            meta.update(status="interrupted", error=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            session.update(
                finished_at=now(), elapsed_seconds=round(time.monotonic() - started, 3)
            )
            meta["finished_at"] = session["finished_at"]
            write_json(run_path, meta)
        return 2 if issues else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=tuple(METHOD_MODULES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--dataset", default="data/benchmark_data_warmup.jsonl")
    parser.add_argument("--environments", default="environments.local.json")
    parser.add_argument("--cache", default=".proof-eval")
    parser.add_argument("--name", action="append")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-rounds", type=int, default=6)
    parser.add_argument("--max-trials", type=int, default=64)
    parser.add_argument("--max-sites", type=int, default=6)
    parser.add_argument("--min-gain", type=float, default=0.05)
    parser.add_argument(
        "--require-all-versions",
        action="store_true",
        help="Accept only candidates that pass every required Lean version",
    )
    args = parser.parse_args()
    if (
        min(args.workers, args.max_rounds, args.max_trials, args.max_sites) < 1
        or not 0 <= args.min_gain < 100
    ):
        parser.error(
            "Positive worker/round/trial/site budgets and a finite margin in [0,100) required"
        )
    try:
        return run(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
