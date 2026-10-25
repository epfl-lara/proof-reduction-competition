"""The real runtime probe is inference-only and refuses bad or failed outputs."""

import re
from types import SimpleNamespace

import pytest

from proof_eval.evidence.immutable import read
from proof_eval.training.gpu_probe import run_probe
from proof_eval.training.reward import UnscorableEpisode


def test_growing_conversations_are_separate_from_training_and_keep_real_options(
    tmp_path,
):
    seen, sync = [], []
    options = SimpleNamespace(max_tokens=8192, temperature=1.0, seed=0)

    def rollout(requests, request_options):
        request = requests[0]
        code = re.findall(r"Code: (\d+)", request.messages[-1]["content"])[-1]
        seen.append((request, request_options))
        return [
            SimpleNamespace(
                response=SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content=code),
                            token_ids=[5, 6],
                            logprobs={
                                "content": [{"logprob": -0.1}, {"logprob": -0.2}]
                            },
                        )
                    ]
                )
            )
        ]

    config = {"root": str(tmp_path / "scratch"), "home": str(tmp_path / "home")}
    run_probe(
        rollout, options, SimpleNamespace, config, 0, lambda x: sync.append(x) or x
    )
    assert len(seen) == len(sync) == 3
    assert [len(r.messages) for r, _ in seen] == [2, 4, 6]
    assert all(r.data_dict == {"purpose": "synthetic_gpu_smoke_only"} for r, _ in seen)
    assert all(o.max_tokens == 64 and o.temperature == 0 for _, o in seen)
    assert (
        options.max_tokens == 8192 and options.temperature == 1.0 and options.seed == 0
    )
    relative = "gpu-preflight/rank-0/finished.json"
    assert read(tmp_path / "home" / relative)["optimizer_steps"] == 0
    assert (tmp_path / "home" / relative).read_bytes() == (
        tmp_path / "scratch" / relative
    ).read_bytes()
    assert not list(tmp_path.rglob("reward.json"))
    assert not list(tmp_path.rglob("step-*.json"))


def test_gpu_error_is_preserved_without_retry_or_training_reward(tmp_path):
    calls = []

    def failed(requests, options):
        calls.append(requests)
        raise RuntimeError("CUDA failure")

    config = {"root": str(tmp_path / "scratch"), "home": str(tmp_path / "home")}
    with pytest.raises(UnscorableEpisode, match="CUDA failure"):
        run_probe(failed, SimpleNamespace(), SimpleNamespace, config, 1, lambda x: x)
    assert len(calls) == 1
    path = tmp_path / "home/gpu-preflight/rank-1"
    assert read(path / "failed.json")["automatic_retry"] is False
    assert not (path / "finished.json").exists()
