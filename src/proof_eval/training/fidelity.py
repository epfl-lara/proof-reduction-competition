"""Refuse a training sample whose loss tokens differ from sampled output."""

from __future__ import annotations

import hashlib

from proof_eval.training.reward import UnscorableEpisode


def capture_purpose(run_purpose: str | None, *, gpu_probe: bool) -> str:
    if gpu_probe:
        return "synthetic_gpu_smoke_only"
    return run_purpose or "arena_training_rollout"


def trainable_sample_hash(trainer) -> str:
    """Keep the existing A/B tensor sample identical across save and restore."""
    digest = hashlib.sha256()
    count = 0
    for model in trainer.unwrapped_models:
        for name, parameter in model.named_parameters():
            if parameter.requires_grad:
                values = parameter.detach().reshape(-1)[:256].float().cpu().numpy()
                digest.update(name.encode())
                digest.update(values.tobytes())
                count += 1
                if count >= 32:
                    return digest.hexdigest()
    if not count:
        raise UnscorableEpisode("Trainer has no trainable parameters")
    return digest.hexdigest()


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
