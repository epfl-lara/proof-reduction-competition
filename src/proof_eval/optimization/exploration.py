"""Durable model-free exploration with private caches and all-version certificates."""

from __future__ import annotations

import fcntl
import time
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint, read, sha, write_json
from proof_eval.verification.references import require_valid, score, versions

from .cleanup import COUNTERS, AllVersionsEvaluator, append_event
from .engine import optimize
from .search_graph import SearchPlan, traverse


def terminal_status(result: dict, last_event: dict) -> str:
    """Keep terminal probe timeouts distinct from failed or exhausted discovery."""
    reason = result["stop_reason"]
    if reason in {"no_new_proposals", "no_improving_proposal"}:
        return "complete"
    if reason in {"round_limit", "trial_limit"}:
        return "work_limit"
    evidence = last_event.get("discovery", {})
    if (
        reason == "discovery_unavailable"
        and last_event.get("kind") == "proposal_set"
        and evidence.get("status") == "discovery_timeout"
        and any(
            d.get("kind") == "discovery_process" and d.get("timed_out") is True
            for d in evidence.get("diagnostics", [])
        )
    ):
        return "discovery_limit"
    return "incomplete"


class _Explorer:
    def __init__(self, evaluator, row, folder, plan, initial, best_effort=False):
        self.evaluator, self.row, self.folder, self.plan = evaluator, row, folder, plan
        self.initial = initial
        self.best_effort = best_effort
        self.nodes = {p.stem: read(p) for p in (folder / "nodes").glob("*.json")}
        self.progress = read(folder / "progress.json")

    def capture(self, proof: str, evaluation: dict, parent: str, method: str) -> str:
        require_valid(evaluation, self.row, proof)
        key = sha(proof)
        if key not in self.nodes:
            node = {
                "proof": proof,
                "evaluation": evaluation,
                "parent": parent,
                "method": method,
                "elapsed_seconds": time.time() - self.progress["started_epoch"],
            }
            self.nodes[key] = node
            write_json(self.folder / "nodes" / (key + ".json"), node)
        best = self.nodes[self.progress["best"]]
        if score(evaluation) > score(best["evaluation"]) + self.plan.budget.min_gain:
            self.progress["best"] = key
            self.progress["improvements"].append(
                {
                    "node": key,
                    "method": method,
                    "elapsed_seconds": time.time() - self.progress["started_epoch"],
                    "score": score(evaluation),
                    "expansions_finished": len(self.progress["expansions"]),
                }
            )
            write_json(self.folder / "progress.json", self.progress)
        return key

    def expand(self, parent: str, method: str) -> dict:
        identity = {"parent": parent, "method": method, "plan": self.plan.record()}
        key = fingerprint(identity)
        folder = self.folder / "expansions" / key
        path = folder / "result.json"
        if path.exists():
            result = read(path)
            if result["identity"] != identity:
                raise ValueError("Expansion identity changed")
            for relative, expected in result["evidence_sha256"].items():
                if digest(folder / relative) != expected:
                    raise ValueError("Expansion evidence changed")
            self._record(key)
            return result
        if (folder / "started.json").exists():
            raise RuntimeError("Indeterminate deterministic expansion; not replayed")
        folder.mkdir(parents=True, exist_ok=True)
        write_json(
            folder / "started.json", {"identity": identity, "epoch": time.time()}
        )
        (folder / "trials.jsonl").touch()
        node = self.nodes[parent]
        adapter = AllVersionsEvaluator(
            self.evaluator,
            versions(self.row),
            lambda event: append_event(folder / "eligibility.jsonl", event),
        )
        children, last_event = [], {}

        def emit(event):
            nonlocal last_event
            last_event = event
            append_event(folder / "trials.jsonl", event)
            if event.get("kind") != "candidate" or not event.get(
                "all_versions_requested"
            ):
                return
            eligible = adapter.latest.get(sha(event["proof"]))
            if (
                eligible
                and eligible["eligible"]
                and score(eligible["evaluation"])
                > score(node["evaluation"]) + self.plan.budget.min_gain
            ):
                child = self.capture(
                    event["proof"], eligible["evaluation"], parent, method
                )
                if child not in children:
                    children.append(child)

        checkpoint = {}

        def save(state):
            checkpoint.clear()
            checkpoint.update(state)
            write_json(folder / "checkpoint.json", state)

        method_started = time.monotonic()
        try:
            result = optimize(
                adapter,
                self.row,
                node["proof"],
                method,
                self.plan.budget,
                emit,
                save,
            )
        except Exception as error:
            if not self.best_effort:
                raise
            # Only already certified nodes can survive a failed optional method.
            best = max(
                [parent, *children],
                key=lambda key: score(self.nodes[key]["evaluation"]),
            )
            emit(
                {
                    "kind": "method_exception",
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            result = {
                **{key: checkpoint.get(key, 0) for key in COUNTERS},
                "method": method,
                "proof": self.nodes[best]["proof"],
                "stop_reason": "method_exception",
                "error": last_event["error"],
                "elapsed_seconds": time.monotonic() - method_started,
                "counters_complete": False,
            }
        write_json(folder / "optimizer.json", result)
        best = sha(result["proof"])
        if best not in self.nodes:
            raise ValueError("Optimizer selected an uncertified state")
        record = {
            "identity": identity,
            "best": best,
            "children": children,
            "status": terminal_status(result, last_event),
            "stop_reason": result["stop_reason"],
            "input_score": score(node["evaluation"]),
            "output_score": score(self.nodes[best]["evaluation"]),
            "counters": {key: result.get(key, 0) for key in COUNTERS},
            "evidence_sha256": {
                p.name: digest(p) for p in folder.iterdir() if p.is_file()
            },
        }
        write_json(path, record)
        self._record(key)
        return record

    def _record(self, key: str) -> None:
        if key not in self.progress["expansions"]:
            self.progress["expansions"].append(key)
            write_json(self.folder / "progress.json", self.progress)


def explore(
    *,
    evaluator,
    row: dict,
    proof: str,
    evaluation: dict,
    folder: Path,
    plan: SearchPlan,
    provenance: dict,
    best_effort: bool = False,
) -> dict:
    """Run a finite search without an overall clock cap; checkpoint every gain.

    Individual verifier and discovery watchdogs are unchanged. A completed
    expansion is reused within this condition only. Indeterminate work blocks
    automatic resume; it is never silently restarted with renewed resources.
    """
    require_valid(evaluation, row, proof)
    folder.mkdir(parents=True, exist_ok=True)
    spec = {
        "schema_version": 1,
        "name": row["name"],
        "row_sha256": fingerprint(row),
        "initial": sha(proof),
        "plan": plan.record(),
        "provenance": provenance,
        **({"cleanup_failure_policy": "best_effort_verified"} if best_effort else {}),
    }
    with (folder / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        spec_path = folder / "spec.json"
        if spec_path.exists() and read(spec_path) != spec:
            raise ValueError("Deterministic search configuration changed")
        write_json(spec_path, spec)
        if (folder / "result.json").exists():
            result = read(folder / "result.json")
            verify_manifest(folder, result)
            return result
        if not (folder / "progress.json").exists():
            write_json(
                folder / "nodes" / (sha(proof) + ".json"),
                {
                    "proof": proof,
                    "evaluation": evaluation,
                    "parent": None,
                    "method": None,
                    "elapsed_seconds": 0,
                },
            )
            write_json(
                folder / "progress.json",
                {
                    "started_epoch": time.time(),
                    "best": sha(proof),
                    "expansions": [],
                    "improvements": [],
                },
            )
        engine = _Explorer(evaluator, row, folder, plan, sha(proof), best_effort)
        stop = traverse(
            sha(proof),
            plan,
            engine.expand,
            lambda key: score(engine.nodes[key]["evaluation"]),
        )
        progress = engine.progress
        records = [
            read(folder / "expansions" / key / "result.json")
            for key in progress["expansions"]
        ]
        statuses = [r["status"] for r in records]
        best = engine.nodes[progress["best"]]
        result = {
            "name": row["name"],
            "spec_sha256": digest(spec_path),
            **stop,
            "status": "incomplete" if "incomplete" in statuses else "complete",
            "best": progress["best"],
            "proof": best["proof"],
            "evaluation": best["evaluation"],
            "gain_pp": score(best["evaluation"]) - score(evaluation),
            "expansions": len(records),
            "nodes": len(engine.nodes),
            "work_limited_expansions": statuses.count("work_limit"),
            "discovery_limited_expansions": statuses.count("discovery_limit"),
            "counters": {
                key: sum(r["counters"][key] for r in records) for key in COUNTERS
            },
            "elapsed_seconds": time.time() - progress["started_epoch"],
            "artifact_sha256": {
                str(p.relative_to(folder)): digest(p)
                for p in sorted(folder.rglob("*"))
                if p.is_file() and p.name != ".lock"
            },
        }
        write_json(folder / "result.json", result)
        return result


def verify_manifest(folder: Path, result: dict) -> None:
    """Verify the sealed search evidence without compiler or model calls."""
    for relative, expected in result["artifact_sha256"].items():
        if digest(folder / relative) != expected:
            raise ValueError("Deterministic search evidence changed: " + relative)
