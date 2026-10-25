"""An isolated synthetic GRPO integration fixture, never an Arena training batch."""

from __future__ import annotations

import copy
import hashlib
import os
import re
import time
from pathlib import Path

from proof_eval.evidence.immutable import immutable, read
from proof_eval.training.reward import validate_token_evidence

PURPOSE = "synthetic_gpu_training_check"


def require_fixture(config: dict) -> None:
    if config.get("purpose") != PURPOSE or config.get("reserved_task_ids") != []:
        raise ValueError("GPU training fixture must contain zero reserved Arena tasks")


def fit_synthetic_messages(
    template, context_tokens: int, rank: int
) -> tuple[list, int]:
    """Create a measured full-window prompt without truncating any encoded input."""
    if context_tokens < 1024 or rank not in range(8):
        raise ValueError("Invalid GPU integration fixture configuration")
    target = context_tokens - 128
    tokenizer = copy.copy(template)
    tokenizer.max_length = None
    code = str(70000 + rank)

    def encode(padding):
        messages = [
            {"role": "system", "content": "Return only the latest five-digit code."},
            {"role": "user", "content": "pad " * padding + "Code: " + code},
        ]
        encoded = tokenizer.encode(
            {"messages": messages, "chat_template_kwargs": {"enable_thinking": False}},
            return_length=True,
        )
        return messages, len(encoded["input_ids"])

    low, high = 0, context_tokens * 2
    while low < high:
        middle = (low + high + 1) // 2
        if encode(middle)[1] <= target:
            low = middle
        else:
            high = middle - 1
    messages, measured = encode(low)
    if not context_tokens - 256 <= measured <= target:
        raise ValueError("Synthetic prompt did not reach the declared full context")
    return messages, measured


def register() -> None:
    """Register explicit fixture-only adapters in the real ms-swift trainer."""
    if os.environ.get("ARENA_RL_RUN_PURPOSE") != PURPOSE:
        raise ValueError("Synthetic integration adapter cannot run as Arena RL")
    from mcore_bridge.model.mm_gpt_model import MultimodalGPTModel
    from swift.rewards import ORM, orms
    from swift.rollout.multi_turn import MultiTurnScheduler, multi_turns

    old_forward = MultimodalGPTModel.forward

    def observe_native_positions(self, input_ids, position_ids, *args, **kwargs):
        if not getattr(self, "arena_fixture_positions_recorded", False):
            if self.language_model.position_embedding_type != "mrope":
                raise ValueError(
                    "GPU fixture lost the model's native MRoPE configuration"
                )
            if position_ids.ndim != 3 or position_ids.shape[0] != 3:
                raise ValueError(
                    "GPU fixture did not exercise native three-axis positions"
                )
            if not all(position_ids[0].equal(position_ids[i]) for i in (1, 2)):
                raise ValueError(
                    "Synthetic text unexpectedly contained multimodal geometry"
                )
            config = read(Path(os.environ["ARENA_RL_CONFIG"]))
            rank = int(os.environ["RANK"])
            record = {
                "purpose": PURPOSE,
                "at_epoch": time.time(),
                "rank": rank,
                "position_embedding_type": self.language_model.position_embedding_type,
                "position_shape": list(position_ids.shape),
                "positions_sha256": hashlib.sha256(
                    position_ids.detach().cpu().numpy().tobytes()
                ).hexdigest(),
                "positions_modified": False,
                "input_tokens_truncated": 0,
            }
            for base in (config["root"], config["home"]):
                immutable(
                    Path(base) / "position-compatibility" / f"rank-{rank}.json", record
                )
            self.arena_fixture_positions_recorded = True
        return old_forward(self, input_ids, position_ids, *args, **kwargs)

    MultimodalGPTModel.forward = observe_native_positions

    class Scheduler(MultiTurnScheduler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.config = read(Path(os.environ["ARENA_RL_CONFIG"]))
            require_fixture(self.config)
            self.rank = int(os.environ["RANK"])
            self.trajectory_failures = []

        def put(self, name, record):
            for base in (self.config["root"], self.config["home"]):
                immutable(
                    Path(base) / "synthetic-rollouts" / f"rank-{self.rank}" / name,
                    record,
                )

        async def on_trajectory_start(self, requests):
            if len(requests) != 1:
                raise ValueError("GPU fixture expects exactly one rollout per rank")
            request = requests[0]
            if not request.data_dict.get("fixture_case", "").startswith("gpu-fixture-"):
                raise ValueError("A real task reached the synthetic GPU fixture")
            request.messages, measured = fit_synthetic_messages(
                self._template, self.config["context_tokens"], self.rank
            )
            request.chat_template_kwargs = {"enable_thinking": False}
            self.put(
                "started.json",
                {
                    "purpose": PURPOSE,
                    "at_epoch": time.time(),
                    "uuid": request.uuid,
                    "rank": self.rank,
                    "actual_prompt_tokens": measured,
                    "reserved_Arena_tasks": 0,
                    "messages": request.messages,
                },
            )

        async def on_turn_end(self, infer_request, response_choice, current_turn):
            asymmetric = self.config.get("asymmetric_multi_turn_fixture", False)
            finish_turn = 3 if asymmetric and self.rank in (0, 1, 4, 5) else 1
            if current_turn not in range(1, finish_turn + 1):
                raise ValueError("GPU training fixture has exactly one model turn")
            ids = list(response_choice.token_ids or [])
            logprobs = [
                row["logprob"]
                for row in (response_choice.logprobs or {}).get("content", [])
            ]
            validate_token_evidence(ids, logprobs)
            text = response_choice.message.content or ""
            if str(70000 + self.rank) not in re.findall(r"\b\d{5}\b", text):
                raise ValueError("Full-window synthetic recall failed")
            # Contrived fixture advantages exercise the real backward pass. They
            # are not Arena rewards, performance measurements or reusable weights.
            info = {"purpose": PURPOSE, "fixture_reward": float(self.rank % 2)}
            self.put(
                f"response-{current_turn}.json" if asymmetric else "response.json",
                {
                    **info,
                    "at_epoch": time.time(),
                    "uuid": infer_request.uuid,
                    "completion": text,
                    "sampled_token_ids": ids,
                    "behavior_logprobs": logprobs,
                    "actual_input_messages": infer_request.messages,
                },
            )
            return {"done": current_turn >= finish_turn, "rollout_infos": info}

        def step(self, infer_request, response_choice, current_turn):
            infer_request.messages.append(
                {"role": "user", "content": f"Return only code {70000 + self.rank}."}
            )
            return {"infer_request": infer_request}

    class Reward(ORM):
        def __call__(self, completions, rollout_infos, **kwargs):
            if len(completions) != len(rollout_infos) or any(
                info.get("purpose") != PURPOSE for info in rollout_infos
            ):
                raise ValueError("Synthetic reward adapter received non-fixture data")
            return [info["fixture_reward"] for info in rollout_infos]

    multi_turns["arena_gpu_training_check"] = Scheduler
    orms["arena_gpu_training_check"] = Reward
