"""Opt-in host-orchestrated tree search and zero-cost policy replay.

The search records which proof each short agent call started from, which
strategy card it focused on, what it checked and what it cost. Replaying
candidate policies over those records estimates their score and cost without
new model calls, in the manner of Dream-RSI's replay simulator.
"""

from proof_eval.harness.tree.policy import FrontierPolicy, TreeSearch
from proof_eval.harness.tree.replay import dream, evaluate, replay

__all__ = ["FrontierPolicy", "TreeSearch", "dream", "evaluate", "replay"]
