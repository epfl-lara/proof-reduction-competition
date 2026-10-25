"""Parallel preparation retains cohort order, exclusions and per-task custody."""

import time

import pytest

from proof_eval.evidence.immutable import immutable, sha
from proof_eval.training import prepare as preparation
from proof_eval.training.gates import require_preparation_policy


def test_parallel_references_preserve_dataset_order_and_full_manifest(
    tmp_path, monkeypatch
):
    rows = [{"source": "fixture", "name": str(i)} for i in range(4)]
    monkeypatch.setattr(preparation, "validate_reserve", lambda _: rows)
    (tmp_path / "rl-reserved.jsonl").write_text("fixture\n")
    env = tmp_path / "environments.json"
    env.write_text("{}")
    prompt = tmp_path / "prompt.md"
    prompt.write_text("system")
    completed = []

    def task(row, dataset_dir, environments, output):
        if row["name"] == "0":
            time.sleep(0.05)
        key = row["name"]
        path = "packs/" + key + ".json"
        pin = immutable(output / path, {"name": key})
        completed.append(key)
        return {
            "status": "prepared",
            "task_id": key,
            "task": ["fixture", key],
            "pack_path": path,
            "pack_sha256": pin,
        }

    monkeypatch.setattr(preparation, "_prepare_task", task)
    monkeypatch.setattr(
        preparation,
        "initial_messages",
        lambda pack, *_: [{"role": "user", "content": pack["name"]}],
    )
    result = preparation.prepare(tmp_path, env, tmp_path / "output", prompt, workers=4)
    assert completed[0] != "0"
    assert [r["task_id"] for r in result["records"]] == ["0", "1", "2", "3"]
    assert result["eligible_tasks"] == 4 and result["preparation_failed"] == 0
    assert result["dataset_sha256"] == sha(tmp_path / "rl-reserved.jsonl")
    assert result["model_calls"] == 0


@pytest.mark.parametrize("workers", [0, -1, True, 33])
def test_invalid_preparation_concurrency_is_rejected_before_work(tmp_path, workers):
    with pytest.raises(ValueError, match="workers"):
        preparation.prepare(
            tmp_path, tmp_path, tmp_path / "unused", tmp_path, workers=workers
        )
    assert not (tmp_path / "unused").exists()


def test_only_declared_compiler_confirmed_invalid_originals_can_be_excluded():
    record = {
        "status": "preparation_failed",
        "task_id": "invalid",
        "reference_outcomes": {
            "v1": {
                "status": "failed",
                "diagnostics": [{"data": "Target declaration depends on sorryAx"}],
            }
        },
    }
    require_preparation_policy([record], ["invalid"])
    with pytest.raises(RuntimeError, match="Unresolved"):
        require_preparation_policy([record], [])
    record["reference_outcomes"]["v1"]["status"] = "unavailable"
    with pytest.raises(RuntimeError, match="Unresolved"):
        require_preparation_policy([record], ["invalid"])
