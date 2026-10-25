from proof_eval.training.context import admit_rows


def test_overlong_inputs_are_explicit_exclusions_and_not_truncated():
    rows = [{"arena_task_id": str(x), "messages": [str(x)]} for x in range(3)]
    admitted, report = admit_rows(rows, [100, 100, 32768], 32768, 8192)
    assert admitted == rows[:2]
    assert report["context_excluded"] == [
        {
            "task_id": "2",
            "prompt_tokens": 32768,
            "reason": "initial_context_over_training_curriculum_limit",
        }
    ]
    assert report["truncated_inputs"] == 0


def test_static_batch_padding_does_not_silently_drop_an_eligible_problem():
    rows = [{"arena_task_id": str(x)} for x in range(3)]
    admitted, report = admit_rows(rows, [100, 100, 100], 32768, 8192)
    assert {x["arena_task_id"] for x in admitted} == {"0", "1", "2"}
    assert report["padding_task_groups"] == ["0"]
    assert report["distinct_eligible_tasks"] == 3
