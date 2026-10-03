# Context ablation with correctness-only repairs

**complete**: 225/225 initial proposals recorded; 225/225 repair outcomes complete. The shared deterministic incumbent averages **46.248122%** local combined score on the 15-proof declared cohort.

Each cell starts from one saved optimization proposal and permits up to **3 correctness-only debugging calls**. The debugger sees compiler validity feedback and the known-valid incumbent; it receives no candidate scores, heartbeat measurements, or reward feedback. It stops at the first proof passing all required versions. Final score comparison occurs only after debugging ends. Empty initial output is not regenerated.

Generation settings remain temperature 0.3, high reasoning, and 32,768 output tokens. This protocol is one optimization proposal plus bounded repairs, not one HTTP request. Initial calls and additional repair calls are counted separately.

## Candidate scores and validity

Raw scores concern the generated candidate. Selected scores retain the incumbent when the final proposal is invalid, unavailable, or not accepted. Unknown infrastructure results leave a raw mean blank; failed or invalid declarations contribute zero. Full means remain blank until their own declared cohort completes. Initial proposals can finish before their repair outcomes.

| Model | Arm | Initial / repaired / expected | Initial raw | Repaired raw | Selected | Gain pp | Valid initial / final | Incumbent returned | Improved |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | plain | 15/15/15 | 0.000 | 0.000 | 46.248 | +0.000 | 0/0 | 0 | 0 |
| DeepSeek-V4.1-Flash | cards | 15/15/15 | 2.282 | 15.773 | 48.470 | +2.222 | 1/4 | 1 | 2 |
| DeepSeek-V4.1-Flash | goals | 15/15/15 | 5.494 | 8.566 | 47.267 | +1.018 | 1/2 | 0 | 2 |
| DeepSeek-V4.1-Flash | cards_goals | 15/15/15 | 0.000 | 2.722 | 46.434 | +0.186 | 0/1 | 0 | 1 |
| DeepSeek-V4.1-Flash | cards_goals_costs | 15/15/15 | 4.098 | 13.578 | 48.124 | +1.876 | 1/4 | 2 | 1 |
| Qwen3.5-397B-A17B | plain | 15/15/15 | 2.160 | — | 46.363 | +0.115 | 1/7 | 1 | 2 |
| Qwen3.5-397B-A17B | cards | 15/15/15 | 2.634 | — | 46.482 | +0.233 | 1/9 | 2 | 3 |
| Qwen3.5-397B-A17B | goals | 15/15/15 | — | — | 46.260 | +0.012 | 3/9 | 3 | 1 |
| Qwen3.5-397B-A17B | cards_goals | 15/15/15 | 4.701 | — | 46.627 | +0.379 | 2/9 | 1 | 3 |
| Qwen3.5-397B-A17B | cards_goals_costs | 15/15/15 | — | — | 47.380 | +1.132 | 1/7 | 2 | 2 |
| Qwen3.6-35B-A3B | plain | 15/15/15 | 0.000 | 13.447 | 46.396 | +0.148 | 0/5 | 2 | 1 |
| Qwen3.6-35B-A3B | cards | 15/15/15 | 0.000 | 15.286 | 46.248 | +0.000 | 0/6 | 5 | 0 |
| Qwen3.6-35B-A3B | goals | 15/15/15 | 0.000 | 31.418 | 46.348 | +0.100 | 0/10 | 7 | 1 |
| Qwen3.6-35B-A3B | cards_goals | 15/15/15 | 2.677 | 18.178 | 46.248 | +0.000 | 1/7 | 4 | 0 |
| Qwen3.6-35B-A3B | cards_goals_costs | 15/15/15 | 0.000 | 15.681 | 46.248 | +0.000 | 0/6 | 1 | 0 |

Among completed repair cells: 74 initially invalid proposals became all-version valid; 30 returned the unchanged incumbent after debugging. There are 55 valid changed proposals and 19 accepted improvements. Validity recovery alone is not proof optimization. The JSON also records initial-selected scores and the paired gain due to repair.

## Additional calls and costs

Counts include saved generations and durable request-start markers, including pending repairs. An attempt without a saved generation has unknown usage. Token counts are provider-reported; reasoning tokens, where reported, are a subset of completion tokens and must not be added a second time.

