"""Report saved deterministic experiments without running Lean or modifying evidence.

One-stage usage: --stage results/03_wrappers --previous results/02_explicit_simp
Comparison usage: --stages results/01_linter_deletion results/02_explicit_simp ...
The original control is stage 01's measured initial state, not an idealized 33.333.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path

FIELDS = (
    "length_reduction_pct",
    "heartbeat_reduction_pct",
    "compatibility_pct",
    "combined_pct",
)
LABELS = ("Token reduction", "Heartbeat reduction", "Compatibility", "Combined")
METHODS = {
    "lint": "Delete tactics nominated by Lean's unused/unreachable-tactic linters.",
    "simp": "Replace existing simplifier calls with compiler-suggested explicit lemma sets.",
    "wrappers": "Contract local return wrappers using parsed syntax spans.",
    "facts": "Try deleting local facts, then recheck the complete declaration.",
    "reuse": "Try reusing an existing local fact instead of proving it again.",
    "menu": "Try the fixed goal-closing tactic menu at selected parsed sites.",
    "search": "Ask deterministic Lean search tactics for explicit proof suggestions.",
    "simp_min": "Remove chunks and individual arguments from explicit simplifier lists.",
    "arith_min": "Remove chunks and individual arithmetic hints while preserving tactic controls.",
    "rw_min": "Remove rewrite-list entries while preserving the order of retained rewrites.",
}


def _json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def _records(directory):
    out = {}
    for path in sorted(Path(directory).glob("problem_*.json")):
        item = _json(path)
        if item["name"] in out:
            raise ValueError(f"Duplicate problem {item['name']} in {directory}")
        out[item["name"]] = item
    return out


def _dataset(path):
    rows = [
        json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()
    ]
    if len({row["name"] for row in rows}) != len(rows):
        raise ValueError("Duplicate dataset problem names")
    return rows


def _score(evaluation, field):
    value = evaluation.get("scores", {}).get(field)
    if value is not None and (
        not isinstance(value, (int, float)) or not math.isfinite(value)
    ):
        raise ValueError("Scores must be finite numbers or null")
    return value


def _means(evaluations):
    values = list(evaluations)
    if not values:
        return {field: None for field in FIELDS}
    return {
        field: (
            sum(_score(v, field) for v in values) / len(values)
            if all(_score(v, field) is not None for v in values)
            else None
        )
        for field in FIELDS
    }


def _delta(after, before):
    return {
        f: (
            after[f] - before[f]
            if after[f] is not None and before[f] is not None
            else None
        )
        for f in FIELDS
    }


def _complete(evaluation):
    return evaluation.get("status") in {"passed", "failed", "invalid"} and all(
        _score(evaluation, f) is not None for f in FIELDS
    )


def _original(baseline, names):
    records = _records(baseline)
    if set(records) != set(names) or not all(
        _complete(r["initial"]) for r in records.values()
    ):
        return {f: None for f in FIELDS}
    return _means(r["initial"] for r in records.values())


def _stage_path(stage):
    """Keep nested sweep identity in a normalized working-directory-relative path."""
    return Path(os.path.relpath(Path(stage).resolve(), Path.cwd())).as_posix()


def _wall_seconds(stage):
    """Sum recorded session durations; do not substitute overlapping worker time."""
    sessions = _json(stage / "run.json", {}).get("sessions")
    if not isinstance(sessions, list) or not sessions:
        return None
    durations = [session.get("elapsed_seconds") for session in sessions]
    if not all(
        isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
        for value in durations
    ):
        return None
    return round(sum(durations), 6)


def _candidate_outcome(event):
    """Separate proof failure from deliberate primary-score-bound pruning."""
    evaluation = event.get("evaluation", {})
    status = evaluation.get("status")
    primary = evaluation.get("per_version", {}).get(
        evaluation.get("primary_version"), {}
    )
    if status == "invalid":
        return "invalid_candidate"
    if primary.get("status") == "timeout":
        return "primary_timeout"
    if status == "failed" or primary.get("status") == "failed":
        return "primary_failed"
    if event.get("all_versions_requested") is False:
        if (
            primary.get("status") == "passed"
            and event.get("primary_upper_bound") is not None
        ):
            return "primary_bound_pruned"
        return "primary_evaluation_unavailable_or_unscored"
    if (
        status == "passed"
        and evaluation.get("scores", {}).get("combined_pct") is not None
    ):
        return (
            "fully_scored_improvement"
            if event.get("improves_incumbent")
            else "fully_scored_no_improvement"
        )
    return "full_evaluation_unavailable_or_unscored"


def _trial_statistics(stage, rows):
    sources = {row["name"]: row["source"] for row in rows}
    events, candidate_statuses, candidate_outcomes = Counter(), Counter(), Counter()
    tactic_statuses, discovery_statuses, errors = Counter(), Counter(), Counter()
    by_tactic, by_source = {}, {}
    screened = 0
    for path in sorted(stage.glob("trials_*.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            kind = event.get("kind", "unspecified")
            events[kind] += 1
            if kind in {"analysis_error", "discovery_error", "proposal_error"}:
                errors["event:" + kind] += 1
            if kind == "candidate":
                candidate_statuses[
                    event.get("evaluation", {}).get("status", "unspecified")
                ] += 1
                candidate_outcomes[_candidate_outcome(event)] += 1
                screened += event.get("all_versions_requested") is False
            if kind != "proposal_set":
                continue
            discovery = event.get("discovery", {})
            if "status" in discovery:
                discovery_statuses[discovery["status"]] += 1
            for diagnostic in discovery.get("diagnostics", []):
                dkind = diagnostic.get("kind", "unspecified")
                if dkind in {"analysis_error", "discovery_error", "proposal_error"}:
                    errors["diagnostic:" + dkind] += 1
                if dkind == "tactic_outcome":
                    status = diagnostic.get("status", "unspecified")
                    tactic_statuses[status] += 1
                    by_tactic.setdefault(
                        diagnostic.get("tactic", "unspecified"), Counter()
                    )[status] += 1
                    by_source.setdefault(
                        sources.get(event.get("name"), "unspecified"), Counter()
                    )[status] += 1

    def sort(c):
        return dict(sorted(c.items()))

    return {
        "trial_events": sort(events),
        "primary_screened_events": screened,
        "candidate_status_counts": sort(candidate_statuses),
        "candidate_outcome_counts": sort(candidate_outcomes),
        "tactic_outcome_status_counts": sort(tactic_statuses),
        "tactic_outcomes_by_tactic": {
            key: sort(value) for key, value in sorted(by_tactic.items())
        },
        "tactic_outcomes_by_source": {
            key: sort(value) for key, value in sorted(by_source.items())
        },
        "discovery_status_counts": sort(discovery_statuses),
        "proposal_error_count": sum(errors.values()),
        "proposal_error_counts_by_kind": sort(errors),
    }


def _accepted_example(
    stage, records, previous_records, rows, config, max_characters=800
):
    """Return a compact, verified single-edit example from an accepted transition.

    Competing candidates can improve their incumbent without being selected.
    Only an explicit accepted event qualifies, and its reported gain covers
    the full edited declaration. Larger or multi-edit changes are omitted.
    """
    initial_codes = {}

    def add_code(name, code):
        if isinstance(code, str):
            initial_codes.setdefault(name, {})[
                hashlib.sha256(code.encode()).hexdigest()
            ] = code

    for row in rows:
        add_code(row["name"], row.get("src"))
    for name, record in previous_records.items():
        add_code(name, record.get("proof"))
    input_path = config.get("input_path")
    if input_path and Path(input_path).is_file():
        for line in Path(input_path).read_text().splitlines():
            if line.strip():
                item = json.loads(line)
                add_code(item["name"], item.get("proof"))
    examples = []
    for path in sorted(stage.glob("trials_*.jsonl")):
        parents, candidates = {}, {}
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            name = event.get("name")
            record = records.get(name)
            if record is None:
                continue
            initial = record["initial"]
            initial_sha = initial.get("candidate", {}).get("code_sha256")
            initial_code = initial_codes.get(name, {}).get(initial_sha)
            if initial_code is not None and initial_sha not in parents:
                parents[initial_sha] = (initial_code, _score(initial, "combined_pct"))
            if event.get("kind") == "candidate":
                candidate_code = event.get("proof")
                if not isinstance(candidate_code, str):
                    continue
                candidates[event.get("trial")] = event
                candidate_sha = hashlib.sha256(candidate_code.encode()).hexdigest()
                parents[candidate_sha] = (
                    candidate_code,
                    _score(event.get("evaluation", {}), "combined_pct"),
                )
            elif event.get("kind") == "accepted":
                candidate = candidates.get(event.get("trial"), {})
                parent = parents.get(candidate.get("parent_sha256"))
                edits = candidate.get("edits", [])
                if parent is None or len(edits) != 1:
                    continue
                code, before_score = parent
                edit = edits[0]
                start, end, after = (
                    edit.get("start"),
                    edit.get("end"),
                    edit.get("replacement"),
                )
                if (
                    not isinstance(start, int)
                    or not isinstance(end, int)
                    or not isinstance(after, str)
                    or not 0 <= start <= end <= len(code)
                ):
                    continue
                before = code[start:end]
                if len(before) + len(after) > max_characters:
                    continue
                if code[:start] + after + code[end:] != candidate.get("proof"):
                    continue
                after_score = _score(candidate.get("evaluation", {}), "combined_pct")
                if (
                    before_score is None
                    or after_score is None
                    or after_score <= before_score
                ):
                    continue
                examples.append(
                    {
                        "name": name,
                        "trial": event.get("trial"),
                        "round": event.get("round"),
                        "log_file": path.name,
                        "edit_count": 1,
                        "reason": edit.get("reason"),
                        "start_column": start - (code.rfind("\n", 0, start) + 1),
                        "before": before,
                        "after": after,
                        "snippets_truncated": False,
                        "initial_combined_pct": before_score,
                        "final_combined_pct": after_score,
                        "combined_gain_pp": after_score - before_score,
                        "gain_scope": "complete candidate declaration; one accepted edit",
                    }
                )
    return max(examples, key=lambda e: e["combined_gain_pp"], default=None)


def stage_report(
    stage, previous=None, *, dataset="data/benchmark_data_warmup.jsonl", baseline=None
):
    """Return auditable aggregates from per-problem records, including partial runs."""
    stage = Path(stage)
    baseline = Path(baseline) if baseline else stage.parent / "01_linter_deletion"
    rows = _dataset(dataset)
    names = {row["name"] for row in rows}
    records = _records(stage)
    config = _json(stage / "config.json", {})
    digest = hashlib.sha256(Path(dataset).read_bytes()).hexdigest()
    if config.get("dataset_sha256", digest) != digest:
        raise ValueError(f"Dataset fingerprint does not match {stage}")
    if set(records) - names:
        raise ValueError(
            f"Unexpected problems in {stage}: {sorted(set(records) - names)}"
        )
    previous_records = _records(previous) if previous is not None else {}
    for name in records.keys() & previous_records.keys():
        before = records[name]["initial"].get("candidate", {}).get("code_sha256")
        prior = previous_records[name]["final"].get("candidate", {}).get("code_sha256")
        if before is not None and prior is not None and before != prior:
            raise ValueError(
                f"Stage input for {name} differs from selected previous-stage proof"
            )
    row_by_name = {row["name"]: row for row in rows}

    def fully_scored(name, evaluation):
        if not _complete(evaluation):
            return False
        # A failed/invalid primary legitimately receives zero without further
        # checks. A successful proof's compatibility requires every version.
        if evaluation["status"] != "passed":
            return True
        versions = [v for item in row_by_name[name]["version_info"] for v in item]
        return all(
            evaluation.get("per_version", {}).get(v, {}).get("status")
            in {"passed", "failed", "timeout"}
            for v in versions
        )

    complete_names = [
        name for name, r in records.items() if fully_scored(name, r["final"])
    ]
    complete = set(complete_names) == names
    final_mean = _means(records[n]["final"] for n in complete_names)
    initial_mean = _means(records[n]["initial"] for n in complete_names)
    final_full = final_mean if complete else {f: None for f in FIELDS}
    initial_full = initial_mean if complete else {f: None for f in FIELDS}
    previous_full = (
        _means(r["final"] for r in previous_records.values())
        if set(previous_records) == names
        and all(fully_scored(n, r["final"]) for n, r in previous_records.items())
        else {f: None for f in FIELDS}
    )
    original_mean = _original(baseline, names)
    checks = Counter()
    for row in rows:
        versions = [v for item in row["version_info"] for v in item]
        selected = records.get(row["name"], {}).get("final", {}).get("per_version", {})
        for version in versions:
            checks[selected.get(version, {}).get("status", "missing")] += 1
    stops = Counter(r.get("stop_reason", "unspecified") for r in records.values())
    counters = {}
    for key in (
        "attempts",
        "rounds",
        "accepted_edits",
        "accepted_transitions",
        "analysis_requests",
        "lean_candidate_checks",
        "cache_hits",
        "elapsed_seconds",
    ):
        counters[key] = (
            sum(r[key] for r in records.values())
            if records and all(key in r for r in records.values())
            else None
        )
    counters["wall_seconds"] = _wall_seconds(stage)
    trial_statistics = _trial_statistics(stage, rows)
    accepted_example = _accepted_example(stage, records, previous_records, rows, config)
    per_problem = []
    for row in rows:
        record = records.get(row["name"])
        if record is None:
            continue
        after, before = record["final"], record["initial"]
        per_problem.append(
            {
                "name": row["name"],
                "source": row["source"],
                "changed": bool(record.get("changed")),
                "initial_combined_pct": _score(before, "combined_pct"),
                "final_combined_pct": _score(after, "combined_pct"),
                "gain_pp": _delta(_means([after]), _means([before]))["combined_pct"],
                "initial_tokens": before.get("candidate", {}).get("length"),
                "final_tokens": after.get("candidate", {}).get("length"),
                "attempts": record.get("attempts"),
                "stop_reason": record.get("stop_reason"),
            }
        )
    return {
        "schema_version": 1,
        "stage": stage.name,
        "stage_path": _stage_path(stage),
        "method": config.get("method", "unknown"),
        "dataset_sha256": digest,
        "expected_problems": len(rows),
        "recorded_problems": len(records),
        "fully_scored_problems": len(complete_names),
        "complete_benchmark": complete,
        "missing_names": sorted(names - set(records)),
        "unscored_names": sorted(set(records) - set(complete_names)),
        "expected_version_checks": sum(checks.values()),
        "passed_version_checks": checks["passed"],
        "version_check_statuses": dict(sorted(checks.items())),
        "changed_problems": sum(bool(r.get("changed")) for r in records.values()),
        "measured_subset_initial_mean": initial_mean,
        "measured_subset_final_mean": final_mean,
        "full_benchmark_initial_mean": initial_full,
        "full_benchmark_final_mean": final_full,
        "original_control_mean": original_mean,
        "previous_stage_mean": previous_full,
        "delta_initial_pp": _delta(final_full, initial_full),
        "delta_previous_pp": _delta(final_full, previous_full),
        "delta_original_pp": _delta(final_full, original_mean),
        "budget": {
            key: config[key]
            for key in (
                "budget",
                "max_rounds",
                "max_trials",
                "max_sites",
                "min_gain_pp",
                "workers",
            )
            if key in config
        },
        "counters": counters,
        "stop_reasons": dict(sorted(stops.items())),
        "cap_stopped_problems": sum(
            n for reason, n in stops.items() if "limit" in reason or "budget" in reason
        ),
        **trial_statistics,
        "accepted_example": accepted_example,
        "per_problem": per_problem,
        "caveats": [
            "Local score proxy; not an arena submission result.",
            "Means average per-problem reductions; ratios of total tokens or heartbeats differ.",
            "Finite candidate, round, and site budgets do not establish a global optimum.",
            "A primary-screened trial need not have a combined score; selected outputs are reported separately.",
            "Elapsed seconds sum per-problem time, including caches and overlapping workers; this is not wall time.",
            "Wall seconds sum recorded runner-session durations, excluding gaps between resumes; incomplete timing data remain null.",
            "Candidate-check and cache counters exclude discovery/compiler-probe work; older stages may not record them.",
            "Tactic outcomes describe discovery attempts, not complete-proof validity; unavailable or unobserved tactics are not proof failures.",
            "Trial and error counts count log events or diagnostics, which can include repeated discovery after an accepted edit or resume.",
            "Sequential gains are conditional on earlier accepted stages and are not independent ablations.",
        ],
    }


def build_comparison(
    stages, *, dataset="data/benchmark_data_warmup.jsonl", baseline=None
):
    """Compare ordered successive stages; original evidence remains separate."""
    stages = [Path(p) for p in stages]
    if not stages or len({p.resolve() for p in stages}) != len(stages):
        raise ValueError("Provide distinct stages in execution order")
    baseline = Path(baseline) if baseline else stages[0].parent / "01_linter_deletion"
    reports = [
        stage_report(
            stage, stages[i - 1] if i else None, dataset=dataset, baseline=baseline
        )
        for i, stage in enumerate(stages)
    ]
    return {
        "schema_version": 1,
        "dataset_sha256": reports[0]["dataset_sha256"],
        "expected_problems": reports[0]["expected_problems"],
        "expected_version_checks": reports[0]["expected_version_checks"],
        "original_control_mean": reports[0]["original_control_mean"],
        "stages": reports,
    }
