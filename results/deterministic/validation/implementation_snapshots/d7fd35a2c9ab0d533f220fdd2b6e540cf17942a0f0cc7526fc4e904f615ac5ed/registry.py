"""Explicit provider routing and supported benchmark conditions."""

from __future__ import annotations

from types import ModuleType

from . import agy, claude, codex, lemex

DEFAULT_CONDITIONS = {
    "codex": (("gpt-6.1-sol", "max"), ("gpt-6-astra", "max")),
    "lemex": ((lemex.MODEL, "high"),),
    "claude": ((claude.MODEL, "max"),),
    "agy": ((agy.MODEL, "high"),),
}
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
