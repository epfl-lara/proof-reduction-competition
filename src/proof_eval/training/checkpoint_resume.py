"""Native full-state restore into an explicit, non-replayed remaining data stream."""

from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path

from proof_eval.evidence.immutable import immutable, read, sha
from proof_eval.training.fidelity import trainable_sample_hash


def resume_manifest(plan: dict) -> dict | None:
    declared = plan.get("optimizer_resume")
    if not declared:
        return None
    path = Path(declared["manifest"])
    if sha(path) != declared["manifest_sha256"]:
        raise ValueError("Optimizer resume manifest changed")
    spec = read(path)
    if (
        spec["schema"] != "arena_native_optimizer_resume_v1"
        or spec["purpose"] != "arena_direct_rl"
        or spec["model_revision"] != plan["model_revision"]
        or spec["lora_rank"] != plan["lora_rank"]
        or spec["checkpoint"] != declared["checkpoint"]
        or spec["global_train_iters"] != declared["global_train_iters"]
        or spec["optimizer_reset_permitted"] is not False
        or spec["unknown_model_replay_permitted"] is not False
        or spec["remaining_dataset_sampler_start"] != 0
    ):
        raise ValueError("Resume must preserve the declared native optimizer lineage")
    if not all(
        spec.get(key) is True
        for key in (
            "restore_native_optimizer",
            "restore_native_rng",
            "restore_native_scheduler",
        )
    ):
        raise ValueError("Weights-only or reset resume is not authorized")
    if spec["remaining_training_rows"] % 2 or spec["global_train_iters"] != (
        spec["checkpoint_step"] + spec["remaining_training_rows"] // 2
    ):
        raise ValueError("Remaining data and global optimizer count do not agree")
    return spec


