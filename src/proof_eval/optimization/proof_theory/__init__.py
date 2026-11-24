"""Lean-free proof-theoretic analysis of tactic proof bodies.

The analysis reads a proof's source text and reports structures named by proof
theory: cuts (local lemmas) and their usage, detours (introductions immediately
eliminated), focusing phases (invertible and synchronous tactic runs), repeated
subproofs found by anti-unification, and automation run in large contexts.

Every result is a proposal signal for later compiler-checked transformations.
The tactic tree is recovered from indentation, not from Lean's parser; names
are matched textually, not resolved. Automation can consume an unreferenced
fact, and two similar subproofs need not have a common generalization that
elaborates. Token savings are therefore upper bounds, never measured scores.
Nothing here compiles Lean, edits a proof, or reads reference measurements.
"""

from proof_eval.optimization.proof_theory.analysis import (
    analyze_declaration,
    analyze_proof,
)
from proof_eval.optimization.proof_theory.antiunify import (
    DUAL_NAMES,
    classify_holes,
    dualize,
)
from proof_eval.optimization.proof_theory.records import (
    DECISION,
    SATURATION,
    AnalysisConfig,
    AutomationCall,
    Cut,
    Detour,
    Phase,
    ProofAnalysis,
    SharedSubproof,
)

__all__ = [
    "DECISION",
    "DUAL_NAMES",
    "SATURATION",
    "AnalysisConfig",
    "AutomationCall",
    "Cut",
    "Detour",
    "Phase",
    "ProofAnalysis",
    "SharedSubproof",
    "analyze_declaration",
    "analyze_proof",
    "classify_holes",
    "dualize",
]