| Model | Arm | Initial calls | Extra repair calls | Repair pending | Initial prompt / completion | Repair prompt / completion | Repair trunc. | Repair empty-final trunc. with reasoning | Repair request seconds sum |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | plain | 15 | 1 | 0 | 68,327/488,581 | 4,401/32,768 | 1 | 1 | 341.5 |
| DeepSeek-V4.1-Flash | cards | 15 | 6 | 0 | 74,631/473,807 | 30,073/109,877 | 1 | 1 | 1151.7 |
| DeepSeek-V4.1-Flash | goals | 15 | 1 | 0 | 147,368/485,296 | 13,399/6,600 | 0 | 0 | 70.2 |
| DeepSeek-V4.1-Flash | cards_goals | 15 | 2 | 0 | 153,672/475,308 | 15,733/51,889 | 1 | 1 | 541.9 |
| DeepSeek-V4.1-Flash | cards_goals_costs | 15 | 6 | 0 | 158,947/481,854 | 48,579/62,776 | 1 | 1 | 673.3 |
| Qwen3.5-397B-A17B | plain | 15 | 30 | 0 | 66,948/54,038 | 196,288/76,646 | 0 | 0 | 25250.9 |
| Qwen3.5-397B-A17B | cards | 15 | 26 | 0 | 73,848/53,676 | 157,169/79,099 | 0 | 0 | 21347.0 |
| Qwen3.5-397B-A17B | goals | 15 | 16 | 0 | 127,013/47,948 | 91,803/54,410 | 0 | 0 | 14172.0 |
| Qwen3.5-397B-A17B | cards_goals | 15 | 22 | 0 | 153,822/49,284 | 143,255/69,128 | 0 | 0 | 15967.3 |
| Qwen3.5-397B-A17B | cards_goals_costs | 15 | 29 | 0 | 147,703/39,102 | 193,334/71,716 | 0 | 0 | 23931.3 |
| Qwen3.6-35B-A3B | plain | 15 | 25 | 0 | 66,948/290,630 | 171,653/268,765 | 0 | 0 | 1882.2 |
| Qwen3.6-35B-A3B | cards | 15 | 19 | 0 | 73,848/258,048 | 127,387/260,193 | 3 | 3 | 1850.8 |
| Qwen3.6-35B-A3B | goals | 15 | 23 | 0 | 146,922/176,020 | 154,113/286,362 | 3 | 3 | 1974.4 |
| Qwen3.6-35B-A3B | cards_goals | 15 | 28 | 0 | 153,822/184,743 | 189,312/317,237 | 1 | 1 | 2253.3 |
| Qwen3.6-35B-A3B | cards_goals_costs | 15 | 27 | 0 | 160,166/187,548 | 164,151/340,604 | 3 | 3 | 2395.9 |

Initial / repair generation failures: transport 3/13, indeterminate 0/0, length-truncated 73/14. Missing usage affects 3/13 saved generations. Request seconds are summed overlapping durations, not end-to-end wall time. No monetary price is inferred.

## Paired effects of the initial context

The original arms differ in cards, goal annotations, and original-tactic cost context. Debugging uses the same correctness-only message contract for all arms. Each comparison pairs the same model and proof, using final incumbent-selected scores. Different repair-call counts mean these are not matched-cost comparisons. One stochastic proposal per cell provides descriptive evidence, not statistical significance.

| Model | Cards − plain | Goals − plain | Cards+goals − plain | Cards+goals+costs − plain | Costs − cards+goals |
| --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | +2.222 | +1.018 | +0.186 | +1.876 | +1.690 |
| Qwen3.5-397B-A17B | +0.119 | -0.103 | +0.265 | +1.018 | +0.753 |
| Qwen3.6-35B-A3B | -0.148 | -0.048 | -0.148 | -0.148 | +0.000 |

Card main effect = average of `(cards − plain)` and `(cards_goals − goals)`; goal main effect = average of `(goals − plain)` and `(cards_goals − cards)`; interaction = `cards_goals − cards − goals + plain`. Cost context is isolated by `cards_goals_costs − cards_goals`. The JSON reports the same contrasts on accepted-improvement rates.

