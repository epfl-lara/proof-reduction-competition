"""The new human instruction changes sequencing, with exact plan binding."""

import pytest

from proof_eval.training.gates import (
    launch_plan_sha256,
    require_launch_authorization,
)


def example():
    plan = {
        "after_current_15_task_test": False,
        "launch_id": "new-owned-release",
        "model_revision": "original-base-pin",
        "context_tokens": 32768,
        "episode_seconds": 1800,
        "root": "/scratch/new-release",
    }
    authorization = {
        "status": "authorized",
        "scope": "train",
        "human_instruction": "Okay dw just start the training then",
        "authorized_plan_sha256": launch_plan_sha256(plan),
    }
    return plan, authorization


def test_training_authorization_binds_the_exact_plan():
    plan, authorization = example()
    plan["launch_authorization_sha256"] = "external-file-sha"
    require_launch_authorization(plan, authorization)


@pytest.mark.parametrize(
    "field,value",
    [
        ("context_tokens", 266400),
        ("episode_seconds", 28800),
        ("root", "/scratch/other-release"),
        ("launch_id", "another-job"),
        ("model_revision", "other-model"),
    ],
)
def test_permission_to_start_does_not_allow_different_training_plan(field, value):
    plan, authorization = example()
    plan[field] = value
    with pytest.raises(RuntimeError, match="another RL plan"):
        require_launch_authorization(plan, authorization)


@pytest.mark.parametrize(
    "field,value", [("human_instruction", ""), ("status", "pending")]
)
def test_missing_human_authorization_still_blocks_submission(field, value):
    plan, authorization = example()
    authorization[field] = value
    with pytest.raises(RuntimeError, match="Explicit training"):
        require_launch_authorization(plan, authorization)
