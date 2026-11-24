"""Configuration and immutable result records of the proof-theoretic analysis."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

SATURATION = "saturation"
DECISION = "decision"


@dataclass(frozen=True)
class AnalysisConfig:
    """Thresholds for proposal signals; they do not change any token count."""

    min_subproof_tokens: int = 10
    min_similarity: float = 0.7
    min_length_ratio: float = 0.5
    max_phase_step_tokens: int = 30


@dataclass(frozen=True)
class Cut:
    """A local lemma (`have`, `let`, `obtain`, ...) and its textual usage.

    `references` counts later same-scope mentions up to a rebinding of the name.
    `ambient_consumer` records later automation that can use facts unnamed.
    """

    kind: str
    names: tuple[str, ...]
    line: int
    statement_tokens: int
    proof_tokens: int
    references: int
    ambient_consumer: bool
    term_proof: bool

    @property
    def usage(self) -> str:
        if self.references == 0:
            return "dead" if not self.ambient_consumer else "unnamed_use_possible"
        return "linear" if self.references == 1 else "shared"

    @property
    def alias(self) -> bool:
        """A proof of at most three tokens, such as `h.1` or `hx`."""
        return 0 < self.proof_tokens <= 3 and self.references > 0


@dataclass(frozen=True)
class Detour:
    """An introduction immediately followed by its elimination (a redex)."""

    kind: str
    line: int
    text: str


@dataclass(frozen=True)
class Phase:
    """A focusing phase: consecutive sibling steps fusable into one step.

    Asynchronous steps (`intro`, destructuring, `ext`) are invertible and fuse
    into an `rintro`/`obtain` pattern. Synchronous steps choose a witness or
    disjunct (`exists`, `use`, `left`) and fuse into an anonymous constructor.
    """

    kind: str
    line: int
    steps: tuple[str, ...]
    tokens: int


@dataclass(frozen=True)
class SharedSubproof:
    """Two disjoint subproofs and their anti-unifier.

    `verdict` is `alpha` (consistent renaming), `dual` (mirror names), or
    `instance` (a variable versus a term: one generalized lemma, two uses),
    otherwise `template(k)` with `k` structural differences.
    """

    first_line: int
    second_line: int
    similarity: float
    verdict: str
    holes: tuple[tuple[str, str], ...]
    saving_tokens: int

    @property
    def generalizable(self) -> bool:
        return self.verdict in {"alpha", "dual", "instance"}


@dataclass(frozen=True)
class AutomationCall:
    """A searching tactic and the number of named local facts in scope."""

    kind: str
    tactic: str
    line: int
    context_size: int


@dataclass(frozen=True)
class ProofAnalysis:
    tokens: int
    steps: int
    max_depth: int
    cuts: tuple[Cut, ...]
    detours: tuple[Detour, ...]
    phases: tuple[Phase, ...]
    shared_subproofs: tuple[SharedSubproof, ...]
    automation: tuple[AutomationCall, ...]

    def summary(self) -> dict[str, Any]:
        """JSON-compatible counts and token upper bounds for reporting."""
        cuts = self.cuts
        usage = Counter(cut.usage for cut in cuts)
        linear = [c for c in cuts if c.usage == "linear" and not c.alias]
        shared = self.shared_subproofs
        saturation = [a for a in self.automation if a.kind == SATURATION]
        return {
            "tokens": self.tokens,
            "steps": self.steps,
            "max_depth": self.max_depth,
            "cuts": len(cuts),
            "cut_usage": dict(sorted(usage.items())),
            "cut_statement_tokens": sum(c.statement_tokens for c in cuts),
            "alias_cut_tokens": sum(c.statement_tokens for c in cuts if c.alias),
            "linear_term_statement_tokens": sum(
                c.statement_tokens for c in linear if c.term_proof
            ),
            "linear_tactic_statement_tokens": sum(
                c.statement_tokens for c in linear if not c.term_proof
            ),
            "dead_cut_tokens": sum(
                c.statement_tokens + c.proof_tokens for c in cuts if c.usage == "dead"
            ),
            "detours": dict(sorted(Counter(d.kind for d in self.detours).items())),
            "asynchronous_phase_tokens": sum(
                p.tokens for p in self.phases if p.kind == "asynchronous"
            ),
            "synchronous_phase_tokens": sum(
                p.tokens for p in self.phases if p.kind == "synchronous"
            ),
            "shared_subproofs": dict(
                sorted(Counter(s.verdict for s in shared).items())
            ),
            "cut_introduction_tokens": sum(
                s.saving_tokens for s in shared if s.generalizable
            ),
            "template_tokens": sum(
                s.saving_tokens for s in shared if not s.generalizable
            ),
            "saturation_calls": len(saturation),
            "decision_calls": sum(1 for a in self.automation if a.kind == DECISION),
            "max_saturation_context": max(
                (a.context_size for a in saturation), default=0
            ),
        }
