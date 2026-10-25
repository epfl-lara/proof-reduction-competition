"""Distributed tool faults rendezvous on CPU before the next model collective."""

import importlib.util
import json
import multiprocessing
from datetime import timedelta

import pytest


def rank_process(rank, root):
    from pathlib import Path

    import torch.distributed as dist

    from proof_eval.training.coordinated_failure import gather_failures

    dist.init_process_group(
        "gloo",
        init_method="file://" + root + "/store",
        rank=rank,
        world_size=2,
        timeout=timedelta(seconds=30),
    )
    first = gather_failures([])
    local = (
        [{"rank": rank, "error": "rope_theta", "reward_assigned": False}]
        if rank == 0
        else []
    )
    failures = gather_failures(local)
    Path(root, "rank-" + str(rank) + ".json").write_text(
        json.dumps({"initial": first, "failures": failures})
    )
    dist.destroy_process_group()


@pytest.mark.skipif(
    importlib.util.find_spec("torch") is None,
    reason="Actual CPU distributed runtime is checked in the pinned image",
)
def test_one_rank_tool_fault_reaches_both_ranks_without_gpu_collectives(tmp_path):
    context = multiprocessing.get_context("spawn")
    children = [
        context.Process(target=rank_process, args=(rank, str(tmp_path)))
        for rank in range(2)
    ]
    for child in children:
        child.start()
    try:
        for child in children:
            child.join(35)
        assert all(not child.is_alive() and child.exitcode == 0 for child in children)
    finally:
        for child in children:
            if child.is_alive():
                child.terminate()
                child.join(5)
    values = [
        json.loads((tmp_path / ("rank-" + str(rank) + ".json")).read_text())
        for rank in range(2)
    ]
    assert values[0] == values[1]
    assert values[0]["initial"] == []
    assert values[0]["failures"] == [
        {"rank": 0, "error": "rope_theta", "reward_assigned": False}
    ]
