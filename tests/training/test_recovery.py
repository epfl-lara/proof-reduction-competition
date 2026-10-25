"""Real started policy work is retained and cannot be silently sampled again."""

import pytest

from proof_eval.evidence.immutable import immutable, sha
from proof_eval.training.context import admit_rows
from proof_eval.training.recovery import consumed_tasks


def fixture_plan(tmp_path):
    p = tmp_path / "archive.json"
    immutable(
        p,
        {
            "learned_checkpoint_directories": [],
            "home_optimizer_receipts": [],
            "home_checkpoint_receipts": [],
            "r11_rollouts": [
                {"task_id": "used", "model_turns": [{"file": "saved-first-turn"}]}
            ],
        },
    )
    return {
        "previous_policy_attempts": {
            "archive_result": str(p),
            "archive_result_sha256": sha(p),
            "excluded_task_ids": ["used"],
        }
    }


def test_started_ids_are_excluded_explicitly_without_resampling_or_truncation(tmp_path):
    plan = fixture_plan(tmp_path)
    ids = consumed_tasks(plan)
    rows = [{"arena_task_id": name} for name in ["used", "new-a", "new-b", "too-long"]]
    admitted, report = admit_rows(
        rows, [10, 10, 10, 40000], 32768, 8192, exclude_started=ids
    )
    assert admitted == rows[1:3]
    assert report["distinct_eligible_tasks"] == 2 and report["truncated_inputs"] == 0
    assert report["previous_policy_attempt_excluded"][0]["task_id"] == "used"
    assert report["context_excluded"][0]["task_id"] == "too-long"


def test_wrong_consumed_set_and_changed_archive_refuse_continuation(tmp_path):
    plan = fixture_plan(tmp_path)
    plan["previous_policy_attempts"]["excluded_task_ids"] = ["other"]
    with pytest.raises(ValueError, match="Consumed-task"):
        consumed_tasks(plan)
    plan["previous_policy_attempts"]["archive_result_sha256"] = "changed"
    with pytest.raises(ValueError, match="archive changed"):
        consumed_tasks(plan)


def test_learned_state_cannot_be_treated_as_a_fresh_base_policy(tmp_path):
    plan = fixture_plan(tmp_path)
    p = tmp_path / "learned.json"
    immutable(
        p,
        {
            "learned_checkpoint_directories": ["checkpoint-1"],
            "home_optimizer_receipts": [],
            "home_checkpoint_receipts": [],
            "r11_rollouts": [],
        },
    )
    plan["previous_policy_attempts"].update(
        archive_result=str(p), archive_result_sha256=sha(p)
    )
    with pytest.raises(ValueError, match="exact checkpoint"):
        consumed_tasks(plan)
