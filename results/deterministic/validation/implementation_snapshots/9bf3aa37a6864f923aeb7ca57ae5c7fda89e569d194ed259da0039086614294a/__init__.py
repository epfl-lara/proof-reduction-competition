"""Public Lean evaluation API. Importing this package has no runtime effects."""

from .verification.api import EvaluationNotReady, Evaluator

__all__ = ["EvaluationNotReady", "Evaluator"]
