"""Convenience top-level entrypoint and alias for RCP communication."""

import sys
from pathlib import Path

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

from proof_eval.rcp import (
    DEFAULT_MODEL,
    DEFAULT_RCP_BASE_URL,
    DEFAULT_REASONING,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_TEMPERATURE,
    MODELS,
    RCPChat,
    RCPClient,
    RCPResponse,
    find_env_file,
    load_rcp_env,
    main,
    map_rcp_reasoning,
    normalize_model_name,
    parse_env_file,
)

__all__ = [
    "RCPClient",
    "RCPChat",
    "RCPResponse",
    "MODELS",
    "DEFAULT_MODEL",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_REASONING",
    "DEFAULT_REASONING_EFFORT",
    "DEFAULT_RCP_BASE_URL",
    "load_rcp_env",
    "find_env_file",
    "parse_env_file",
    "normalize_model_name",
    "map_rcp_reasoning",
    "main",
]

if __name__ == "__main__":
    main()
