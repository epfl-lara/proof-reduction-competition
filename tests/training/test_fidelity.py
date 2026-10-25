import pytest

from proof_eval.training.fidelity import check_loss_tokens
from proof_eval.training.reward import UnscorableEpisode


def test_tool_observations_and_inserted_prefix_are_not_trained():
    # 900 is a deterministic reasoning prefix; 10/11 are external tool tokens.
    check_loss_tokens(
        [[900, 7, 8], [900, 9]],
        [[0, 1, 1], [0, 1]],
        {
            "labels": [-100, 900, 7, 8, 10, 11, 900, 9],
            "loss_scale": [0, 0, 1, 1, 0, 0, 0, 1],
        },
    )


def test_accidental_retokenization_is_detected_even_if_decoding_would_match():
    with pytest.raises(UnscorableEpisode, match="sampled"):
        check_loss_tokens([[7, 8]], [[1, 1]], {"labels": [-100, 99]})


def test_tool_tokens_cannot_enter_the_policy_loss():
    with pytest.raises(UnscorableEpisode, match="sampled"):
        check_loss_tokens([[7]], [[1]], {"labels": [-100, 7, 10]})


@pytest.mark.parametrize("masks", [[], [[1]], [[1, 2]]])
def test_missing_or_invalid_mask_refuses_the_sample(masks):
    with pytest.raises(UnscorableEpisode):
        check_loss_tokens([[7, 8]], masks, {"labels": [7, 8]})
