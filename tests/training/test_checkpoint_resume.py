"""Full-state resume and exact remaining-data admission without model work."""

import json
from array import array
from pathlib import Path
from types import SimpleNamespace

import pytest

from proof_eval.evidence.immutable import immutable, read, sha
from proof_eval.training.checkpoint_resume import (
    optimizer_state_entries,
    prepare_remaining_resume,
    resume_manifest,
    verify_restored_state,
)
from proof_eval.training.command import training_command
from proof_eval.training.fidelity import capture_purpose, trainable_sample_hash


class Parameter:
    requires_grad = True

    def __init__(self, value):
        self.value = value

    def detach(self):
        return self

    def reshape(self, *args):
        return self

    def __getitem__(self, key):
        return self

    def float(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self

    def tobytes(self):
        return array("f", [self.value]).tobytes()


def trainer(checkpoint):
    parameters = [("lora_A", Parameter(0.25)), ("lora_B", Parameter(0.0))]
    model = SimpleNamespace(named_parameters=lambda: iter(parameters))
    state = {"num_steps": 8, "lr_decay_steps": 752, "lr_warmup_steps": 37.6}
    optimizer = SimpleNamespace(
        optimizer=SimpleNamespace(state={"p": {"exp_avg": 0.1}})
    )
    return SimpleNamespace(
        args=SimpleNamespace(
            finetune=False,
            no_load_optim=False,
            no_load_rng=False,
            mcore_adapter=checkpoint,
            consumed_train_samples=8,
        ),
        state=SimpleNamespace(iteration=1, consumed_train_samples=8),
        opt_param_scheduler=SimpleNamespace(state_dict=lambda: dict(state)),
        optimizer=optimizer,
        unwrapped_models=[model],
        parameters=parameters,
        scheduled=state,
    )


@pytest.fixture
def resumed(tmp_path):
    home, root = tmp_path / "new-home", tmp_path / "new-root"
    home.mkdir()
    (root / "preparation").mkdir(parents=True)
    previous = tmp_path / "old-home"
    (previous / "release").mkdir(parents=True)
    immutable(
        previous / "release/plan.json", {"model_revision": "original", "lora_rank": 8}
    )
    immutable(previous / "release/source-manifest.json", {"source": "pinned"})
    checkpoint = previous / "resume-checkpoints/checkpoint-1"
    iteration = checkpoint / "iter_0000001"
    iteration.mkdir(parents=True)
    (checkpoint / "adapter_model.safetensors").write_bytes(b"test-real-policy-adapter")
    (iteration / ".metadata").write_bytes(b"native-metadata")
    for rank in range(8):
        (iteration / f"__{rank}_0.distcp").write_bytes(bytes([rank]))
    inventory = {
        str(path.relative_to(checkpoint)): {
            "bytes": path.stat().st_size,
            "sha256": sha(path),
        }
        for path in checkpoint.rglob("*")
        if path.is_file()
    }
    source_home, source_root = tmp_path / "custody-home", tmp_path / "custody-root"
    source_home.mkdir()
    source_root.mkdir()
    source = {
        "checkpoint_home": str(checkpoint),
        "checkpoint_files": inventory,
        "checkpoint_receipt": {"purpose": "arena_direct_rl"},
        "optimizer_reset_permitted": False,
        "completed_trained_tasks": ["a", "b"],
        "policy_used_not_updated_tasks": ["c", "d"],
    }
    for base in (source_home, source_root):
        immutable(base / "result.json", source)
    for base in (source_home, source_root):
        immutable(
            base / "finished.json",
            {"status": "passed", "result_sha256": sha(source_home / "result.json")},
        )
    raw = b"".join(
        (
            json.dumps(
                {
                    "arena_task_id": value,
                    "messages": [{"role": "user", "content": "original Δ " + value}],
                },
                ensure_ascii=False,
            )
            + "\n"
        ).encode()
        for value in "abcdef"
    )
    parent_data = tmp_path / "parent.jsonl"
    parent_data.write_bytes(raw)
    (root / "preparation/train-admitted.jsonl").write_bytes(raw)
    loaded = trainer(str(checkpoint))
    spec = {
        "schema": "arena_native_optimizer_resume_v1",
        "purpose": "arena_direct_rl",
        "model_revision": "original",
        "lora_rank": 8,
        "source_training_home": str(previous),
        "source_plan_sha256": sha(previous / "release/plan.json"),
        "source_manifest_sha256": sha(previous / "release/source-manifest.json"),
        "source_custody_home": str(source_home),
        "source_custody_root": str(source_root),
        "source_custody_result_sha256": sha(source_home / "result.json"),
        "checkpoint": str(checkpoint),
        "checkpoint_files": inventory,
        "checkpoint_step": 1,
        "checkpoint_consumed_train_samples": 8,
        "checkpoint_scheduler_steps": 8,
        "checkpoint_lr_decay_steps": 752,
        "checkpoint_lr_warmup_steps": 37.6,
        "parent_training_data": str(parent_data),
        "parent_training_data_sha256": sha(parent_data),
        "parent_training_rows": 6,
        "completed_trained_task_ids": ["a", "b"],
        "policy_used_not_updated_task_ids": ["c", "d"],
        "remaining_training_rows": 2,
        "global_train_iters": 2,
        "remaining_dataset_sampler_start": 0,
        "expected_trainable_sample_sha256": {"0": trainable_sample_hash(loaded)},
        "optimizer_reset_permitted": False,
        "unknown_model_replay_permitted": False,
        "restore_native_optimizer": True,
        "restore_native_rng": True,
        "restore_native_scheduler": True,
    }
    path = tmp_path / "resume-manifest.json"
    immutable(path, spec)
    plan = {
        "home": str(home),
        "root": str(root),
        "model_revision": "original",
        "lora_rank": 8,
        "context_tokens": 32768,
        "per_turn_max_tokens": 8192,
        "max_turns": 32,
        "optimizer_resume": {
            "manifest": str(path),
            "manifest_sha256": sha(path),
            "checkpoint": str(checkpoint),
            "global_train_iters": 2,
        },
    }
    return plan, spec, loaded, raw


def test_remaining_data_excludes_every_prior_policy_task_and_keeps_exact_lines(resumed):
    plan, spec, _, raw = resumed
    result = prepare_remaining_resume(
        plan, {"distinct_eligible_tasks": 6, "padding_task_groups": []}
    )
    path = Path(plan["root"]) / "preparation/train-resume-remaining.jsonl"
    assert path.read_bytes() == b"".join(raw.splitlines(keepends=True)[4:])
    assert [
        json.loads(line)["arena_task_id"] for line in path.read_bytes().splitlines()
    ] == ["e", "f"]
    assert Path(spec["parent_training_data"]).read_bytes() == raw
    assert result["training_rows"] == 2 and result["global_train_iters"] == 2
    assert result["optimizer_reset"] is False
    assert read(Path(plan["home"]) / "resume-data-admission.json") == result


@pytest.mark.parametrize("target", ["source", "checkpoint", "dataset", "source-plan"])
def test_changed_resume_assets_refuse_before_model_admission(resumed, target):
    plan, spec, _, _ = resumed
    path = {
        "source": Path(spec["source_custody_home"]) / "result.json",
        "checkpoint": Path(spec["checkpoint"]) / "adapter_model.safetensors",
        "dataset": Path(spec["parent_training_data"]),
        "source-plan": Path(spec["source_training_home"]) / "release/plan.json",
    }[target]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        prepare_remaining_resume(
            plan, {"distinct_eligible_tasks": 6, "padding_task_groups": []}
        )
    assert not (
        Path(plan["root"]) / "preparation/train-resume-remaining.jsonl"
    ).exists()


def test_weights_only_checkpoint_is_not_a_native_optimizer_resume(resumed):
    plan, spec, _, _ = resumed
    (Path(spec["checkpoint"]) / "iter_0000001/.metadata").unlink()
    with pytest.raises(ValueError, match="optimizer checkpoint metadata"):
        prepare_remaining_resume(
            plan, {"distinct_eligible_tasks": 6, "padding_task_groups": []}
        )


def test_native_restore_preserves_optimizer_and_scheduler_and_only_moves_new_data_cursor(
    resumed,
):
    _, spec, loaded, _ = resumed
    original_optimizer = loaded.optimizer
    original_schedule = dict(loaded.scheduled)
    record = verify_restored_state(loaded, spec, 0)
    assert loaded.optimizer is original_optimizer
    assert loaded.scheduled == original_schedule
    assert loaded.state.iteration == 1
    assert (
        loaded.state.consumed_train_samples == loaded.args.consumed_train_samples == 0
    )
    assert record["source_consumed_train_samples"] == 8
    assert record["optimizer_state_entries"] == 1
    assert record["optimizer_reset"] is False and record["new_model_calls"] == 0


@pytest.mark.parametrize(
    "fault",
    [
        "finetune",
        "no_load_optim",
        "no_load_rng",
        "iteration",
        "samples",
        "scheduler",
        "weights",
        "adam",
    ],
)
def test_incomplete_or_reset_native_restore_cannot_look_successful(resumed, fault):
    _, spec, loaded, _ = resumed
    if fault in {"finetune", "no_load_optim", "no_load_rng"}:
        setattr(loaded.args, fault, True)
    elif fault == "iteration":
        loaded.state.iteration = 0
    elif fault == "samples":
        loaded.state.consumed_train_samples = 0
    elif fault == "scheduler":
        loaded.scheduled["num_steps"] = 0
    elif fault == "weights":
        loaded.parameters[1][1].value = 0.5
    elif fault == "adam":
        loaded.optimizer.optimizer.state.clear()
    with pytest.raises(ValueError):
        verify_restored_state(loaded, spec, 0)


def test_command_uses_stock_full_state_resume_not_weights_only(resumed):
    plan, _, _, _ = resumed
    command = training_command(plan, "/original-model")
    for flag in ["--finetune", "--no_load_optim", "--no_load_rng"]:
        assert command[command.index(flag) + 1] == "false"
    assert (
        command[command.index("--mcore_adapter") + 1]
        == plan["optimizer_resume"]["checkpoint"]
    )
    assert command[command.index("--train_iters") + 1] == "2"
    assert command[command.index("--dataset") + 1].endswith(
        "train-resume-remaining.jsonl"
    )


def test_resume_manifest_rejects_silent_optimizer_reset(resumed):
    plan, _, _, _ = resumed
    path = Path(plan["optimizer_resume"]["manifest"])
    value = read(path)
    value["optimizer_reset_permitted"] = True
    path.write_text(json.dumps(value))
    plan["optimizer_resume"]["manifest_sha256"] = sha(path)
    with pytest.raises(ValueError):
        resume_manifest(plan)


def test_adam_wrappers_cannot_double_count_shared_state():
    inner = SimpleNamespace(state={"a": {}, "b": {}})
    root = SimpleNamespace(chained_optimizers=[inner, inner], optimizer=inner)
    assert optimizer_state_entries(root) == 2


def test_probe_purpose_does_not_become_real_training_due_to_parent_environment():
    assert (
        capture_purpose("arena_direct_rl", gpu_probe=True) == "synthetic_gpu_smoke_only"
    )
    assert (
        capture_purpose("synthetic_gpu_training_check", gpu_probe=False)
        == "synthetic_gpu_training_check"
    )
