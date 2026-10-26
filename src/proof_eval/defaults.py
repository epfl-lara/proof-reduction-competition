"""Shared defaults for fresh Qwen Flash-Next benchmark runs.

Historical configurations and frozen runtime copies retain their saved values.
"""

VERIFICATION_TIMEOUT_SECONDS = 600.0
QWEN_TIMEOUT_SECONDS = 8 * 60 * 60
LOCAL_QWEN_WORKERS = 10
QWEN_CONTEXT_TOKENS = 266400
QWEN_COMPACTION_TOKENS = 222400
QWEN_TIME_RESTARTS = 10000
