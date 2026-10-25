"""Fail a whole rollout batch coherently, without inventing rewards."""

from __future__ import annotations

from datetime import timedelta

_GROUPS: dict[int, object] = {}


def gather_failures(local: list[dict]) -> list[dict]:
    import os

    import torch.distributed as dist

    if not dist.is_available() or not dist.is_initialized():
        return list(local)
    # CPU collectives avoid CUDA object-size allocations and let host tools run
    # within their episode budget. Every rank enters these two batch boundaries.
    pid = os.getpid()
    if pid not in _GROUPS:
        _GROUPS[pid] = dist.new_group(backend="gloo", timeout=timedelta(seconds=2100))
    gathered = [None] * dist.get_world_size()
    dist.all_gather_object(gathered, local, group=_GROUPS[pid])
    return [item for rank_errors in gathered for item in rank_errors]
