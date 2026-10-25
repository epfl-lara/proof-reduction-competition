"""Explicit original-only reference preparation, before any training rollout."""

from __future__ import annotations

import json
import math
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

from proof_eval import Evaluator
from proof_eval.evidence.immutable import immutable, read, sha
from proof_eval.training.actions import initial_messages
from proof_eval.training.data import task_id, validate_reserve
from proof_eval.training.reward import verified_score
from proof_eval.verification.references import original_evaluation, required_versions


def original_pack(row: dict, evaluator: Evaluator) -> dict:
    """Freeze original-only context and the existing fixed score denominators."""
    # Dataset attaches the explicit published-heartbeat field. Use its exact row
    # identity, as the evaluator fingerprints that row for every reference key.
    canonical_row = evaluator.dataset.get(row["name"])
    if any(
        canonical_row.get(k) != v for k, v in row.items() if k != "published_heartbeats"
    ):
        raise ValueError("Original row differs from the evaluator dataset")
    row = canonical_row
    versions = required_versions({"row": row})
    references = evaluator.get_reference(row["name"])["versions"]
    for version in versions:
        reference = references[version]
        heartbeats = reference.get("heartbeats")
        if reference.get("status") != "prepared" or (
            type(heartbeats) not in (int, float)
            or not math.isfinite(heartbeats)
            or heartbeats <= 0
        ):
            raise ValueError("Original reference unavailable: " + version)
    context = row.get("header", "")
    if row.get("file_path"):
        project = evaluator.projects[(row["source"], versions[0])]
        source = (project / row["file_path"]).resolve()
        if not source.is_relative_to(project):
            raise ValueError("Task source escapes the configured project")
        text = source.read_text()
        target = row["src"] if text.count(row["src"]) == 1 else row["statement"]
        if text.count(target) != 1:
            raise ValueError("Original statement is not unique in its pinned source")
        context = text[: text.index(target)][-6000:]
    pack = {
        "name": row["name"],
        "row": row,
        "proof": row["src"],
        "incumbent": {
            "schema_version": 1,
            "name": row["name"],
            "status": "passed",
            "primary_version": versions[0],
            "requested_versions": versions,
            "all_versions": versions,
            "reference": {
                "length": row["proof_length"],
                "published_heartbeats": row.get("published_heartbeats"),
            },
            "per_version": {v: {"reference": references[v]} for v in versions},
        },
        "source_context": context,
        "source_excerpt_characters": len(context),
    }
    pack["incumbent"] = original_evaluation(pack)
    return pack


def _prepare_task(
    row: dict, dataset_dir: Path, environments: Path, output: Path
) -> dict:
    from proof_eval.verification.metrics import token_count, validate_candidate

    identity = task_id(row)
    path = output / "references" / (identity + ".json")
    if path.exists():
        record = read(path)
        if record["task"] != [row["source"], row["name"]]:
            raise ValueError("Prepared task identity changed")
        if record["status"] == "prepared":
            if sha(output / record["pack_path"]) != record["pack_sha256"]:
                raise ValueError("Prepared original pack changed")
        return record
    marker = output / "reference-started" / (identity + ".json")
    if marker.exists():
        raise RuntimeError(
            "Original preparation is indeterminate; inspect before continuing"
        )
    immutable(marker, {"task": [row["source"], row["name"]], "task_id": identity})
    record = {"task": [row["source"], row["name"]], "task_id": identity}
    evaluator = Evaluator(
        dataset_dir / "rl-reserved.jsonl", environments, output / "cache", timeout=300
    )
    refs = None
    try:
        _, body = validate_candidate(row, row["src"])
        if token_count(body) != row["proof_length"]:
            raise ValueError("Original published token denominator mismatch")
        refs = evaluator.prepare_reference(row["name"], versions="all")
        immutable(output / "reference-observations" / (identity + ".json"), refs)
        pack = original_pack(row, evaluator)
        verified_score(pack["incumbent"], required_versions(pack))
        relative = "packs/" + identity + ".json"
        pin = immutable(output / relative, pack)
        record.update(status="prepared", pack_path=relative, pack_sha256=pin)
    except Exception as error:
        # This is a pre-model exclusion with its exact reason, never reward=0.
        record.update(
            status="preparation_failed",
            error_type=type(error).__name__,
            error=str(error),
            reference_outcomes={
                version: {
                    k: reference.get(k)
                    for k in [
                        "status",
                        "heartbeats",
                        "heartbeats_raw",
                        "error",
                        "error_type",
                        "reason",
                        "diagnostics",
                    ]
                }
                for version, reference in (refs or {}).get("versions", {}).items()
            },
        )
    immutable(path, record)
    return record


def prepare(
    dataset_dir: Path,
    environments: Path,
    output: Path,
    system_prompt: Path,
    episode_seconds: int = 1800,
    *,
    workers: int = 4,
) -> dict:
    if type(workers) is not int or not 1 <= workers <= 32:
        raise ValueError("Reference workers must be between 1 and 32")
    rows = validate_reserve(dataset_dir)
    output.mkdir(parents=True, exist_ok=True)
    task = partial(
        _prepare_task, dataset_dir=dataset_dir, environments=environments, output=output
    )
    if workers == 1:
        records = [task(row) for row in rows]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # map retains dataset order; each task owns distinct immutable paths/cache keys.
            records = list(executor.map(task, rows))
    eligible = [r for r in records if r["status"] == "prepared"]
    if len(eligible) < 2:
        raise RuntimeError("Fewer than two independently prepared RL tasks")
    raw = b"".join(
        (
            json.dumps(
                {
                    "messages": initial_messages(
                        read(output / r["pack_path"]),
                        system_prompt.read_text(),
                        episode_seconds,
                    ),
                    "arena_task_id": r["task_id"],
                    "chat_template_kwargs": {
                        "enable_thinking": True,
                        "reasoning_effort": "xhigh",
                    },
                },
                ensure_ascii=False,
            )
            + "\n"
        ).encode()
        for r in eligible
    )
    train = output / "train.jsonl"
    if train.exists() and train.read_bytes() != raw:
        raise ValueError("Prepared training input changed")
    if not train.exists():
        with train.open("xb") as stream:
            stream.write(raw)
    manifest = {
        "status": "prepared",
        "authorized_tasks": 200,
        "eligible_tasks": len(eligible),
        "preparation_failed": len(records) - len(eligible),
        "preparation_failure_reasons": [
            r for r in records if r["status"] != "prepared"
        ],
        "records": records,
        "dataset_sha256": sha(dataset_dir / "rl-reserved.jsonl"),
        "environments": str(environments),
        "environments_sha256": sha(environments),
        "train_sha256": sha(train),
        "optimizer_inputs_are_rl_reserve_only": True,
        "sft_or_heldout_outputs_consumed": False,
        "model_calls": 0,
    }
    immutable(output / "prepared.json", manifest)
    return manifest
