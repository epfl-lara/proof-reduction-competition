"""Close colocated vLLM before Megatron tears down its shared process groups."""

from __future__ import annotations

import os
import time
import traceback
from pathlib import Path

from proof_eval.evidence.immutable import immutable, read


def _offload_training_state(trainer) -> None:
    from swift.megatron.trainers.utils import (
        offload_megatron_model_to_cpu,
        offload_megatron_optimizer,
    )

    if not trainer.args.offload_model:
        raise RuntimeError("Sleeping colocated shutdown requires model offloading")
    offload_megatron_model_to_cpu(trainer.wrapped_models)
    if getattr(trainer, "ref_models", None):
        offload_megatron_model_to_cpu(trainer.ref_models)
    if getattr(trainer, "optimizer", None) and trainer.args.offload_optimizer:
        offload_megatron_optimizer(trainer.optimizer)


def shutdown_colocated_engine(trainer) -> None:
    """Use library lifecycle APIs after completed training and checkpoint saves."""
    if (
        not getattr(trainer, "use_vllm", False)
        or getattr(trainer, "vllm_mode", None) != "colocate"
        or getattr(trainer, "arena_colocated_engine_closed", False)
    ):
        return
    config = read(Path(os.environ["ARENA_RL_CONFIG"]))
    rank = int(os.environ.get("RANK", "0"))
    record = {
        "at_epoch": time.time(),
        "purpose": os.environ.get("ARENA_RL_RUN_PURPOSE", "arena_direct_rl"),
        "rank": rank,
        "after_final_training_and_checkpoint_save": True,
        "new_model_requests": 0,
    }

    def put(name, value):
        for base in (config["root"], config["home"]):
            immutable(Path(base) / "trainer-shutdown" / f"rank-{rank}" / name, value)

    put("started.json", record)
    try:
        # The stock generation path offloads these same objects before waking
        # vLLM. At terminal shutdown they remain on CPU; no training follows.
        _offload_training_state(trainer)
        engine = trainer.engine.engine.llm_engine
        sleeping = engine.is_sleeping()
        if sleeping:
            # Freeing asleep cuMem pools double-unmaps them in this pinned
            # vLLM. Remap only after the trainer has released its GPU storage.
            engine.wake_up()
        # This public client method detaches its weakref finalizer and closes
        # workers/groups while they still exist, before Megatron closes WORLD.
        engine.engine_core.shutdown()
        trainer.arena_colocated_engine_closed = True
        put(
            "finished.json",
            {
                **record,
                "at_epoch": time.time(),
                "status": "passed",
                "was_sleeping": sleeping,
                "library_shutdown_called": True,
            },
        )
    except BaseException:
        put(
            "failed.json",
            {**record, "at_epoch": time.time(), "error": traceback.format_exc()},
        )
        raise


def install_colocated_shutdown() -> None:
    """Add terminal resource ownership to the existing library training loop."""
    from swift.megatron.trainers.base import BaseMegatronTrainer

    original = BaseMegatronTrainer.finalize_training
    if getattr(original, "arena_colocated_shutdown", False):
        return

    def finalize(self):
        result = original(self)
        shutdown_colocated_engine(self)
        return result

    finalize.arena_colocated_shutdown = True
    BaseMegatronTrainer.finalize_training = finalize