def prepare_remaining_resume(plan: dict, admission: dict) -> dict | None:
    """Verify durable state once, preserve original rows, exclude prior policy work."""
    spec = resume_manifest(plan)
    if spec is None:
        return None
    prior = Path(spec["source_training_home"]) / "release"
    if (
        sha(prior / "plan.json") != spec["source_plan_sha256"]
        or sha(prior / "source-manifest.json") != spec["source_manifest_sha256"]
    ):
        raise ValueError("Original native training source or plan changed")
    prior_plan = read(prior / "plan.json")
    if (
        prior_plan["model_revision"] != plan["model_revision"]
        or prior_plan["lora_rank"] != plan["lora_rank"]
    ):
        raise ValueError("Checkpoint belongs to a different original model")
    source_home = Path(spec["source_custody_home"])
    source_root = Path(spec["source_custody_root"])
    finished = read(source_home / "finished.json")
    if (
        (source_home / "finished.json").read_bytes()
        != (source_root / "finished.json").read_bytes()
        or finished["status"] != "passed"
        or finished["result_sha256"] != spec["source_custody_result_sha256"]
    ):
        raise ValueError("Original checkpoint custody has no passed terminal receipt")
    raw = (source_home / "result.json").read_bytes()
    if (
        raw != (source_root / "result.json").read_bytes()
        or sha(source_home / "result.json") != spec["source_custody_result_sha256"]
    ):
        raise ValueError("Original checkpoint custody is incomplete or changed")
    source = json.loads(raw)
    if (
        source["checkpoint_home"] != spec["checkpoint"]
        or source["checkpoint_files"] != spec["checkpoint_files"]
        or source["checkpoint_receipt"]["purpose"] != "arena_direct_rl"
        or source["optimizer_reset_permitted"] is not False
    ):
        raise ValueError("Resume source is not the verified real Arena checkpoint")
    checkpoint = Path(spec["checkpoint"])
    if not (checkpoint / f"iter_{spec['checkpoint_step']:07d}/.metadata").is_file():
        raise ValueError("Native optimizer checkpoint metadata is missing")
    if len(
        list((checkpoint / f"iter_{spec['checkpoint_step']:07d}").glob("__*_0.distcp"))
    ) != plan.get("gpus", 8):
        raise ValueError("Native optimizer checkpoint shards are missing")
    if len(spec["checkpoint_files"]) >= 1000:
        raise ValueError("Checkpoint inventory exceeds its declared bounded scope")
    for relative, expected in spec["checkpoint_files"].items():
        name = Path(relative)
        if name.is_absolute() or ".." in name.parts:
            raise ValueError("Checkpoint inventory escapes its root")
        path = checkpoint / name
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size != expected["bytes"]
            or sha(path) != expected["sha256"]
        ):
            raise ValueError(
                "Native checkpoint file failed custody verification: " + relative
            )
    data = Path(spec["parent_training_data"])
    if sha(data) != spec["parent_training_data_sha256"]:
        raise ValueError("Original admitted training data changed")
    lines = data.read_bytes().splitlines(keepends=True)
    records = [json.loads(line) for line in lines]
    ids = [row["arena_task_id"] for row in records]
    if len(ids) != spec["parent_training_rows"] or len(set(ids)) != len(ids):
        raise ValueError("Original prompt cohort is missing or padded unexpectedly")
    trained = spec["completed_trained_task_ids"]
    interrupted = spec["policy_used_not_updated_task_ids"]
    excluded = trained + interrupted
    if len(set(excluded)) != len(excluded) or not set(excluded) <= set(ids):
        raise ValueError("Prior policy task accounting is ambiguous")
    if set(trained) != set(source["completed_trained_tasks"]) or set(
        interrupted
    ) != set(source["policy_used_not_updated_tasks"]):
        raise ValueError("Prior attempted task IDs do not match terminal custody")
    if (
        admission["distinct_eligible_tasks"] != len(ids)
        or admission["padding_task_groups"]
    ):
        raise ValueError("Fresh original admission differs from the resumed cohort")
    current = Path(plan["root"]) / "preparation/train-admitted.jsonl"
    current_ids = [
        json.loads(line)["arena_task_id"] for line in current.read_bytes().splitlines()
    ]
    if current_ids != ids:
        raise ValueError("Fresh admitted task order differs from parent cohort")
    selected = [line for line, task_id in zip(lines, ids) if task_id not in excluded]
    if len(selected) != spec["remaining_training_rows"]:
        raise ValueError("Remaining-only data has the wrong distinct task count")
    output = Path(plan["root"]) / "preparation/train-resume-remaining.jsonl"
    with output.open("xb") as stream:
        stream.write(b"".join(selected))
        stream.flush()
        os.fsync(stream.fileno())
    result = {
        "status": "native_checkpoint_and_remaining_data_verified",
        "at_epoch": time.time(),
        "checkpoint": str(checkpoint),
        "manifest_sha256": plan["optimizer_resume"]["manifest_sha256"],
        "source_training_data_sha256": spec["parent_training_data_sha256"],
        "train_sha256": sha(output),
        "training_rows": len(selected),
        "distinct_eligible_tasks": len(selected),
        "prior_trained_tasks": trained,
        "prior_unupdated_policy_tasks": interrupted,
        "resumed_optimizer_iteration": spec["checkpoint_step"],
        "global_train_iters": spec["global_train_iters"],
        "new_data_sampler_start": 0,
        "optimizer_reset": False,
        "model_calls": 0,
        "input_rows_rewritten": False,
    }
    for base in (plan["home"], plan["root"]):
        immutable(Path(base) / "resume-data-admission.json", result)
    return result


def optimizer_state_entries(optimizer) -> int:
    pending, seen, count = [optimizer], set(), 0
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if len(seen) > 32:
            raise ValueError("Unexpected native optimizer wrapper graph")
        state = getattr(current, "state", None)
        if isinstance(state, dict):
            count += len(state)
        pending.extend(getattr(current, "chained_optimizers", []) or [])
        child = getattr(current, "optimizer", None)
        if child is not None:
            pending.append(child)
    return count


