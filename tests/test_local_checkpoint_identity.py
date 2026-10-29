"""A fine-tuned checkpoint keeps its own identity and the full Qwen budget."""

import json
import sys
import time
from types import SimpleNamespace

from proof_eval.harness.config import RunConfig
from proof_eval.providers import capacity_probe, lemex_local
from proof_eval.providers.costs import rate_card
from proof_eval.providers.registry import MODEL_TRACKS


def test_proofopt_uses_open_model_defaults_and_its_own_cost_identity():
    model = lemex_local.PROOFOPT_SFT_MODEL
    config = RunConfig(provider="lemex-local", conditions=((model, "xhigh"),))
    assert config.workers == 10 and config.problem_timeout_seconds == 28800
    assert config.budget_tracking == "time"
    assert config.original_measurement_policy == "prepared"
    assert not config.restart_history and not config.deterministic
    assert config.verification_timeout_seconds == 600
    assert MODEL_TRACKS[model] == "open"
    assert model in rate_card("lemex-local")["unpriced_models"]


def test_capacity_requests_target_the_selected_checkpoint(tmp_path, monkeypatch):
    model = lemex_local.PROOFOPT_SFT_MODEL
    payloads = []

    class Tokenizer:
        def encode(self, value, **kwargs):
            return list(value.encode())

        def decode(self, value):
            return bytes(value).decode()

        def apply_chat_template(self, *args, **kwargs):
            return [1] * 56

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            AutoTokenizer=SimpleNamespace(from_pretrained=lambda *a, **k: Tokenizer())
        ),
    )
    monkeypatch.setattr(
        capacity_probe,
        "metrics",
        lambda *a: {"vllm:num_requests_running": 1, "vllm:num_preemptions_total": 0},
    )

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps({"choices": [{"text": "Silver-6832-Cedar"}]}).encode()

        def __iter__(self):
            yield b'data: {"choices":[{"text":"synthetic output"}]}\n'
            time.sleep(2.1)  # Let the actual sampler observe the active stream.
            yield b'data: {"usage":{"prompt_tokens":56,"completion_tokens":8}}\n'

    def request(value, **kwargs):
        payload = json.loads(value.data)
        payloads.append(payload)
        return Response(payload)

    monkeypatch.setattr(capacity_probe, "urlopen", request)
    receipt = capacity_probe.exercise_full_context(
        "http://127.0.0.1:1/v1",
        tmp_path,
        tmp_path / "capacity",
        1,
        model=model,
        context_tokens=64,
        output_tokens=8,
    )
    assert len(payloads) == 2
    assert all(p["model"] == model for p in payloads)
    assert receipt["model"] == model and receipt["status"] == "pressure_passed"
