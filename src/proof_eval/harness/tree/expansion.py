"""One expansion's view of the host session: a parent seed and a check budget.

The provider executor reads only `seed_code` and the tool service calls only
`dispatch`. Every operation is delegated to the shared host `ProofSession`, so
the ledger, best-proof selection and all-version acceptance stay host-owned.
After `max_checks` check requests the host refuses further checks without
compiling them; the agent should then finish. `status` and check feedback
still report the global best proof, so branches are not fully isolated.
"""

from __future__ import annotations

import threading

BUDGET_MESSAGE = (
    "This expansion's check budget is used up. Call status if needed, then "
    "finish with a short factual reason and return your best declaration."
)


class ExpansionSession:
    def __init__(self, session, parent_code: str, max_checks: int):
        self.session = session
        self.seed_code = parent_code
        self.max_checks = max_checks
        self.used = 0
        self.lock = threading.Lock()

    def dispatch(self, request: dict) -> dict:
        if request.get("op") == "check":
            with self.lock:
                if self.used >= self.max_checks:
                    return {
                        "kind": "expansion_check_budget_reached",
                        "stop": True,
                        "message": BUDGET_MESSAGE,
                    }
                self.used += 1
        return self.session.dispatch(request)
