"""Fresh original starts over an explicitly pinned Arena host snapshot."""

from __future__ import annotations

from copy import deepcopy

from proof_eval.harness.session import ProofSession
from proof_eval.verification.references import require_valid


class TrainingProofSession(ProofSession):
    """Supply a fresh baseline before the host's first durable state write.

    Earlier sealed host releases lack the original_measurement constructor
    argument. This adapter leaves those sources intact and uses their normal
    tool dispatcher and ledger. A rollout always owns a new empty session.
    """

    def __init__(self, *args, original_measurement: dict, **kwargs):
        self._training_original = deepcopy(original_measurement)
        super().__init__(*args, **kwargs)

    def _save_state(self):
        if self._training_original is not None:
            if self.checks or self.finished is not None or self.cache:
                raise ValueError(
                    "A training session must begin with empty private state"
                )
            original = self._training_original
            require_valid(original, self.row, self.row["src"])
            if any(
                v.get("cached") is not False for v in original["per_version"].values()
            ):
                raise ValueError("A training baseline requires fresh original checks")
            self.original = original
            self.seed_code, self.seed_evaluation = self.row["src"], original
            self.best_code, self.best_evaluation = self.row["src"], deepcopy(original)
            self._training_original = None
        return super()._save_state()

    def source(self, request):
        if request.get("op") != "semantic_search":
            return super().source(request)
        from proof_eval.training.semantic_process import search_isolated

        tools = self.source_tools
        if not set(request) <= {"op", "version", "query", "limit", "packages"}:
            raise ValueError("Unsupported source fields")
        version = request.get("version") or tools.versions[0]
        if version not in tools.versions:
            raise ValueError("Version outside this theorem")
        project = tools.evaluator.projects[(tools.row["source"], version)].resolve()
        return search_isolated(
            tools.semantic_config,
            project,
            request,
            version,
            self.folder / "isolated-tool-evidence",
        )
