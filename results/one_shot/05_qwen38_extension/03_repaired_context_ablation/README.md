# Context ablation with correctness-only repairs

**incomplete**: 47/75 initial proposals recorded; 47/75 repair outcomes complete. The shared deterministic incumbent averages **46.248122%** local combined score on the 15-proof declared cohort.

Each cell starts from one saved optimization proposal and permits up to **3 correctness-only debugging calls**. The debugger sees compiler validity feedback and the known-valid incumbent; it receives no candidate scores, heartbeat measurements, or reward feedback. It stops at the first proof passing all required versions. Final score comparison occurs only after debugging ends. Empty initial output is not regenerated.

Generation settings remain temperature 0.3, high reasoning, and 32,768 output tokens. This protocol is one optimization proposal plus bounded repairs, not one HTTP request. Initial calls and additional repair calls are counted separately.

## Candidate scores and validity

Raw scores concern the generated candidate. Selected scores retain the incumbent when the final proposal is invalid, unavailable, or not accepted. Unknown infrastructure results leave a raw mean blank; failed or invalid declarations contribute zero. Full means remain blank until their own declared cohort completes. Initial proposals can finish before their repair outcomes.

| Model | Arm | Initial / repaired / expected | Initial raw | Repaired raw | Selected | Gain pp | Valid initial / final | Incumbent returned | Improved |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3.8-27B | plain | 10/10/15 | — | — | — | — | 0/0 | 0 | 0 |
| Qwen3.8-27B | cards | 10/10/15 | — | — | — | — | 0/0 | 0 | 0 |
| Qwen3.8-27B | goals | 9/9/15 | — | — | — | — | 0/0 | 0 | 0 |
| Qwen3.8-27B | cards_goals | 9/9/15 | — | — | — | — | 0/0 | 0 | 0 |
| Qwen3.8-27B | cards_goals_costs | 9/9/15 | — | — | — | — | 0/0 | 0 | 0 |

Among completed repair cells: 0 initially invalid proposals became all-version valid; 0 returned the unchanged incumbent after debugging. There are 0 valid changed proposals and 0 accepted improvements. Validity recovery alone is not proof optimization. The JSON also records initial-selected scores and the paired gain due to repair.

## Additional calls and costs

Counts include saved generations and durable request-start markers, including pending repairs. An attempt without a saved generation has unknown usage. Token counts are provider-reported; reasoning tokens, where reported, are a subset of completion tokens and must not be added a second time.

| Model | Arm | Initial calls | Extra repair calls | Repair pending | Initial prompt / completion | Repair prompt / completion | Repair trunc. | Repair empty-final trunc. with reasoning | Repair request seconds sum |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3.8-27B | plain | 10 | 0 | 0 | 43,535/327,680 | 0/0 | 0 | 0 | 0.0 |
| Qwen3.8-27B | cards | 10 | 0 | 0 | 48,125/327,680 | 0/0 | 0 | 0 | 0.0 |
| Qwen3.8-27B | goals | 10 | 0 | 0 | 78,103/294,912 | 0/0 | 0 | 0 | 0.0 |
| Qwen3.8-27B | cards_goals | 10 | 0 | 0 | 82,230/294,912 | 0/0 | 0 | 0 | 0.0 |
| Qwen3.8-27B | cards_goals_costs | 9 | 0 | 0 | 86,033/294,912 | 0/0 | 0 | 0 | 0.0 |

Initial / repair generation failures: transport 0/0, indeterminate 0/0, length-truncated 47/0. Missing usage affects 0/0 saved generations. Request seconds are summed overlapping durations, not end-to-end wall time. No monetary price is inferred.

## Paired effects of the initial context

The original arms differ in cards, goal annotations, and original-tactic cost context. Debugging uses the same correctness-only message contract for all arms. Each comparison pairs the same model and proof, using final incumbent-selected scores. Different repair-call counts mean these are not matched-cost comparisons. One stochastic proposal per cell provides descriptive evidence, not statistical significance.

| Model | Cards − plain | Goals − plain | Cards+goals − plain | Cards+goals+costs − plain | Costs − cards+goals |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3.8-27B | — | — | — | — | — |

Card main effect = average of `(cards − plain)` and `(cards_goals − goals)`; goal main effect = average of `(goals − plain)` and `(cards_goals − cards)`; interaction = `cards_goals − cards − goals + plain`. Cost context is isolated by `cards_goals_costs − cards_goals`. The JSON reports the same contrasts on accepted-improvement rates.

| Model | Card effect pp | Goal effect pp | Interaction pp |
| --- | ---: | ---: | ---: |
| Qwen3.8-27B | — | — | — |

## Evidence

[report.json](report.json) records per-axis scores, exact completion denominators, outcomes, repair-round counts, generation statistics, source summaries, and artifact hashes. [per_problem.csv](per_problem.csv) separates initial, repaired, and fallback-selected results for each proposal. [source_results.csv](source_results.csv) and [pairwise.csv](pairwise.csv) expose source-level and paired effects. No pooled best-of-models or best-of-arms submission is constructed.

Complete original-cohort conditions receive their own `conditions/<model>__<arm>/selected_candidates.jsonl` and manifest with source request keys, repair-result hashes, selected metrics, and submission hash. Partial or subset cohorts do not produce full submissions.

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
