"""Wire harness policy into the provider's general agent transport."""

from proof_eval.providers import codex

from .prompts import tool_instructions
from .service import ProofToolService


def command(**kwargs) -> list[str]:
    return codex.command(**kwargs, instructions=tool_instructions(kwargs["mode"]))


def generate(**kwargs) -> dict:
    return codex.generate(
        **kwargs,
        instructions=tool_instructions(kwargs["mode"]),
        tool_service=ProofToolService,
    )
