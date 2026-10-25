"""Align native multi-turn liveness with the shared colocated inference group."""

from __future__ import annotations

import inspect
import os
import time
from pathlib import Path


def install_colocated_world_sync() -> None:
    """Select the library's boolean-gather callback without changing samples."""
    from proof_eval.evidence.immutable import immutable, read

    config_path = os.environ.get("ARENA_RL_CONFIG")
    if not config_path:
        return
    config = read(Path(config_path))
    if not config.get("colocate_multi_turn_world_sync", False):
        return

    import torch.distributed as distributed
    from swift.megatron.trainers import rollout_mixin

    original = rollout_mixin.run_multi_turn
    if getattr(original, "arena_colocated_world_sync", False):
        return
    signature = inspect.signature(original)
    recorded = False

    def run_multi_turn(*args, **kwargs):
        nonlocal recorded
        if not distributed.is_initialized() or distributed.get_world_size() != 8:
            raise RuntimeError(
                "Declared colocated world synchronization requires eight ranks"
            )
        bound = signature.bind(*args, **kwargs)
        # run_multi_turn uses gather_fn ONLY to ask whether any rank has work.
        # Local requests, returned outputs, loss masks and rewards stay unchanged.
        bound.arguments["gather_fn"] = lambda values: rollout_mixin.gather_object(
            values, group=distributed.group.WORLD
        )
        if not recorded:
            rank = distributed.get_rank()
            original_group = rollout_mixin.mpu.get_model_parallel_group()
            record = {
                "at_epoch": time.time(),
                "rank": rank,
                "purpose": os.environ.get("ARENA_RL_RUN_PURPOSE", "arena_direct_rl"),
                "original_rollout_group": distributed.get_process_group_ranks(
                    original_group
                ),
                "continuation_liveness_group": list(range(8)),
                "inference_tensor_parallel_size": 8,
                "boolean_liveness_only": True,
                "input_output_tokens_modified": False,
                "reward_modified": False,
            }
            for base in (config["root"], config["home"]):
                immutable(
                    Path(base) / "rollout-collectives" / f"rank-{rank}.json", record
                )
            recorded = True
        return original(*bound.args, **bound.kwargs)

    run_multi_turn.arena_colocated_world_sync = True
    rollout_mixin.run_multi_turn = run_multi_turn
