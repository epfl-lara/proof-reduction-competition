"""Refuse a training sample whose loss tokens differ from sampled output."""

from __future__ import annotations

from proof_eval.training.reward import UnscorableEpisode


def check_loss_tokens(
    response_ids: list[list[int]], response_masks: list[list[int]], encoded: dict
) -> None:
    if len(response_ids) != len(response_masks):
        raise UnscorableEpisode("Missing per-turn response masks")
    expected = []
    for ids, mask in zip(response_ids, response_masks):
        if len(ids) != len(mask) or any(
            type(x) is not int or x not in (0, 1) for x in mask
        ):
            raise UnscorableEpisode("Loss mask does not align with sampled IDs")
        expected.extend(token for token, keep in zip(ids, mask) if keep)
    labels = encoded["labels"]
    scale = encoded.get("loss_scale") or [1] * len(labels)
    if len(scale) != len(labels):
        raise UnscorableEpisode("Encoded loss scale has the wrong length")
    actual = [
        int(token) for token, keep in zip(labels, scale) if token != -100 and keep > 0
    ]
    if actual != expected:
        raise UnscorableEpisode(
            "Trainable token IDs differ from actual sampled outputs"
        )