def verify_restored_state(
    trainer, spec: dict, rank: int, *, restore_only: bool = False
) -> dict:
    args, state, scheduler = trainer.args, trainer.state, trainer.opt_param_scheduler
    if args.finetune or args.no_load_optim or args.no_load_rng:
        raise ValueError("Native restore disabled optimizer or RNG loading")
    if str(args.mcore_adapter) != spec["checkpoint"]:
        raise ValueError("Native trainer loaded a different adapter")
    if (
        state.iteration != spec["checkpoint_step"]
        or state.consumed_train_samples != spec["checkpoint_consumed_train_samples"]
    ):
        raise ValueError("Native optimizer iteration/sample state was not restored")
    scheduled = scheduler.state_dict()
    if (
        scheduled["num_steps"] != spec["checkpoint_scheduler_steps"]
        or scheduled["lr_decay_steps"] != spec["checkpoint_lr_decay_steps"]
        or not math.isclose(
            scheduled["lr_warmup_steps"], spec["checkpoint_lr_warmup_steps"]
        )
    ):
        raise ValueError("Native learning-rate scheduler was reset or changed")
    sample = trainable_sample_hash(trainer)
    if sample != spec["expected_trainable_sample_sha256"][str(rank)]:
        raise ValueError("Restored trainable weights differ from the saved real policy")
    entries = optimizer_state_entries(trainer.optimizer)
    if not entries:
        raise ValueError("Native optimizer loaded no saved Adam state")
    native_iters = args.train_iters
    if native_iters not in {
        spec["remaining_training_rows"] // 2,
        spec["global_train_iters"],
    }:
        raise ValueError("Native remaining-data iteration count is unexpected")
    target = spec["checkpoint_step"] if restore_only else spec["global_train_iters"]
    record = {
        "at_epoch": time.time(),
        "rank": rank,
        "purpose": os.environ.get("ARENA_RL_RUN_PURPOSE", "arena_direct_rl"),
        "checkpoint": spec["checkpoint"],
        "optimizer_iteration": state.iteration,
        "source_consumed_train_samples": state.consumed_train_samples,
        "optimizer_state_entries": entries,
        "scheduler_state": scheduled,
        "trainable_sample_sha256": sample,
        "native_rng_loading_enabled": True,
        "new_remaining_data_sampler_start": spec["remaining_dataset_sampler_start"],
        "optimizer_reset": False,
        "new_model_calls": 0,
        "native_dataset_computed_iterations": native_iters,
        "declared_global_training_iterations": spec["global_train_iters"],
        "effective_native_loop_bound": target,
        "restore_only": restore_only,
    }
    # ms-swift recomputes train_iters from num_train_epochs before constructing
    # this trainer, overriding the CLI value. Its loop compares that bound with
    # the restored GLOBAL iteration, so retain the declared completed+remaining
    # total here. Scheduler state above has already been restored unchanged.
    args.train_iters = target
    state.max_steps = target
    # The input file is now a separately declared remaining-only stream. This
    # changes its cursor, never the optimizer, scheduler, RNG or global iteration.
    state.consumed_train_samples = spec["remaining_dataset_sampler_start"]
    args.consumed_train_samples = spec["remaining_dataset_sampler_start"]
    return record


def install_native_optimizer_resume() -> None:
    path = os.environ.get("ARENA_RL_CONFIG")
    if not path:
        return
    plan = read(Path(path))
    spec = resume_manifest(plan)
    if spec is None:
        return
    from swift.megatron.trainers.base import BaseMegatronTrainer

    original = BaseMegatronTrainer._load_checkpoint
    if getattr(original, "arena_native_resume", False):
        return

    def load_checkpoint(self):
        result = original(self)
        record = verify_restored_state(
            self,
            spec,
            int(os.environ.get("RANK", "0")),
            restore_only=bool(plan.get("checkpoint_restore_only", False)),
        )
        for base in (plan["home"], plan["root"]):
            immutable(
                Path(base) / "optimizer-resume" / f"rank-{record['rank']}.json", record
            )
        return result

    load_checkpoint.arena_native_resume = True
    BaseMegatronTrainer._load_checkpoint = load_checkpoint
