"""Explicit provider routing and supported benchmark conditions."""

from __future__ import annotations

from types import ModuleType

from . import claude, codex, lemex

DEFAULT_CONDITIONS = {
    "codex": (("gpt-6.1-sol", "max"), ("gpt-6-astra", "max")),
    "lemex": ((lemex.MODEL, "high"),),
    "claude": ((claude.MODEL, "max"),),
}


def adapter(provider: str) -> ModuleType:
    try:
        return {"codex": codex, "lemex": lemex, "claude": claude}[provider]
    except KeyError:
        raise ValueError("Unknown agent provider: " + provider) from None


def validate(provider: str, conditions: tuple | list) -> None:
    adapter(provider)
    allowed = set(DEFAULT_CONDITIONS[provider])
    if provider == "lemex":
        allowed = {
            (model, e) for model, efforts in lemex.MODELS.items() for e in efforts
        }
    if not conditions or any(tuple(c) not in allowed for c in conditions):
        raise ValueError("Unsupported model/effort for " + provider)
