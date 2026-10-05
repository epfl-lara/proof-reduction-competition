"""Wire harness policy into the provider's general agent transport."""

from proof_eval.providers import codex
from proof_eval.providers.registry import adapter

from .prompts import tool_instructions
from .service import ProofToolService


def command(**kwargs) -> list[str]:
    return codex.command(**kwargs, instructions=tool_instructions(kwargs["mode"]))


def generate(*, provider: str = "codex", **kwargs) -> dict:
    return adapter(provider).generate(
        **kwargs,
        instructions=tool_instructions(kwargs["mode"]),
        tool_service=ProofToolService,
    )
