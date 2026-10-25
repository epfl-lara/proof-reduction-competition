"""The GPU fixture cannot consume real tasks or silently shorten its context."""

import pytest

from proof_eval.training.gpu_training_probe import (
    PURPOSE,
    fit_synthetic_messages,
    register,
    require_fixture,
)


def test_fixture_requires_explicit_empty_arena_reserve():
    require_fixture({"purpose": PURPOSE, "reserved_task_ids": []})
    for config in (
        {},
        {"purpose": PURPOSE},
        {"purpose": PURPOSE, "reserved_task_ids": ["real"]},
    ):
        with pytest.raises(ValueError, match="zero reserved Arena tasks"):
            require_fixture(config)


def test_full_context_is_measured_without_changing_template_or_truncating():
    class Template:
        max_length = 7

        def encode(self, value, *, return_length):
            assert self.max_length is None
            assert value["chat_template_kwargs"] == {"enable_thinking": False}
            length = len(value["messages"][-1]["content"].split()) + 20
            return {"input_ids": list(range(length))}

    template = Template()
    messages, measured = fit_synthetic_messages(template, 32768, 5)
    assert 32512 <= measured <= 32640
    assert messages[-1]["content"].endswith("Code: 70005")
    assert template.max_length == 7


def test_fixture_adapter_cannot_register_in_real_training(monkeypatch):
    monkeypatch.delenv("ARENA_RL_RUN_PURPOSE", raising=False)
    with pytest.raises(ValueError, match="cannot run as Arena RL"):
        register()
