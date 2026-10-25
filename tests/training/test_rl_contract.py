import pytest

from proof_eval.evidence.immutable import immutable
from proof_eval.training.actions import parse_action
from proof_eval.training.command import training_command
from proof_eval.training.data import validate_reserve
from proof_eval.training.gates import (
    assert_no_unknown_dispatch,
)
from proof_eval.training.reward import (
    ScorePotential,
    UnscorableEpisode,
    validate_token_evidence,
    verified_score,
)


def evaluation(length=0, heartbeat=0, passing=True):
    return {
        "status": "passed",
        "per_version": {"v1": {"passed": passing}, "v2": {"passed": passing}},
        "scores": {
            "length_reduction_pct": length,
            "heartbeat_reduction_pct": heartbeat,
            "compatibility_pct": 100,
            "combined_pct": (length + heartbeat + 100) / 3,
        },
    }


def test_partial_rewards_telescope_and_are_not_added_twice():
    potential = ScorePotential.from_original(evaluation(), ["v1", "v2"])
    first = potential.observe_best(evaluation(30, 12), ["v1", "v2"])
    second = potential.observe_best(evaluation(60, 30), ["v1", "v2"])
    assert first + second == pytest.approx(potential.reward)
    assert potential.reward == pytest.approx(0.3)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x.update(status="unavailable"),
        lambda x: x["per_version"].pop("v2"),
        lambda x: x["per_version"]["v2"].update(passed=False),
        lambda x: x["scores"].update(combined_pct=float("nan")),
        lambda x: x["scores"].update(combined_pct=99),
        lambda x: x["scores"].update(heartbeat_reduction_pct=None),
        lambda x: x["scores"].update(compatibility_pct=50),
    ],
)
def test_no_reward_for_unavailable_or_forged_verdicts(mutation):
    value = evaluation()
    mutation(value)
    with pytest.raises(UnscorableEpisode):
        verified_score(value, ["v1", "v2"])


def test_regressed_host_best_is_not_silently_clamped():
    p = ScorePotential.from_original(evaluation(30, 30), ["v1", "v2"])
    with pytest.raises(UnscorableEpisode):
        p.observe_best(evaluation(), ["v1", "v2"])


@pytest.mark.parametrize(
    "ids,lps",
    [
        ([], []),
        ([1, 2], [-1.0]),
        ([True], [-1.0]),
        ([1], [float("nan")]),
        ([-1], [-0.1]),
    ],
)
def test_missing_or_misaligned_exact_tokens_cannot_train(ids, lps):
    with pytest.raises(UnscorableEpisode):
        validate_token_evidence(ids, lps)


def test_sample_ids_are_not_retokenized_or_repaired():
    ids = [251000, 4, 4, 248055]
    validate_token_evidence(ids, [-0.1, -0.2, -0.3, -0.01])
    assert ids == [251000, 4, 4, 248055]


@pytest.mark.parametrize(
    "text",
    [
        "check it",
        '<arena_action>{"op":"exec"}</arena_action>',
        '<arena_action>{"op":"status"}</arena_action>' * 2,
    ],
)
def test_ambiguous_or_arbitrary_shell_actions_rejected(text):
    with pytest.raises(ValueError):
        parse_action(text)


def test_host_verdict_remains_authoritative_over_model_prose():
    assert parse_action(
        'My score is 100. <arena_action>{"op":"status"}</arena_action>'
    ) == {"op": "status"}


def test_unknown_job_is_not_submitted_twice(tmp_path):
    assert_no_unknown_dispatch(tmp_path)
    immutable(tmp_path / "submission-intent.json", {"once": True})
    with pytest.raises(RuntimeError, match="do not submit"):
        assert_no_unknown_dispatch(tmp_path)


def test_original_reserve_is_hash_bound_and_disjoint(tmp_path, monkeypatch):
    import json

    from proof_eval.evidence.io import digest
    from proof_eval.training import data

    for filename, source, count in [
        ("rl-reserved.jsonl", "rl", 200),
        ("sft.jsonl", "sft", 1857),
        ("validation.jsonl", "validation", 50),
    ]:
        (tmp_path / filename).write_text(
            "".join(
                json.dumps({"source": source, "name": str(i)}) + "\n"
                for i in range(count)
            )
        )
    monkeypatch.setattr(data, "RL_SHA", digest(tmp_path / "rl-reserved.jsonl"))
    assert len(validate_reserve(tmp_path)) == 200
    path = tmp_path / "validation.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0] = {"source": "rl", "name": "0"}
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(ValueError, match="overlap"):
        validate_reserve(tmp_path)


def test_immutable_artifact_cannot_be_overwritten(tmp_path):
    path = tmp_path / "reward.json"
    immutable(path, {"score": 1})
    immutable(path, {"score": 1})
    with pytest.raises(ValueError):
        immutable(path, {"score": 2})


def test_command_uses_original_base_and_keeps_long_context():
    plan = {
        "root": "/scratch/new",
        "home": "/home/new",
        "model_revision": "pinned",
        "context_tokens": 266400,
        "max_turns": 32,
        "per_turn_max_tokens": 4096,
    }
    command = training_command(plan, "/cache/base-model")
    assert command[command.index("--model") + 1] == "/cache/base-model"
    assert "ThinkingCap" not in " ".join(command)
    assert command[command.index("--max_length") + 1] == "266400"
    assert command[command.index("--num_generations") + 1] == "4"
    assert command[command.index("--truncation_strategy") + 1] == "delete"
    assert command[command.index("--split_dataset_ratio") + 1] == "0"