| Model | Card effect pp | Goal effect pp | Interaction pp |
| --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | +0.695 | -0.509 | -3.055 |
| Qwen3.5-397B-A17B | +0.243 | +0.021 | +0.249 |
| Qwen3.6-35B-A3B | -0.124 | -0.024 | +0.048 |

## Evidence

[report.json](report.json) records per-axis scores, exact completion denominators, outcomes, repair-round counts, generation statistics, source summaries, and artifact hashes. [per_problem.csv](per_problem.csv) separates initial, repaired, and fallback-selected results for each proposal. [source_results.csv](source_results.csv) and [pairwise.csv](pairwise.csv) expose source-level and paired effects. No pooled best-of-models or best-of-arms submission is constructed.

Complete original-cohort conditions receive their own `conditions/<model>__<arm>/selected_candidates.jsonl` and manifest with source request keys, repair-result hashes, selected metrics, and submission hash. Partial or subset cohorts do not produce full submissions.

Available condition submissions: [DeepSeek-V4.1-Flash / plain](conditions/DeepSeek-V4.1-Flash__plain/selected_candidates.jsonl); [DeepSeek-V4.1-Flash / cards](conditions/DeepSeek-V4.1-Flash__cards/selected_candidates.jsonl); [DeepSeek-V4.1-Flash / goals](conditions/DeepSeek-V4.1-Flash__goals/selected_candidates.jsonl); [DeepSeek-V4.1-Flash / cards_goals](conditions/DeepSeek-V4.1-Flash__cards_goals/selected_candidates.jsonl); [DeepSeek-V4.1-Flash / cards_goals_costs](conditions/DeepSeek-V4.1-Flash__cards_goals_costs/selected_candidates.jsonl); [Qwen3.5-397B-A17B / plain](conditions/Qwen3.5-397B-A17B__plain/selected_candidates.jsonl); [Qwen3.5-397B-A17B / cards](conditions/Qwen3.5-397B-A17B__cards/selected_candidates.jsonl); [Qwen3.5-397B-A17B / goals](conditions/Qwen3.5-397B-A17B__goals/selected_candidates.jsonl); [Qwen3.5-397B-A17B / cards_goals](conditions/Qwen3.5-397B-A17B__cards_goals/selected_candidates.jsonl); [Qwen3.5-397B-A17B / cards_goals_costs](conditions/Qwen3.5-397B-A17B__cards_goals_costs/selected_candidates.jsonl); [Qwen3.6-35B-A3B / plain](conditions/Qwen3.6-35B-A3B__plain/selected_candidates.jsonl); [Qwen3.6-35B-A3B / cards](conditions/Qwen3.6-35B-A3B__cards/selected_candidates.jsonl); [Qwen3.6-35B-A3B / goals](conditions/Qwen3.6-35B-A3B__goals/selected_candidates.jsonl); [Qwen3.6-35B-A3B / cards_goals](conditions/Qwen3.6-35B-A3B__cards_goals/selected_candidates.jsonl); [Qwen3.6-35B-A3B / cards_goals_costs](conditions/Qwen3.6-35B-A3B__cards_goals_costs/selected_candidates.jsonl).

## Limits

- One initial optimization proposal plus up to three correctness-only debugging calls; this is not a single HTTP call.
- The first all-version-valid proposal stops debugging. Scores affect only final incumbent selection, not feedback or continuation.
- A return to the supplied incumbent is counted separately from a valid changed proposal and an accepted improvement.
- Empty output, infrastructure failure, or exhausted repair budget can leave a proposal unusable; fallback is reported separately.
- Unknown infrastructure outcomes have null raw scores. Invalid and failed declarations score zero.
- Context effects are descriptive paired differences from one stochastic proposal per cell, not statistical significance or causal proof.
- Conditions can consume different numbers of repair calls; paired score differences are not equal-cost comparisons.
- Request durations overlap under concurrency; saved duration sums are not experiment wall time. Missing usage is not estimated.
- This report reads saved artifacts, does not recompile proofs, and creates no pooled best-of-arms portfolio.

Rebuild from saved artifacts without model calls or Lean execution:

```bash
python src/report_repair_matrix.py --input results/one_shot/03_repaired_context_ablation
```

Use `--base PATH` if the initial experiment was relocated, or `--output PATH` for a separate report snapshot.
