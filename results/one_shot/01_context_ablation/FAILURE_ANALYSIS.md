# One-shot failure analysis

Saved-artifact snapshot: **225/225 results**, `complete`.

Authoritative evaluator statuses and heuristic error labels are reported separately. Multi-label counts overlap; repeated diagnostics and version failures count once per cell. No models or Lean processes were invoked.

## Recorded evaluator outcomes

| Status | Cells |
|---|---:|
| failed | 137 |
| invalid | 73 |
| passed | 12 |
| unavailable | 3 |

Unchanged returned incumbents passing every version: **1**. Changed outputs passing every version: **11**. Accepted improvements: **6**.

Extracted proof compared with saved input incumbent after stripping outer whitespace only. Internal whitespace changes count as changed. Missing extraction or input remains distinct; no Lean equivalence is inferred.

## Diagnostic categories

| Heuristic label | Cells | Representative cell |
|---|---:|---|
| evaluation_unavailable | 3 | [putnam_1995_a3](<cells/0bea29b9472d366239f483774f99dc76c6ff1c0162a6125ecf27aef2129e1f10>) |
| generation_truncated | 73 | [Core.InitsUpdatesComm](<cells/00a1c09d39a06a15594198cdfbcbc5fa5cb994b8efa16f093c7faf154bb8caf4>) |
| lean_missing_name | 31 | [Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius](<cells/0a5670bdd174c517fc0933377151ce9628c5f9f0359d96aeb144d2b8b74411c8>) |
| lean_other_failure | 57 | [Cslib.CCS.bisimilarity_congr_choice](<cells/01bfe7b951ba873af4e128bd667f09782ad606331038494db6093b2c9d1db502>) |
| lean_resource_limit | 1 | [Binius.BinaryBasefold.fold_advances_evaluation_poly](<cells/c6ad28d966ce1a46b5a74b1574bcb6673ff38159448194f89bbfc18757a4aff2>) |
| lean_syntax_error | 16 | [Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius](<cells/0a5670bdd174c517fc0933377151ce9628c5f9f0359d96aeb144d2b8b74411c8>) |
| lean_tactic_failure | 69 | [Core.InitsUpdatesComm](<cells/035c19e20211425cad1cb303e7996b0181881618f079eda3220aa6c7c68fca3b>) |
| lean_type_mismatch | 76 | [Core.InitsUpdatesComm](<cells/035c19e20211425cad1cb303e7996b0181881618f079eda3220aa6c7c68fca3b>) |
| lean_unknown_tactic | 3 | [Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress](<cells/67bac31b04a8102b55ce834dff036c15811952e61f8b1270c8c6d02efff52c93>) |
| lean_unsolved_goals | 51 | [Core.InitsUpdatesComm](<cells/035c19e20211425cad1cb303e7996b0181881618f079eda3220aa6c7c68fca3b>) |
| transport_error | 3 | [putnam_1995_a3](<cells/0bea29b9472d366239f483774f99dc76c6ff1c0162a6125ecf27aef2129e1f10>) |
| verification_marker_missing | 136 | [Cslib.CCS.bisimilarity_congr_choice](<cells/01bfe7b951ba873af4e128bd667f09782ad606331038494db6093b2c9d1db502>) |
| verification_rejected_sorry | 114 | [Cslib.CCS.bisimilarity_congr_choice](<cells/01bfe7b951ba873af4e128bd667f09782ad606331038494db6093b2c9d1db502>) |

## Provider output-token accounting

Non-reasoning completion tokens are derived only from valid provider completion and reasoning counters. They are not independently tokenized final proof tokens. Missing counters stay null; reasoning character counts are never converted to tokens. No reasoning or model text is exported.

| Model | Cells with output count | Completion tokens | Reasoning tokens | Derived non-reasoning tokens | Truncated, empty final |
|---|---:|---:|---:|---:|---:|
| Qwen/Qwen3.5-397B-A17B | 72/75 | 244048 | 140516 | 103532 | 0 |
| Qwen/Qwen3.6-35B-A3B | 75/75 | 1096989 | 1021141 | 75848 | 10 |
| deepseek-ai/DeepSeek-V4.1-Flash | 75/75 | 2404846 | 2387115 | 17731 | 60 |

Detailed JSON includes source/model/arm groups, per-version recorded statuses, provider counter availability, and diagnostic pointers into each original result. Target `sorryAx` rejection can follow elaboration errors; it does not establish deliberate use of `sorry`. Pending cells are not counted as invalid proofs.
