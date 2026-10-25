"""Terminal engine ownership without inference, optimizer or GPU execution."""

import json
import sys
from types import SimpleNamespace

import pytest

from proof_eval.training import shutdown


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    config = {"home": str(tmp_path / "home"), "root": str(tmp_path / "scratch")}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setenv("ARENA_RL_CONFIG", str(path))
    monkeypatch.setenv("RANK", "3")
    monkeypatch.setenv("ARENA_RL_RUN_PURPOSE", "synthetic_gpu_training_check")
    events = []
    state = {"sleeping": True, "offloaded": False}

    def offload(trainer):
        events.append("offload")
        state["offloaded"] = True

    def wake():
        assert state["offloaded"], "Do not remap inference over trainer GPU storage"
        events.append("wake")
        state["sleeping"] = False

    def close():
        assert not state["sleeping"], "Do not free asleep cuMem pools"
        events.append("shutdown")

    monkeypatch.setattr(shutdown, "_offload_training_state", offload)
    llm = SimpleNamespace(
        llm_engine=SimpleNamespace(
            is_sleeping=lambda: state["sleeping"],
            wake_up=wake,
            engine_core=SimpleNamespace(shutdown=close),
        )
    )
    trainer = SimpleNamespace(
        use_vllm=True, vllm_mode="colocate", engine=SimpleNamespace(engine=llm)
    )
    return trainer, events, state, config


def test_remaps_before_free_and_preserves_mirrored_terminal_receipts(runtime):
    trainer, events, _, config = runtime
    shutdown.shutdown_colocated_engine(trainer)
    assert events == ["offload", "wake", "shutdown"]
    from pathlib import Path

    relative = "trainer-shutdown/rank-3/finished.json"
    a = Path(config["home"]) / relative
    b = Path(config["root"]) / relative
    assert a.read_bytes() == b.read_bytes()
    result = json.loads(a.read_bytes())
    assert result["status"] == "passed" and result["new_model_requests"] == 0
    assert result["purpose"] == "synthetic_gpu_training_check"


def test_already_awake_engine_is_not_woken_twice(runtime):
    trainer, events, state, _ = runtime
    state["sleeping"] = False
    shutdown.shutdown_colocated_engine(trainer)
    assert events == ["offload", "shutdown"]


@pytest.mark.parametrize("field,value", [("use_vllm", False), ("vllm_mode", "server")])
def test_other_training_modes_are_unchanged(runtime, monkeypatch, field, value):
    trainer, events, _, _ = runtime
    setattr(trainer, field, value)
    monkeypatch.delenv("ARENA_RL_CONFIG")
    shutdown.shutdown_colocated_engine(trainer)
    assert events == []


def test_explicit_shutdown_is_not_repeated(runtime):
    trainer, events, _, _ = runtime
    shutdown.shutdown_colocated_engine(trainer)
    shutdown.shutdown_colocated_engine(trainer)
    assert events == ["offload", "wake", "shutdown"]


def test_shutdown_failure_is_saved_and_propagated(runtime):
    trainer, events, _, config = runtime

    def failure():
        raise RuntimeError("real lifecycle failure")

    trainer.engine.engine.llm_engine.wake_up = failure
    with pytest.raises(RuntimeError, match="real lifecycle failure"):
        shutdown.shutdown_colocated_engine(trainer)
    assert events == ["offload"]
    from pathlib import Path

    failed = Path(config["home"]) / "trainer-shutdown/rank-3/failed.json"
    assert "real lifecycle failure" in json.loads(failed.read_bytes())["error"]
    assert not getattr(trainer, "arena_colocated_engine_closed", False)


def test_finalizer_runs_library_completion_before_shutdown(monkeypatch):
    events = []
    trainer_class = type(
        "Trainer",
        (),
        {"finalize_training": lambda self: events.append("library_finished")},
    )
    module = SimpleNamespace(BaseMegatronTrainer=trainer_class)
    monkeypatch.setitem(sys.modules, "swift.megatron.trainers.base", module)
    monkeypatch.setattr(
        shutdown, "shutdown_colocated_engine", lambda trainer: events.append("shutdown")
    )
    shutdown.install_colocated_shutdown()
    shutdown.install_colocated_shutdown()
    trainer_class().finalize_training()
    assert events == ["library_finished", "shutdown"]


def test_failed_training_is_not_promoted_to_terminal_success(monkeypatch):
    events = []

    def failed(self):
        raise RuntimeError("training failed before completion")

    trainer_class = type("Trainer", (), {"finalize_training": failed})
    monkeypatch.setitem(
        sys.modules,
        "swift.megatron.trainers.base",
        SimpleNamespace(BaseMegatronTrainer=trainer_class),
    )
    monkeypatch.setattr(
        shutdown, "shutdown_colocated_engine", lambda trainer: events.append("shutdown")
    )
    shutdown.install_colocated_shutdown()
    with pytest.raises(RuntimeError, match="training failed before completion"):
        trainer_class().finalize_training()
    assert events == []


def test_pinned_image_exposes_the_lifecycle_apis():
    helpers = pytest.importorskip("swift.megatron.trainers.utils")
    llm = pytest.importorskip("vllm.v1.engine.llm_engine")
    client = pytest.importorskip("vllm.v1.engine.core_client")
    assert callable(helpers.offload_megatron_model_to_cpu)
    assert callable(helpers.offload_megatron_optimizer)
    assert callable(llm.LLMEngine.is_sleeping) and callable(llm.LLMEngine.wake_up)
    assert callable(client.InprocClient.shutdown)
