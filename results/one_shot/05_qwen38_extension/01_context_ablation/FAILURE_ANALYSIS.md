# One-shot failure analysis

Saved-artifact snapshot: **30/75 results**, `partial_or_unreadable`.

Authoritative evaluator statuses and heuristic error labels are reported separately. Multi-label counts overlap; repeated diagnostics and version failures count once per cell. No models or Lean processes were invoked.

## Recorded evaluator outcomes

| Status | Cells |
|---|---:|
| invalid | 30 |
| not_recorded | 45 |

Unchanged returned incumbents passing every version: **0**. Changed outputs passing every version: **0**. Accepted improvements: **0**.

Extracted proof compared with saved input incumbent after stripping outer whitespace only. Internal whitespace changes count as changed. Missing extraction or input remains distinct; no Lean equivalence is inferred.

## Diagnostic categories

| Heuristic label | Cells | Representative cell |
|---|---:|---|
| generation_truncated | 30 | [FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time](<cells/01604c173b0f7ba9a2cc9e7eda53a6330e131093d03bafd7025d4c7aa00f534c>) |
| not_started | 43 | [Cslib.SKI.parallelReduction_diamond](<cells/06da2795e03af7c57765d967a340cb32c1c4c28dede2e7ddc82803b654e63352>) |
| pending_generation | 2 | [Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress](<cells/b3b20471ea22d3b5fce4213cc9668cc24d162d35224cfb054a5c8ac5eadfafba>) |

## Provider output-token accounting

Non-reasoning completion tokens are derived only from valid provider completion and reasoning counters. They are not independently tokenized final proof tokens. Missing counters stay null; reasoning character counts are never converted to tokens. No reasoning or model text is exported.

| Model | Cells with output count | Completion tokens | Reasoning tokens | Derived non-reasoning tokens | Truncated, empty final |
|---|---:|---:|---:|---:|---:|
| Qwen/Qwen3.8-27B | 30/75 | 983040 | 983040 | 0 | 30 |

Detailed JSON includes source/model/arm groups, per-version recorded statuses, provider counter availability, and diagnostic pointers into each original result. Target `sorryAx` rejection can follow elaboration errors; it does not establish deliberate use of `sorry`. Pending cells are not counted as invalid proofs.
