"""Entry points combining every proof-theoretic signal for one proof body."""

from __future__ import annotations

from typing import Any

from proof_eval.optimization.proof_theory.antiunify import find_shared_subproofs
from proof_eval.optimization.proof_theory.automation import find_automation
from proof_eval.optimization.proof_theory.cuts import find_cuts
from proof_eval.optimization.proof_theory.detours import find_detours
from proof_eval.optimization.proof_theory.focusing import find_phases
from proof_eval.optimization.proof_theory.records import AnalysisConfig, ProofAnalysis
from proof_eval.optimization.proof_theory.tree import TokenCounter, parse
from proof_eval.verification.backend import _masked_comments
from proof_eval.verification.metrics import token_count, validate_candidate


def analyze_proof(body: str, config: AnalysisConfig | None = None) -> ProofAnalysis:
    """Analyze a proof body: the text after `:=`, normally beginning with `by`.

    Line numbers are 1-based within `body`. Comments are masked first, keeping
    every offset. The arena token count covers the whole body.
    """
    config = config or AnalysisConfig()
    text = _masked_comments(body)
    root = parse(text)
    tokens = TokenCounter()
    steps = [step for step in root.walk() if step is not root]
    return ProofAnalysis(
        tokens=token_count(body),
        steps=len(steps),
        max_depth=max((step.depth for step in steps), default=0),
        cuts=tuple(find_cuts(root)),
        detours=tuple(find_detours(root, text)),
        phases=tuple(find_phases(root, tokens, config)),
        shared_subproofs=tuple(find_shared_subproofs(root, tokens, config)),
        automation=tuple(find_automation(root)),
    )


def analyze_declaration(
    row: dict[str, Any], code: str, config: AnalysisConfig | None = None
) -> ProofAnalysis:
    """Validate a full declaration against its benchmark row, then analyze it."""
    _, body = validate_candidate(row, code)
    return analyze_proof(body, config)
