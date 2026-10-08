"""Quality gates preserve real tasks and cannot hide a shortage of long proofs."""

from __future__ import annotations

from collections import Counter

import pytest

from proof_eval.benchmark.quality import (
    QualityConfig,
    band_targets,
    intake_reason,
    select_like_benchmark,
    shape_summary,
    token_band,
)
from proof_eval.verification.metrics import token_count


def candidate(name, tokens, *, source="a", group=None, signature=None):
    return {
        "name": name,
        "source": source,
        "proof_length": tokens,
        "file_path": f"{name}.lean",
        "training_metadata": {
            "id": name,
            "split_group": group or name,
            "signature_key": signature or name,
            "content_key": name,
        },
    }


def test_match_keeps_benchmark_length_distribution_and_exact_row_objects():
    reference = [{"proof_length": value} for value in [250, 300, 850, 1250, 1900]]
    rows = [
        candidate(f"{source}_{band}_{i}", length, source=source)
        for source in ["a", "b"]
        for band, length in enumerate([350, 700, 1300, 2000, 3000])
        for i in range(20)
    ]
    config = QualityConfig()
    selected = select_like_benchmark(rows, reference, limit=25, config=config)
    assert Counter(token_band(r["proof_length"]) for r in selected) == {
        0: 10,
        1: 5,
        2: 5,
        3: 5,
    }
    assert {r["source"] for r in selected} == {"a", "b"}
    assert all(any(r is original for original in rows) for r in selected)
    assert selected == select_like_benchmark(
        list(reversed(rows)), reference, limit=25, config=config
    )


def test_no_short_task_fallback_when_long_band_is_missing():
    rows = [candidate(str(i), 300) for i in range(20)]
    reference = [{"proof_length": 300}, {"proof_length": 2000}]
    with pytest.raises(ValueError, match="Insufficient distinct tasks"):
        select_like_benchmark(rows, reference, limit=10, config=QualityConfig())


def test_duplicate_statements_and_project_cap_apply_across_files():
    rows = [candidate(str(i), 300, group="project") for i in range(10)]
    rows += [candidate("other", 300, source="b", signature="0")]
    config = QualityConfig(max_per_group=2)
    selected = select_like_benchmark(
        rows, [{"proof_length": 300}], limit=2, config=config
    )
    assert len({r["training_metadata"]["signature_key"] for r in selected}) == 2
    with pytest.raises(ValueError, match="selected 2, required 3"):
        select_like_benchmark(
            rows[:10], [{"proof_length": 300}], limit=3, config=config
        )


def test_intake_rejects_tautologies_without_mislabeling_contradiction_lemmas():
    config = QualityConfig(min_tokens=1, min_proof_lines=1)

    def row(statement, body):
        return {
            "statement": statement,
            "src": f"{statement} := {body}",
            "proof_length": token_count(body),
        }

    assert intake_reason(row("theorem t : True", "by trivial"), config) == (
        "trivial_true_target"
    )
    assert intake_reason(row("theorem t (x : Nat) : x = x", "by rfl"), config) == (
        "reflexive_target"
    )
    assert (
        intake_reason(row("theorem t (h : False) : False", "by exact h"), config)
        is None
    )
    bad = row("theorem t (h : False) : False", "by exact h")
    bad["proof_length"] += 1
    assert intake_reason(bad, config) == "incorrect_token_denominator"


def test_shape_counts_only_uncommented_proof_body():
    statement = "/-- A long docstring that is context, not proof. -/\ntheorem t : True"
    body = "by\n  -- a comment\n  trivial"
    row = {
        "source": "example",
        "statement": statement,
        "src": statement + " := " + body,
        "proof_length": token_count(body),
    }
    summary = shape_summary([row])
    assert summary["proof_tokens"]["median"] == 2
    assert summary["proof_nonempty_lines"]["median"] == 2
    assert sum(band_targets([row], 2108)) == 2108
