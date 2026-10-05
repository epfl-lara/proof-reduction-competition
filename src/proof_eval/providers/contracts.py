"""Interfaces between an agent transport and the host-owned tool service."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ToolSession(Protocol):
    seed_code: str

    def dispatch(self, request: dict) -> dict: ...


class AgentGenerator(Protocol):
    def __call__(
        self,
        *,
        folder: Path,
        messages: list[dict[str, str]],
        model: str,
        effort: str,
        mode: str,
        session: ToolSession,
        context: dict,
        expected_cli: dict,
        provider: str = "codex",
    ) -> dict: ...
