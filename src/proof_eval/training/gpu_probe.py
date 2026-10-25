"""Synthetic GPU conversation checks; no Arena examples, rewards or optimizer."""

from __future__ import annotations

import copy
import re
import time
from pathlib import Path
from typing import Any, Callable

from proof_eval.evidence.immutable import immutable
from proof_eval.training.reward import UnscorableEpisode, validate_token_evidence


def run_probe(
    rollout: Callable[..., list],
    request_config: Any,
    request_type: Any,
    config: dict,
    rank: int,
    synchronize: Callable[[list], list],
) -> None:
    """Exercise growing contexts in the actual loaded distributed rollout engine."""
    relative = Path("gpu-preflight") / f"rank-{rank}"

    def put(name: str, value: dict) -> None:
        for base in (config["root"], config["home"]):
            immutable(Path(base) / relative / name, value)

    put(
        "started.json",
        {
            "at_epoch": time.time(),
            "purpose": "synthetic_gpu_smoke_only",
            "rounds": 3,
            "maximum_output_tokens_per_round": 64,
            "training_examples": 0,
            "optimizer_steps": 0,
            "active_engine": config.get("observed_gpu_engine"),
        },
    )
    messages = [
        {
            "role": "system",
            "content": "Return only the latest five-digit code provided by the user.",
        }
    ]
    try:
        for turn, padding in enumerate((500, 6000, 17000)):
            code = str(70000 + rank * 100 + turn)
            messages.append(
                {"role": "user", "content": "pad " * padding + "Code: " + code}
            )
            request = request_type(
                messages=copy.deepcopy(messages),
                uuid=f"arena-gpu-probe-{rank}-{turn}",
                data_dict={"purpose": "synthetic_gpu_smoke_only"},
                chat_template_kwargs={"enable_thinking": False},
            )
            options = copy.copy(request_config)
            options.max_tokens, options.temperature, options.seed = 64, 0, 7919 + turn
            failure = []
            try:
                outputs = rollout([request], options)
                if len(outputs) != 1:
                    raise ValueError("GPU probe response count changed")
                choice = outputs[0].response.choices[0]
                text = choice.message.content or ""
                ids = list(choice.token_ids or [])
                logprobs = [
                    r["logprob"] for r in (choice.logprobs or {}).get("content", [])
                ]
                validate_token_evidence(ids, logprobs)
                put(
                    f"turn-{turn:02d}.json",
                    {
                        "purpose": "synthetic_gpu_smoke_only",
                        "messages": request.messages,
                        "response": text,
                        "sampled_token_ids": ids,
                        "behavior_logprobs": logprobs,
                        "expected_code": code,
                    },
                )
                if code not in re.findall(r"\b\d{5}\b", text):
                    raise ValueError("GPU conversation probe did not retain its code")
                messages.append({"role": "assistant", "content": text})
            except Exception as error:
                failure = [
                    {"rank": rank, "phase": f"gpu-probe-{turn}", "error": str(error)}
                ]
            failures = synchronize(failure)
            if failures:
                raise UnscorableEpisode(
                    "GPU preflight failed before training: " + str(failures)
                )
        put(
            "finished.json",
            {
                "status": "passed",
                "at_epoch": time.time(),
                "rounds": 3,
                "optimizer_steps": 0,
            },
        )
    except BaseException as error:
        put(
            "failed.json",
            {"at_epoch": time.time(), "error": str(error), "automatic_retry": False},
        )
        raise
