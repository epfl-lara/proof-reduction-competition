"""Explicit fixtures for signal-scoped Linux native launches."""

from __future__ import annotations

import os
import sys

import pytest

from proof_eval.providers import signal_scope


@pytest.fixture
def signal_identity():
    if sys.platform != "linux":
        pytest.skip("Signal integration requires the pinned Linux production image")
    if not os.environ.get("PROOF_SIGNAL_SCOPE_BINARY"):
        pytest.skip("Pinned native guard not configured; run the documented Linux gate")
    # The production-image validation driver supplies the already passed binary.
    # Missing or changed guard setup must fail rather than silently skip a gate.
    return signal_scope.configured_identity()
