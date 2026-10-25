"""Real native multi-turn control flow on eight CPU-only distributed ranks."""

import json
import os
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest


def _native_worker(rank, rendezvous, base):
    import torch.distributed as distributed

    os.environ.update(
        RANK=str(rank),
        WORLD_SIZE="8",
        LOCAL_RANK=str(rank),
        LOCAL_WORLD_SIZE="8",
        MASTER_ADDR="127.0.0.1",
        MASTER_PORT="29501",
        ACCELERATE_USE_CPU="true",
    )
    distributed.init_process_group(
        "gloo",
        init_method=rendezvous,
        rank=rank,
        world_size=8,
        timeout=timedelta(seconds=20),
    )
    try:
        from swift.megatron.trainers import rollout_mixin
        from swift.rollout import agent_loop

        from proof_eval.training.rollout_collectives import install_colocated_world_sync

        for ranks in ([0, 1, 4, 5], [2, 3, 6, 7]):
            group = distributed.new_group(ranks=ranks, backend="gloo")
            if rank in ranks:
                local_group = group
        rollout_mixin.mpu.get_model_parallel_group = lambda: local_group
        # Only response carriers are synthetic; the actual library loop,
        # distributed gathers and early-finished rank behavior run unchanged.
        agent_loop.RolloutOutput = SimpleNamespace
        install_colocated_world_sync()
        calls = []
        finish_turn = 3 if rank in (0, 1, 4, 5) else 1

        def output():
            choice = SimpleNamespace(
                token_ids=[100 + rank],
                logprobs={"content": [{"logprob": -0.1}]},
                message=SimpleNamespace(content="synthetic"),
            )
            return SimpleNamespace(response=SimpleNamespace(choices=[choice]))

        class Scheduler:
            def append_assistant_completion(self, request, text):
                request.messages.append({"role": "assistant", "content": text})
                return False

            def snapshot_and_materialize_assistant_messages(self, request):
                return None

            def restore_assistant_message_snapshots(self, snapshots):
                pass

            async def on_turn_end(self, request, choice, turn):
                return {"done": turn >= finish_turn}

            def check_finished(self, request, choice, turn):
                return False

            def get_response_token_data(self, request, choice, **kwargs):
                return list(choice.token_ids), [1]

            def step(self, request, choice, turn):
                request.messages.append({"role": "user", "content": "next"})
                return {"infer_request": request}

            def set_assistant_message_token_ids(self, request, tokens):
                pass

        def infer(requests, config):
            calls.append(len(requests))
            # This represents the all-eight-rank inference collective. A
            # four-rank early exit would leave the remaining ranks blocked.
            distributed.barrier()
            return [output() for _ in requests]

        request = SimpleNamespace(messages=[{"role": "user", "content": "start"}])
        outputs = rollout_mixin.run_multi_turn(
            requests=[request],
            first_turn_outputs=[output()],
            scheduler=Scheduler(),
            rollout_fn=infer,
            request_config=None,
            max_turns=3,
            gather_fn=lambda flags: rollout_mixin.gather_object(
                flags, group=local_group
            ),
        )
        assert len(outputs) == 1
        assert outputs[0].response_token_ids == [[100 + rank]] * finish_turn
        assert outputs[0].response_loss_mask == [[1]] * finish_turn
        assert len(calls) == 3
        assert calls == ([1, 1, 0] if finish_turn == 3 else [0, 0, 0])
        (Path(base) / f"rank-{rank}-passed.json").write_text(
            json.dumps(
                {
                    "rank": rank,
                    "calls": calls,
                    "turns": finish_turn,
                    "model_calls": 0,
                    "optimizer_steps": 0,
                }
            )
        )
    finally:
        distributed.destroy_process_group()


@pytest.mark.skipif(
    os.environ.get("ARENA_TEST_NATIVE_COLLECTIVES") != "1",
    reason="Explicit pinned-image CPU-only eight-rank integration check",
)
def test_native_multi_turn_keeps_early_finished_ranks_in_shared_inference(
    tmp_path, monkeypatch
):
    import torch.multiprocessing as multiprocessing

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    config = {
        "home": str(tmp_path / "home"),
        "root": str(tmp_path / "root"),
        "colocate_multi_turn_world_sync": True,
    }
    for key in ("home", "root"):
        Path(config[key]).mkdir()
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setenv("ARENA_RL_CONFIG", str(path))
    monkeypatch.setenv("ARENA_RL_RUN_PURPOSE", "model_free_collective_check")
    multiprocessing.start_processes(
        _native_worker,
        args=("file://" + str(tmp_path / "gloo-rendezvous"), str(tmp_path)),
        nprocs=8,
        join=True,
        start_method="spawn",
    )
    assert len(list(tmp_path.glob("rank-*-passed.json"))) == 8
    for rank in range(8):
        receipt = json.loads(
            (
                tmp_path / "home" / "rollout-collectives" / f"rank-{rank}.json"
            ).read_text()
        )
        assert len(receipt["original_rollout_group"]) == 4
        assert receipt["continuation_liveness_group"] == list(range(8))
        assert receipt["input_output_tokens_modified"] is False
