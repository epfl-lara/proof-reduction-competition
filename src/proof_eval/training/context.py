"""Explicit prompt admission without truncation or hidden dataset dropping."""

from __future__ import annotations

import json
from pathlib import Path

from proof_eval.evidence.immutable import immutable, sha


def admit_rows(
    rows: list[dict],
    lengths: list[int],
    context: int,
    completion: int,
    *,
    exclude_started: tuple[str, ...] = (),
) -> tuple[list[dict], dict]:
    if len(rows) != len(lengths):
        raise ValueError("Prompt length inventory is incomplete")
    if len(set(exclude_started)) != len(exclude_started) or not set(
        exclude_started
    ) <= {r["arena_task_id"] for r in rows}:
        raise ValueError(
            "Started-policy exclusion is duplicate or outside the prepared cohort"
        )
    admitted, excluded, previous_attempts = [], [], []
    for row, length in zip(rows, lengths):
        if row["arena_task_id"] in exclude_started:
            previous_attempts.append(
                {
                    "task_id": row["arena_task_id"],
                    "reason": "known_terminal_pre_update_policy_attempt_preserved_not_replayed",
                }
            )
        elif length + completion + 64 > context:
            excluded.append(
                {
                    "task_id": row["arena_task_id"],
                    "prompt_tokens": length,
                    "reason": "initial_context_over_training_curriculum_limit",
                }
            )
        else:
            admitted.append(row)
    if len(admitted) < 2:
        raise ValueError("Fewer than two RL tasks fit the declared context curriculum")
    distinct = len(admitted)
    # The static 8-completion/4-generation trainer needs an even number of prompts.
    # Document this single padding group so no eligible task is silently omitted.
    padding = []
    if len(admitted) % 2:
        padding.append(admitted[0]["arena_task_id"])
        admitted.append(dict(admitted[0]))
    return admitted, {
        "distinct_eligible_tasks": distinct,
        "training_rows": len(admitted),
        "context_excluded": excluded,
        "previous_policy_attempt_excluded": previous_attempts,
        "padding_task_groups": padding,
        "context_tokens": context,
        "max_completion_tokens": completion,
        "truncated_inputs": 0,
    }


def admit_prepared(
    prepared: Path,
    model_path: Path,
    context: int,
    completion: int,
    *,
    exclude_started: tuple[str, ...] = (),
) -> dict:
    from swift.model import get_model_processor
    from swift.template import get_template

    _, processor = get_model_processor(str(model_path), load_model=False, use_hf=True)
    template = get_template(processor, max_length=None, loss_scale="default")
    template.set_mode("vllm")
    rows = [
        json.loads(line) for line in (prepared / "train.jsonl").read_text().splitlines()
    ]
    lengths = [len(template.encode(row)["input_ids"]) for row in rows]
    admitted, result = admit_rows(
        rows, lengths, context, completion, exclude_started=exclude_started
    )
    output = prepared / "train-admitted.jsonl"
    raw = b"".join(
        (json.dumps(row, ensure_ascii=False) + "\n").encode() for row in admitted
    )
    with output.open("xb") as stream:
        stream.write(raw)
    result.update(
        train_sha256=sha(output),
        prompt_lengths=dict(zip([r["arena_task_id"] for r in rows], lengths)),
    )
    immutable(prepared / "context-admission.json", result)
    return result
