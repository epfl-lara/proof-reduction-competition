"""CPU tool model loading cannot inherit training globals or distributed state."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from proof_eval.evidence.immutable import immutable, read, sha
from proof_eval.training import semantic_process


def test_child_environment_masks_gpus_and_rank_without_changing_parent(monkeypatch):
    monkeypatch.setenv("RANK", "7")
    monkeypatch.setenv("WORLD_SIZE", "8")
    monkeypatch.setenv("MASTER_ADDR", "training-host")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0,1,2,3,4,5,6,7")
    environment = semantic_process.semantic_environment()
    assert not {"RANK", "WORLD_SIZE", "MASTER_ADDR"} & set(environment)
    assert environment["CUDA_VISIBLE_DEVICES"] == ""
    assert environment["HF_HUB_OFFLINE"] == "1"
    assert environment["PYTHONPATH"] == str(
        Path(semantic_process.__file__).resolve().parents[2]
    )
    import os

    assert os.environ["RANK"] == "7"
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0,1,2,3,4,5,6,7"


def test_exact_owned_request_and_response_receipts_are_preserved(tmp_path, monkeypatch):
    seen = []
    response = {"kind": "semantic_search", "query": "nat sum", "count": 1}

    def worker(command, **kwargs):
        folder = Path(command[-1])
        request = read(folder / "request.json")
        seen.append((command, request, kwargs))
        pin = immutable(folder / "result.json", response)
        immutable(
            folder / "finished.json",
            {
                "request_sha256": sha(folder / "request.json"),
                "result_sha256": pin,
                "source_sha256": sha(
                    Path(semantic_process.__file__).with_name("semantic_worker.py")
                ),
            },
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", worker)
    result = semantic_process.search_isolated(
        {"frozen": True},
        tmp_path,
        {"op": "semantic_search", "query": "nat sum"},
        "v1",
        tmp_path / "evidence",
    )
    assert result == response
    assert seen[0][0][1:3] == ["-m", "proof_eval.training.semantic_worker"]
    assert seen[0][1]["config"] == {"frozen": True}
    assert seen[0][2]["env"]["CUDA_VISIBLE_DEVICES"] == ""
    folder = Path(seen[0][0][-1])
    assert read(folder / "exit.json")["returncode"] == 0
    assert read(folder / "intent.json")["automatic_retry"] is False


def test_runtime_tool_fault_is_not_an_argument_error_or_reward(tmp_path, monkeypatch):
    def worker(command, **kwargs):
        immutable(
            Path(command[-1]) / "failed.json",
            {"type": "AttributeError", "error": "rope_theta"},
        )
        return SimpleNamespace(returncode=2)

    monkeypatch.setattr(subprocess, "run", worker)
    with pytest.raises(semantic_process.SemanticProcessError, match="rope_theta"):
        semantic_process.search_isolated(
            {}, tmp_path, {"op": "semantic_search"}, "v1", tmp_path / "evidence"
        )
    assert len(list((tmp_path / "evidence").iterdir())) == 1


def test_invalid_model_argument_keeps_the_host_argument_error_contract(
    tmp_path, monkeypatch
):
    def worker(command, **kwargs):
        immutable(
            Path(command[-1]) / "failed.json",
            {"type": "ValueError", "error": "Use one nonempty semantic query string"},
        )
        return SimpleNamespace(returncode=2)

    monkeypatch.setattr(subprocess, "run", worker)
    with pytest.raises(ValueError, match="nonempty"):
        semantic_process.search_isolated(
            {}, tmp_path, {"op": "semantic_search"}, "v1", tmp_path / "evidence"
        )


def test_timeout_never_retries_or_invents_a_tool_result(tmp_path, monkeypatch):
    calls = []

    def worker(command, **kwargs):
        calls.append(command)
        raise subprocess.TimeoutExpired(command, 100)

    monkeypatch.setattr(subprocess, "run", worker)
    with pytest.raises(
        semantic_process.SemanticProcessError, match="exceeded its bound"
    ):
        semantic_process.search_isolated(
            {}, tmp_path, {"op": "semantic_search"}, "v1", tmp_path / "evidence"
        )
    assert len(calls) == 1
    assert not list((tmp_path / "evidence").glob("*/result.json"))
