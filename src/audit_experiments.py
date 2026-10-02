"""Audit saved experiment evidence without running Lean or preparing references.

    python src/audit_experiments.py --stages results/deterministic/03_wrappers \
      --check-cache --check-code --output results/deterministic/validation/audit.json

This checks artifact consistency and score arithmetic, not kernel correctness
afresh. The saved compiler outcomes remain the source of passing-check evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from proof_eval.metrics import token_count, validate_candidate
from proof_eval.optimizer import Edit, apply_edits


TOLERANCE = 1e-8
FIELDS = ("length_reduction_pct", "heartbeat_reduction_pct", "compatibility_pct", "combined_pct")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text())


def _rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def _named(rows, expected, label):
    _require(len(rows) == len(expected), f"{label}: expected exactly {len(expected)} rows")
    names = [row["name"] for row in rows]
    _require(len(set(names)) == len(names) and set(names) == set(expected), f"{label}: missing, duplicate, or unknown names")
    return dict(zip(names, rows))


def _number(value, label):
    _require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value),
             f"{label}: expected a finite number")
    return value


def _close(actual, expected, label):
    _require(abs(_number(actual, label) - expected) <= TOLERANCE,
             f"{label}: recorded {actual!r}, recomputed {expected!r}")


def _versions(row):
    return [version for entry in row["version_info"] for version in entry]


def _implementation(relative, expected, code_root, snapshots, label):
    """Verify current bytes or an exact content-addressed historical source.

    The directory name alone is never evidence: recompute the archived file's
    SHA-256. No manifest, import, evaluation, or subprocess is involved.
    """
    _require(len(expected) == 64 and all(c in "0123456789abcdef" for c in expected),
             f"{label}: implementation hash is not a SHA-256 digest: {relative}")
    current = Path(code_root) / relative
    if current.is_file() and _digest(current) == expected:
        return {"source": relative, "sha256": expected, "verification": "current", "path": str(current)}
    archived = Path(snapshots) / expected / Path(relative).name
    if archived.is_file() and _digest(archived) == expected:
        return {"source": relative, "sha256": expected, "verification": "snapshot", "path": str(archived)}
    raise ValueError(f"{label}: implementation hash changed and no matching snapshot: {relative}")


def _proof(row, code, evaluation, label):
    normalized, body = validate_candidate(row, code)
    candidate = evaluation["candidate"]
    _require(candidate["code_sha256"] == _sha(normalized), f"{label}: normalized proof hash mismatch")
    length = token_count(body)
    _require(candidate["length"] == length, f"{label}: token count mismatch")
    return length


def _evaluation(row, baseline, code, evaluation, label):
    """Recompute fully scored successful-primary evidence, including failures elsewhere."""
    length = _proof(row, code, evaluation, label)
    versions = _versions(row)
    _require(evaluation["status"] == "passed", f"{label}: selected/accepted evaluation is not fully scored")
    _require(evaluation["primary_version"] == versions[0], f"{label}: wrong primary version")
    per_version = evaluation["per_version"]
    _require(set(per_version) == set(versions), f"{label}: required version keys differ")
    passed = 0
    for version in versions:
        item, reference = per_version[version], baseline["per_version"][version]
        prefix = f"{label}/{version}"
        _require(item["status"] in {"passed", "failed", "timeout"}, f"{prefix}: check unavailable")
        _require(item.get("passed") is (item["status"] == "passed"), f"{prefix}: passing flag disagrees with status")
        _require(item.get("environment_fingerprint") == reference["provenance"]["environment_fingerprint"],
                 f"{prefix}: environment fingerprint mismatch")
        if item["passed"]:
            passed += 1
            heartbeat = _number(item["heartbeats"], prefix + "/heartbeats")
            _require(heartbeat >= 0, f"{prefix}: negative heartbeat count")
            reduction = 100.0 * (1.0 - heartbeat / reference["heartbeats"])
            _close(item["heartbeat_reduction_pct"], reduction, prefix + "/heartbeat reduction")
    _require(per_version[versions[0]]["passed"], f"{label}: primary check did not pass")
    expected = {
        "length_reduction_pct": 100.0 * (1.0 - length / row["proof_length"]),
        "heartbeat_reduction_pct": 100.0 * (1.0 - per_version[versions[0]]["heartbeats"]
                                           / baseline["per_version"][versions[0]]["heartbeats"]),
        "compatibility_pct": 100.0 * passed / len(versions),
    }
    expected["combined_pct"] = sum(expected.values()) / 3.0
    for field in FIELDS:
        _close(evaluation["scores"][field], expected[field], label + "/" + field)
    return passed


def _input_proofs(stage, config, rows, previous):
    expected = config.get("input_sha256")
    if expected is None:
        _require(previous is None, f"{stage}: chain unexpectedly restarts from dataset originals")
        return {name: row["src"] for name, row in rows.items()}
    possibilities = []
    if previous is not None:
        possibilities.append(previous / "candidates.jsonl")
    if config.get("input_path"):
        possibilities.append(Path(config["input_path"]))
        # Historical evidence keeps its original paths after the results move.
        # Resolve the known relocation without changing recorded hashes/inputs.
        try:
            relative = Path(config["input_path"]).relative_to("results")
        except ValueError:
            pass
        else:
            possibilities.append(Path("results/deterministic") / relative)
    # Original stages did not save input_path. Resolve their recorded digest
    # among sibling stage artifacts, rather than infer a proof from its hash.
    possibilities.extend(sorted(stage.parent.glob("*/candidates.jsonl")))
    matching = next((path for path in possibilities if path.is_file() and _digest(path) == expected), None)
    _require(matching is not None, f"{stage}: no input artifact matches recorded input hash")
    if previous is not None:
        _require(_digest(previous / "candidates.jsonl") == expected, f"{stage}: stage input chain hash mismatch")
    supplied = _named(_rows(matching), rows, f"{stage}/input")
    return {name: item["proof"] for name, item in supplied.items()}


def _transitions(stage, row, baseline, record, initial, margin):
    name = row["name"]
    path = stage / ("trials_" + _sha(name)[:16] + ".jsonl")
    _require(path.exists(), f"{stage}/{name}: missing trial log")
    current, score = initial, record["initial"]["scores"]["combined_pct"]
    candidates, accepted, duplicates = {}, {}, 0
    edit_count = 0
    for event in _rows(path):
        _require(event.get("name") == name, f"{path}: event belongs to another problem")
        key = (event.get("round"), event.get("trial"))
        if event["kind"] == "candidate":
            candidates[key] = event  # A resumed pending trial can be logged again.
        elif event["kind"] == "accepted":
            if key in accepted:
                _require(event == accepted[key], f"{path}: conflicting duplicated acceptance")
                duplicates += 1
                continue
            _require(key in candidates, f"{path}: acceptance has no preceding candidate")
            candidate = candidates[key]
            _require(candidate["parent_sha256"] == _sha(current), f"{path}: accepted candidate has wrong parent")
            _require(candidate.get("all_versions_requested") is True and candidate.get("improves_incumbent") is True,
                     f"{path}: acceptance lacks full improved evaluation")
            _require(event["edits"] == candidate["edits"], f"{path}: accepted edits differ from candidate")
            edits = [Edit(**item) for item in event["edits"]]
            _require(all(0 <= e.start <= e.end <= len(current) for e in edits), f"{path}: edit outside parent proof")
            _require(apply_edits(current, edits) == candidate["proof"], f"{path}: edits do not produce candidate proof")
            _evaluation(row, baseline, candidate["proof"], candidate["evaluation"], f"{path}/accepted {key}")
            next_score = candidate["evaluation"]["scores"]["combined_pct"]
            _close(event["score"], next_score, f"{path}/accepted score")
            _require(next_score - score > margin, f"{path}: accepted gain does not exceed configured margin")
            current, score = candidate["proof"], next_score
            accepted[key] = event
            edit_count += len(edits)
    _require(current == record["proof"], f"{path}: accepted transition chain does not reach selected proof")
    _close(record["final"]["scores"]["combined_pct"], score, f"{path}/terminal score")
    _require(record["accepted_edits"] == edit_count, f"{path}: accepted-edit count mismatch")
    if "accepted_transitions" in record:
        _require(record["accepted_transitions"] == len(accepted), f"{path}: accepted-transition count mismatch")
    _require(record["changed"] is (current != initial), f"{path}: changed flag mismatch")
    return len(accepted), duplicates


def audit(stages, *, dataset="data/benchmark_data_warmup.jsonl",
          references="results/deterministic/00_reference_baseline/reference_values.jsonl",
          check_code=False, check_cache=False, cache=".proof-eval", code_root=".",
          snapshots="results/deterministic/validation/implementation_snapshots"):
    """Audit immutable artifacts. Optional cache checks only read JSON files."""
    stages = [Path(stage) for stage in stages]
    _require(stages and len({stage.resolve() for stage in stages}) == len(stages), "Provide distinct stages in execution order")
    dataset_rows = _rows(dataset)
    rows = _named(dataset_rows, [row["name"] for row in dataset_rows], "dataset")
    baseline = _named(_rows(references), rows, "reference export")
    dataset_hash = _digest(dataset)
    backend_hashes = set()
    for name, row in rows.items():
        reference = baseline[name]
        _require(reference["status"] == "prepared" and reference["dataset_sha256"] == dataset_hash,
                 f"{name}: unprepared or mismatched reference export")
        _require(reference["reference_length_tokens"] == row["proof_length"], f"{name}: reference token denominator changed")
        _require(reference["reference_code_sha256"] == _sha(row["src"]), f"{name}: reference source hash changed")
        _require(set(reference["per_version"]) == set(_versions(row)), f"{name}: reference versions differ")
        for version, item in reference["per_version"].items():
            _require(item["status"] == "prepared" and _number(item["heartbeats"], name + "/reference HB") > 0,
                     f"{name}/{version}: reference unavailable or nonpositive")
            _close(item["heartbeats_raw"] / 1000, item["heartbeats"], name + "/reference units")
            backend_hashes.add(item["provenance"]["details"]["backend_implementation_sha256"])
    _require(len(backend_hashes) == 1, "Reference export mixes measurement implementations")
    reports, previous, previous_records, contexts = [], None, None, None
    cache_checked = set()
    for stage in stages:
        config = _read(stage / "config.json")
        _require(config["dataset_sha256"] == dataset_hash, f"{stage}: dataset hash mismatch")
        _require(set(config["names"]) == set(rows) and len(config["names"]) == len(rows), f"{stage}: partial problem selection")
        _require(config["code_sha256"]["src/proof_eval/lean_backend.py"] in backend_hashes,
                 f"{stage}: baseline measurement implementation changed")
        implementation_checks = []
        if check_code:
            implementation_checks = [_implementation(relative, expected, code_root, snapshots, str(stage))
                                     for relative, expected in sorted(config["code_sha256"].items())]
        _require(set(config["contexts"]) == set(rows), f"{stage}: context problem keys differ")
        if contexts is not None:
            _require(config["contexts"] == contexts, f"{stage}: context cache identities changed across stages")
        contexts = config["contexts"]
        initial = _input_proofs(stage, config, rows, previous)
        selected = _named(_rows(stage / "candidates.jsonl"), rows, f"{stage}/candidates")
        records = _named([_read(path) for path in sorted(stage.glob("problem_*.json"))], rows, f"{stage}/records")
        margin = config.get("budget", {}).get("min_gain", config.get("min_gain_pp"))
        _require(_number(margin, str(stage) + "/margin") >= 0, f"{stage}: negative acceptance margin")
        passed = transitions = duplicate_acceptances = 0
        for name, row in rows.items():
            record = records[name]
            _require(set(contexts[name]) == set(_versions(row)), f"{stage}/{name}: context versions differ")
            _require(record["source"] == row["source"], f"{stage}/{name}: source mismatch")
            _require(selected[name]["proof"] == record["proof"], f"{stage}/{name}: selected proof differs from problem record")
            _evaluation(row, baseline[name], initial[name], record["initial"], f"{stage}/{name}/initial")
            passed += _evaluation(row, baseline[name], record["proof"], record["final"], f"{stage}/{name}/final")
            if previous_records is not None:
                prior = previous_records[name]["final"]
                _require(record["initial"]["candidate"] == prior["candidate"], f"{stage}/{name}: input candidate chain differs")
                for field in FIELDS:
                    _close(record["initial"]["scores"][field], prior["scores"][field], f"{stage}/{name}/input {field}")
            count, duplicates = _transitions(stage, row, baseline[name], record, initial[name], margin)
            transitions += count
            duplicate_acceptances += duplicates
            if check_cache:
                for version, key in contexts[name].items():
                    if key in cache_checked:
                        continue
                    cached = _read(Path(cache) / "references" / (key + ".json"))
                    exported = baseline[name]["per_version"][version]
                    _require(cached["name"] == name and cached["version"] == version and cached["status"] == "prepared",
                             f"{name}/{version}: cached reference identity/status mismatch")
                    for field in ("heartbeats", "heartbeats_raw"):
                        _close(cached[field], exported[field], f"{name}/{version}/cached {field}")
                    for field in ("environment_fingerprint", "reference_code_sha256", "measured_at", "machine"):
                        _require(cached[field] == exported["provenance"][field], f"{name}/{version}: cached reference {field} changed")
                    cache_checked.add(key)
        initial_mean = sum(record["initial"]["scores"]["combined_pct"] for record in records.values()) / len(rows)
        mean = sum(record["final"]["scores"]["combined_pct"] for record in records.values()) / len(rows)
        summary = _read(stage / "summary.json")
        _close(summary["full_benchmark_combined_pct"], mean, f"{stage}/summary combined mean")
        _close(summary["full_benchmark_delta_pp"], mean - initial_mean, f"{stage}/summary delta")
        reports.append({"stage": str(stage), "problems": len(rows), "passed_version_checks": passed,
                        "expected_version_checks": sum(len(_versions(row)) for row in rows.values()),
                        "accepted_transitions_checked": transitions, "duplicate_acceptance_events": duplicate_acceptances,
                        "combined_pct": mean, "gain_pp": mean - initial_mean,
                        "implementation_checks": implementation_checks,
                        "unavailable_discovery_names": [name for name, record in records.items()
                                                        if record.get("stop_reason") == "discovery_unavailable"]})
        previous, previous_records = stage, records
    return {"schema_version": 1, "status": "passed", "audited_at": datetime.now(timezone.utc).isoformat(),
            "tolerance": TOLERANCE, "dataset_sha256": dataset_hash, "reference_export_sha256": _digest(references),
            "code_hashes_checked": check_code, "cached_reference_records_checked": len(cache_checked),
            "stages": reports,
            "scope": "Saved-evidence consistency and score arithmetic; no new Lean verification or reference measurements."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stages", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=Path("data/benchmark_data_warmup.jsonl"))
    parser.add_argument("--references", type=Path, default=Path("results/deterministic/00_reference_baseline/reference_values.jsonl"))
    parser.add_argument("--check-code", action="store_true")
    parser.add_argument("--check-cache", action="store_true")
    parser.add_argument("--cache", type=Path, default=Path(".proof-eval"))
    parser.add_argument("--snapshots", type=Path, default=Path("results/deterministic/validation/implementation_snapshots"),
                        help="Content-addressed historical sources, used only by --check-code")
    args = parser.parse_args(argv)
    try:
        report = audit(args.stages, dataset=args.dataset, references=args.references,
                       check_code=args.check_code, check_cache=args.check_cache, cache=args.cache,
                       snapshots=args.snapshots)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        report = {"schema_version": 1, "status": "failed", "error": str(exc)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(args.output)
    print(json.dumps({"status": report["status"], "output": str(args.output), "error": report.get("error")}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
