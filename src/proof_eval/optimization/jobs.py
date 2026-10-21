"""Proof-keyed deterministic job cache, sharing the immutable original reference."""

import fcntl
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

from proof_eval.evidence.io import digest, fingerprint
from proof_eval.protocol import code_identity
from proof_eval.verification.metrics import validate_candidate
from proof_eval.verification.references import original_evaluation

from .cleanup import BUDGET, METHODS, cleanup_proof


class DeterministicCleanup:
    """Proof-keyed, shared cleanup jobs using the existing ten-method portfolio."""

    def __init__(self, root, pack, evaluator, provenance, guard, *, methods=METHODS):
        self.methods = tuple(methods)
        self.root, self.pack, self.provenance, self.guard = (
            Path(root),
            pack,
            provenance,
            guard,
        )
        original = original_evaluation(pack)
        original_identity = code_identity(pack["row"], pack["row"]["src"])

        class ReferenceAwareEvaluator:
            def __getattr__(self, name):
                return getattr(evaluator, name)

            def evaluate(self, name, code, *, versions="all"):
                if (
                    name == pack["name"]
                    and code_identity(pack["row"], code) == original_identity
                ):
                    return deepcopy(original)
                return evaluator.evaluate(name, code, versions=versions)

        self.evaluator = ReferenceAwareEvaluator()

    def __call__(self, code):
        code = validate_candidate(self.pack["row"], code)[0]
        key = fingerprint(
            {
                "name": self.pack["name"],
                "proof": code,
                "provenance": self.provenance,
                "methods": self.methods,
                "budget": asdict(BUDGET),
            }
        )
        folder = self.root / key
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / ".dispatch.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            reused = (folder / "result.json").exists()
            result = cleanup_proof(
                evaluator=self.evaluator,
                row=self.pack["row"],
                proof=code,
                folder=folder,
                provenance=self.provenance,
                guard=self.guard,
                methods=self.methods,
            )
            return {
                **result,
                "job_path": str(folder),
                "reused": reused,
                "job_result_sha256": digest(folder / "result.json"),
            }
