"""Read-only diagnostic and output-budget analysis of saved one-shot artifacts.

No model calls, Lean execution, runtime imports, or reasoning text exports.
Heuristic diagnostic labels are separate from recorded authoritative statuses.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from os.path import relpath
from pathlib import Path
import re


RULES = (
    ("lean_missing_name", r"unknown (?:identifier|constant|namespace)|unknown field|invalid field (?!notation)|unknown declaration"),
    ("lean_unknown_tactic", r"unknown tactic|unknown syntax kind"),
    ("lean_type_mismatch", r"type mismatch|application type mismatch|could not unify|failed to unify|has type.*expected|function expected"),
    ("lean_unsolved_goals", r"unsolved goals"),
    ("lean_resource_limit", r"maximum.*(?:heartbeats|recursion)|(?:deterministic )?timeout|timed out|out of memory|stack overflow"),
    ("lean_syntax_error", r"unexpected token|unexpected end of input|expected token|unterminated|invalid syntax"),
    ("lean_tactic_failure", r"tactic .* failed|made no progress|no goals to be solved|failed to synthesize"),
    ("verification_rejected_sorry", r"target declaration depends on sorryax"),
    ("verification_marker_missing", r"expected exactly one verified target heartbeat marker"),
)
PRIORITY = (
    "artifact_error", "generation_truncated", "transport_error", "indeterminate_generation",
    "statement_violation", "output_contract_violation", "evaluation_unavailable",
    "lean_resource_limit", "lean_missing_name", "lean_unknown_tactic", "lean_type_mismatch",
    "lean_syntax_error", "lean_unsolved_goals", "lean_tactic_failure", "verification_rejected_sorry",
    "lean_other_failure", "verification_marker_missing", "output_invalid_other",
    "pending_evaluation", "pending_generation", "not_started",
)


def integer(value):
    return value if type(value) is int and value >= 0 else None


def object_or_empty(value):
    return value if isinstance(value, dict) else {}


def usage_summary(generation, max_tokens):
    """Only copy whitelisted numerical fields, never provider text or rationale."""
    generation = object_or_empty(generation)
    usage = object_or_empty(generation.get("usage"))
    completion = integer(usage.get("completion_tokens"))
    completion_source = "completion_tokens" if completion is not None else None
    if completion is None:
        completion = integer(usage.get("output_tokens"))
        completion_source = "output_tokens" if completion is not None else None
    details_key = "completion_tokens_details" if completion_source == "completion_tokens" else "output_tokens_details"
    reasoning = integer(object_or_empty(usage.get(details_key)).get("reasoning_tokens"))
    reasoning_source = details_key + ".reasoning_tokens" if reasoning is not None else None
    if reasoning is None:
        reasoning = integer(usage.get("reasoning_tokens"))
        reasoning_source = "reasoning_tokens" if reasoning is not None else None
    consistent = completion is not None and reasoning is not None and reasoning <= completion
    non_reasoning = completion - reasoning if consistent else None
    budget = integer(max_tokens)
    budget = budget if budget else None
    final_content = generation.get("content")
    final_characters = len(final_content) if isinstance(final_content, str) else None
    return {
        "max_output_tokens": budget,
        "prompt_tokens": integer(usage.get("prompt_tokens", usage.get("input_tokens"))),
        "completion_tokens": completion, "completion_tokens_source": completion_source,
        "reasoning_tokens": reasoning, "reasoning_tokens_source": reasoning_source,
        "non_reasoning_completion_tokens_derived": non_reasoning,
        "split_status": "available" if consistent else "inconsistent" if completion is not None and reasoning is not None else "unavailable",
        "completion_budget_fraction": completion / budget if completion is not None and budget else None,
        "reasoning_fraction_of_completion": reasoning / completion if consistent and completion else None,
        "final_content_characters": final_characters,
        "empty_final_content": not final_content.strip() if isinstance(final_content, str) else None,
        "reasoning_characters_reported": integer(generation.get("reasoning_characters")),
        "all_reported_completion_tokens_are_reasoning": completion > 0 and non_reasoning == 0 if consistent else None,
    }


def _pointer_part(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def classify(evaluation, generation, *, result_exists, generation_exists, started=False, artifact_error=False):
    """Classify actual evaluator diagnostics; labels are descriptive heuristics.

    Ignore warnings (including preexisting source-prefix sorry warnings). A
    target sorryAx rejection is evidence of failed verification, not evidence the
    model deliberately introduced an admission. Prefix/infrastructure failures
    keep their recorded unavailable status instead of being called bad proofs.
    """
    evaluation, generation = object_or_empty(evaluation), object_or_empty(generation)
    labels, evidence = set(), []
    if artifact_error:
        labels.add("artifact_error")
    if generation.get("status") == "transport_error":
        labels.add("transport_error")
    elif generation.get("status") == "indeterminate":
        labels.add("indeterminate_generation")
    if generation.get("finish_reason") == "length":
        labels.add("generation_truncated")
    for index, message in enumerate(evaluation.get("diagnostics") or []):
        text = message if isinstance(message, str) else str(object_or_empty(message).get("data", object_or_empty(message).get("message", "")))
        lower = text.lower()
        if "generation_truncated" in lower:
            label = "generation_truncated"
        elif "exact benchmark statement" in lower:
            label = "statement_violation"
        elif any(term in lower for term in (
            "empty_final_content", "ambiguous_code_fences", "query_tactic_in_final_output",
            "forbidden construct", "forbidden command", "proof body is empty", "nonempty string",
            "size limit", "unbalanced proof-body", "unterminated lean")):
            label = "output_contract_violation"
        elif evaluation.get("status") == "invalid":
            label = "output_invalid_other"
        else:
            continue
        labels.add(label)
        evidence.append({"category": label, "pointer": f"/evaluation/diagnostics/{index}"})
    versions = object_or_empty(evaluation.get("per_version"))
    for version, raw in versions.items():
        info = object_or_empty(raw)
        status = info.get("status")
        if status == "unavailable":
            labels.add("evaluation_unavailable")
            continue
        if status == "timeout":
            labels.add("lean_resource_limit")
        if status not in {"failed", "timeout"}:
            continue
        matched = False
        for index, message in enumerate(info.get("diagnostics") or []):
            if not isinstance(message, dict) or message.get("severity") != "error":
                continue
            text = str(message.get("data", message.get("message", "")))
            header = text.splitlines()[0] if text else ""
            found = [label for label, pattern in RULES if re.search(pattern, header, re.I)]
            if message.get("kind") == "Tactic.unsolvedGoals" and "lean_unsolved_goals" not in found:
                found.append("lean_unsolved_goals")
            if not found:
                found = ["lean_other_failure"]
            for label in found:
                labels.add(label)
                matched = True
                evidence.append({"category": label, "version": version,
                    "pointer": f"/evaluation/per_version/{_pointer_part(version)}/diagnostics/{index}"})
        if not matched and status == "failed":
            labels.add("lean_other_failure")
    if evaluation.get("status") in {"unavailable", "incomplete"}:
        labels.add("evaluation_unavailable")
    if evaluation.get("status") == "failed" and not versions:
        labels.add("lean_other_failure")
    if evaluation.get("status") == "invalid" and not labels:
        labels.add("output_invalid_other")
    if not result_exists:
        labels.add("pending_evaluation" if generation_exists else "pending_generation" if started else "not_started")
    elif not evaluation:
        labels.add("pending_evaluation")
    primary = next((label for label in PRIORITY if label in labels), None)
    if primary is None:
        if evaluation.get("status") == "passed":
            primary = "passed_all_observed_versions" if versions and all(v.get("passed") is True for v in versions.values()) else "passed_evaluator"
        else:
            primary = "unclassified"
    return {"primary_category": primary, "heuristic_categories": sorted(labels), "evidence": evidence}


def _read(path, issues, hashes):
    if not path.exists():
        return None
    try:
        raw = path.read_bytes()
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise TypeError("Expected an object")
        return result
    except (OSError, ValueError, TypeError) as exc:
        # Exception text may quote file contents; export only its type.
        issues.append({"path": str(path), "error_type": type(exc).__name__})
        return None


def aggregate(rows, examples=3):
    """Counts are per cell, so one multi-version error never multiplies cells."""
    category_rows = defaultdict(list)
    for row in rows:
        for category in row["heuristic_categories"]:
            category_rows[category].append(row)
    sums = {}
    for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "non_reasoning_completion_tokens_derived"):
        known = [row["usage"][key] for row in rows if row["usage"][key] is not None]
        sums[key] = {"known_cells": len(known), "unknown_cells": len(rows) - len(known),
                     "sum_known": sum(known) if known else None}
    versions = Counter()
    for row in rows:
        versions.update(info["status"] or "unknown" for info in row["authoritative"]["per_version"].values())
    return {
        "cells": len(rows), "recorded_results": sum(row["result_recorded"] for row in rows),
        "authoritative_evaluation_status_counts": dict(Counter(row["authoritative"]["evaluation_status"] or "not_recorded" for row in rows)),
        "generation_status_counts": dict(Counter(row["generation_status"] or "not_recorded" for row in rows)),
        "authoritative_version_check_status_counts": dict(versions),
        "accepted_cells": sum(row["authoritative"]["accepted"] is True for row in rows),
        "candidate_change_counts": dict(Counter(row["candidate_change"] for row in rows)),
        "unchanged_all_versions_passed_cells": sum(row["candidate_change"] == "unchanged" and row["authoritative"]["all_versions_passed"] is True for row in rows),
        "changed_all_versions_passed_cells": sum(row["candidate_change"] == "changed" and row["authoritative"]["all_versions_passed"] is True for row in rows),
        "changed_evaluator_passed_cells": sum(row["candidate_change"] == "changed" and row["authoritative"]["evaluation_status"] == "passed" for row in rows),
        "primary_category_counts": dict(Counter(row["primary_category"] for row in rows)),
        "heuristic_category_cell_counts": {key: len(value) for key, value in sorted(category_rows.items())},
        "representative_cells": {key: [{"cell_path": row["cell_path"], "name": row["name"],
            "model": row["model"], "arm": row["arm"], "source": row["source"]}
            for row in value[:examples]] for key, value in sorted(category_rows.items())},
        "token_usage": sums,
        "token_split_status_counts": dict(Counter(row["usage"]["split_status"] for row in rows)),
        "all_reasoning_completion_cells": sum(row["usage"]["all_reported_completion_tokens_are_reasoning"] is True for row in rows),
        "truncated_with_empty_final_cells": sum("generation_truncated" in row["heuristic_categories"] and row["usage"]["empty_final_content"] is True for row in rows),
    }


def analyze(input_path, examples=3):
    root = Path(input_path).resolve()
    if not root.is_dir():
        raise ValueError("Input run directory does not exist")
    if type(examples) is not int or examples < 1:
        raise ValueError("examples must be a positive integer")
    issues, hashes = [], {}
    config = _read(root / "config.json", issues, hashes) or {}
    run = _read(root / "run.json", issues, hashes) or {}
    index = _read(root / "cell_index.json", issues, hashes) or {}
    sources, incumbents = {}, {}
    for path in sorted((root / "inputs").glob("*.json")):
        pack = _read(path, issues, hashes) or {}
        row = object_or_empty(pack.get("row"))
        name = pack.get("name", row.get("name"))
        sources[name] = row.get("source")
        if isinstance(pack.get("proof"), str):
            incumbents[name] = pack["proof"]
    metadata = {}
    for raw, key in index.items():
        try:
            name, arm, model = json.loads(raw)
            if not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{64}", key):
                raise ValueError("Invalid cell key")
            metadata[key] = {"name": name, "arm": arm, "model": model}
        except (ValueError, TypeError):
            issues.append({"path": str(root / "cell_index.json"), "error_type": "invalid_cell_index_entry"})
    keys = set(metadata)
    if (root / "cells").is_dir():
        keys.update(path.name for path in (root / "cells").iterdir() if path.is_dir())
    rows = []
    for key in sorted(keys):
        folder = root / "cells" / key
        before_issues = len(issues)
        request = _read(folder / "request.json", issues, hashes) or {}
        result = _read(folder / "result.json", issues, hashes)
        generation = _read(folder / "generation.json", issues, hashes)
        embedded = object_or_empty((result or {}).get("generation"))
        if generation is not None and embedded and generation != embedded:
            issues.append({"path": str(folder), "error_type": "generation_artifacts_disagree"})
        # A completed result's embedded generation is its authoritative evidence.
        generation = embedded or generation or {}
        evaluation = object_or_empty((result or {}).get("evaluation"))
        meta = {field: (result or {}).get(field, request.get(field, metadata.get(key, {}).get(field)))
                for field in ("name", "model", "arm")}
        source = (result or {}).get("source", sources.get(meta["name"]))
        extracted = (result or {}).get("extracted_proof")
        original = incumbents.get(meta["name"])
        candidate_change = ("not_extracted" if not isinstance(extracted, str)
                            else "unknown_incumbent" if original is None
                            else "unchanged" if extracted.strip() == original.strip() else "changed")
        per_version = {version: {"status": item.get("status"), "passed": item.get("passed")}
                       for version, item in object_or_empty(evaluation.get("per_version")).items() if isinstance(item, dict)}
        row = {
            **meta, "source": source, "cell_key": key, "cell_path": str(folder),
            "result_recorded": result is not None,
            "candidate_change": candidate_change,
            "generation_status": generation.get("status"), "finish_reason": generation.get("finish_reason"),
            "authoritative": {"evaluation_status": evaluation.get("status"),
                "primary_version": evaluation.get("primary_version"), "per_version": per_version,
                "accepted": (result or {}).get("accepted"), "all_versions_passed": (result or {}).get("all_versions_passed")},
            "usage": usage_summary(generation, request.get("max_tokens", config.get("max_tokens"))),
            **classify(evaluation, generation, result_exists=result is not None,
                generation_exists=bool(generation), started=(folder / "request_started.json").exists(),
                artifact_error=len(issues) > before_issues),
        }
        rows.append(row)
    groups = {}
    for dimensions in (("source",), ("model",), ("arm",), ("model", "arm"), ("source", "model", "arm")):
        grouped = defaultdict(list)
        for row in rows:
            grouped[tuple(row.get(field) for field in dimensions)].append(row)
        groups["_".join(dimensions)] = [
            {"group": dict(zip(dimensions, key)), **aggregate(value, examples)}
            for key, value in sorted(grouped.items(), key=lambda item: repr(item[0]))]
    planned = len(config.get("names", [])) * len(config.get("models", [])) * len(config.get("arms", []))
    planned = max(planned, len(index), len(rows))
    recorded = sum(row["result_recorded"] for row in rows)
    return {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "input": str(root), "recorded_run_status": run.get("status"),
        "snapshot_status": "complete" if recorded == planned and not issues and all(row["authoritative"]["evaluation_status"] for row in rows) else "partial_or_unreadable",
        "planned_cells": planned, "observed_cell_folders": len(rows), "recorded_results": recorded,
        "missing_result_cells": planned - recorded, "unindexed_expected_cells": planned - len(rows),
        "method": "Read-only saved-artifact snapshot; no Lean or model calls. Heuristic labels can overlap and are not root-cause or correctness judgments. Statuses are copied separately from the evaluator.",
        "usage_note": "Non-reasoning completion tokens are derived only from valid provider completion and reasoning counters. They are not independently tokenized final proof tokens. Missing counters stay null; reasoning character counts are never converted to tokens. No reasoning or model text is exported.",
        "candidate_change_note": "Extracted proof compared with saved input incumbent after stripping outer whitespace only. Internal whitespace changes count as changed. Missing extraction or input remains distinct; no Lean equivalence is inferred.",
        "categories": {label: pattern for label, pattern in RULES}, "primary_category_priority": list(PRIORITY),
        "overall": aggregate(rows, examples), "groups": groups, "cells": rows,
        "artifact_issues": issues, "read_artifact_sha256": hashes,
    }


def markdown(report, output_directory=None):
    output_directory = Path(output_directory or report["input"]).resolve()
    overall = report["overall"]
    out = ["# One-shot failure analysis", "", f"Saved-artifact snapshot: **{report['recorded_results']}/{report['planned_cells']} results**, `{report['snapshot_status']}`.", "",
        "Authoritative evaluator statuses and heuristic error labels are reported separately. Multi-label counts overlap; repeated diagnostics and version failures count once per cell. No models or Lean processes were invoked.", "",
        "## Recorded evaluator outcomes", "", "| Status | Cells |", "|---|---:|"]
    out.extend(f"| {key} | {value} |" for key, value in sorted(overall["authoritative_evaluation_status_counts"].items()))
    out += ["", f"Unchanged returned incumbents passing every version: **{overall['unchanged_all_versions_passed_cells']}**. Changed outputs passing every version: **{overall['changed_all_versions_passed_cells']}**. Accepted improvements: **{overall['accepted_cells']}**.", "", report["candidate_change_note"]]
    out += ["", "## Diagnostic categories", "", "| Heuristic label | Cells | Representative cell |", "|---|---:|---|"]
    for category, count in overall["heuristic_category_cell_counts"].items():
        example = overall["representative_cells"][category][0]
        target = Path(relpath(example["cell_path"], output_directory)).as_posix()
        label = str(example["name"] or Path(example["cell_path"]).name).replace("|", "\\|").replace("]", "\\]")
        out.append(f"| {category} | {count} | [{label}](<{target}>) |")
    out += ["", "## Provider output-token accounting", "", report["usage_note"], "",
            "| Model | Cells with output count | Completion tokens | Reasoning tokens | Derived non-reasoning tokens | Truncated, empty final |", "|---|---:|---:|---:|---:|---:|"]
    for group in report["groups"]["model"]:
        usage = group["token_usage"]
        out.append(f"| {group['group']['model']} | {usage['completion_tokens']['known_cells']}/{group['cells']} | {usage['completion_tokens']['sum_known']} | {usage['reasoning_tokens']['sum_known']} | {usage['non_reasoning_completion_tokens_derived']['sum_known']} | {group['truncated_with_empty_final_cells']} |")
    out += ["", "Detailed JSON includes source/model/arm groups, per-version recorded statuses, provider counter availability, and diagnostic pointers into each original result. Target `sorryAx` rejection can follow elaboration errors; it does not establish deliberate use of `sorry`. Pending cells are not counted as invalid proofs.", ""]
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Saved one-shot run directory")
    parser.add_argument("--output", type=Path, help="Report directory; defaults to input")
    parser.add_argument("--examples", type=int, default=3, help="Representative cells per category and group")
    args = parser.parse_args(argv)
    report = analyze(args.input, args.examples)
    output = args.output or args.input
    output.mkdir(parents=True, exist_ok=True)
    for name, text in (("failure_analysis.json", json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"),
                       ("FAILURE_ANALYSIS.md", markdown(report, output))):
        path = output / name
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)
    print(json.dumps({key: report[key] for key in ("snapshot_status", "recorded_results", "planned_cells", "missing_result_cells")}))


if __name__ == "__main__":
    main()
