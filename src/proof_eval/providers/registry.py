"""Explicit provider routing and supported benchmark conditions."""

from __future__ import annotations

from types import ModuleType
from typing import Literal

from . import agy, claude, codex, lemex

DEFAULT_CONDITIONS = {
    "codex": (("gpt-6.1-sol", "max"), ("gpt-6-astra", "max")),
    "lemex": ((lemex.MODEL, "high"),),
    "claude": ((claude.MODEL, "max"),),
    "agy": ((agy.MODEL, "high"),),
}
# Experiment contract: routing additions must declare their track separately.
# Preparation pins this source along with the runtime; changes require a new run.
MODEL_TRACKS: dict[str, Literal["open", "closed"]] = {
    "deepseek-ai/DeepSeek-V4.1-Flash": "open",
    "Qwen/Qwen3.8-Flash-Next": "open",
    "gpt-6.1-sol": "closed",
    "gpt-6-astra": "closed",
    "claude-opus-5-5": "closed",
    "gemini-3.8-flash": "closed",
}
OPEN_MODELS = frozenset(
    model for model, track in MODEL_TRACKS.items() if track == "open"
)
# Explicit per-provider allow-list; Codex stays limited to its active conditions.
ALLOWED_CONDITIONS = {
    "codex": set(DEFAULT_CONDITIONS["codex"]),
    "claude": set(DEFAULT_CONDITIONS["claude"]),
    "lemex": {(m, e) for m, efforts in lemex.MODELS.items() for e in efforts},
    "agy": {(m, e) for m, efforts in agy.MODELS.items() for e in efforts},
}


def adapter(provider: str) -> ModuleType:
    try:
        return {"codex": codex, "lemex": lemex, "claude": claude, "agy": agy}[provider]
    except KeyError:
        raise ValueError("Unknown agent provider: " + provider) from None


def validate(provider: str, conditions: tuple | list) -> None:
    adapter(provider)
    if not conditions or any(
        tuple(c) not in ALLOWED_CONDITIONS[provider] for c in conditions
    ):
        raise ValueError("Unsupported model/effort for " + provider)
