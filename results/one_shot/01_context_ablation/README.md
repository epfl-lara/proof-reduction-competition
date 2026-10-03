# One-shot strategy and context ablation

Snapshot: **complete**, 225/225 cells recorded. Common deterministic incumbent: **46.248122%** local combined score across 15 proofs.

Each model/arm/proof receives one independent request at temperature 0.3, high reasoning, and a 32,768-token output limit. There are no repair calls, automatic transport retries, or cross-arm feedback. A candidate replaces its incumbent only under the frozen 0.05-percentage-point gain policy.

`plain` has the common proof, objective, and environment context. `cards` adds selected strategy cards; `goals` adds actual goal annotations; `cards_goals` combines these. `cards_goals_costs` adds measured costs to the same selected goal sites. No random seed is fixed or repeated draws averaged.

Full-cohort scores are blank until the condition completes. A raw score is also blank if any output could not be scored. Invalid or failed proofs keep their recorded zero score. Selected scores use the incumbent after an unavailable, invalid, or non-improving output. Counts and costs cover recorded cells.

## Scores and passing outputs

| Model | Arm | Recorded | Raw score | Selected score | Gain pp | Primary pass | All versions pass | Improved |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | plain | 15/15 | 0.000 | 46.248 | +0.000 | 0 | 0 | 0 |
| DeepSeek-V4.1-Flash | cards | 15/15 | 2.282 | 46.248 | +0.000 | 1 | 1 | 0 |
| DeepSeek-V4.1-Flash | goals | 15/15 | 5.494 | 46.854 | +0.606 | 1 | 1 | 1 |
| DeepSeek-V4.1-Flash | cards_goals | 15/15 | 0.000 | 46.248 | +0.000 | 0 | 0 | 0 |
| DeepSeek-V4.1-Flash | cards_goals_costs | 15/15 | 4.098 | 48.124 | +1.876 | 1 | 1 | 1 |
| Qwen3.5-397B-A17B | plain | 15/15 | 2.160 | 46.248 | +0.000 | 1 | 1 | 0 |
| Qwen3.5-397B-A17B | cards | 15/15 | 2.634 | 46.346 | +0.098 | 1 | 1 | 1 |
| Qwen3.5-397B-A17B | goals | 15/15 | — | 46.260 | +0.012 | 3 | 3 | 1 |
| Qwen3.5-397B-A17B | cards_goals | 15/15 | 4.701 | 46.252 | +0.004 | 2 | 2 | 1 |
| Qwen3.5-397B-A17B | cards_goals_costs | 15/15 | — | 47.021 | +0.773 | 1 | 1 | 1 |
| Qwen3.6-35B-A3B | plain | 15/15 | 0.000 | 46.248 | +0.000 | 0 | 0 | 0 |
| Qwen3.6-35B-A3B | cards | 15/15 | 0.000 | 46.248 | +0.000 | 0 | 0 | 0 |
| Qwen3.6-35B-A3B | goals | 15/15 | 0.000 | 46.248 | +0.000 | 0 | 0 | 0 |
| Qwen3.6-35B-A3B | cards_goals | 15/15 | 2.677 | 46.248 | +0.000 | 1 | 1 | 0 |
| Qwen3.6-35B-A3B | cards_goals_costs | 15/15 | 0.000 | 46.248 | +0.000 | 0 | 0 | 0 |

The report JSON includes length, heartbeat, and compatibility axes for raw and selected outputs. Passing counts describe the generated candidate, not the fallback.

## Generation cost and failures

| Model | Arm | Transport errors | Indeterminate | Truncated | Prompt tokens | Completion tokens | Missing usage | Request seconds sum |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | plain | 0 | 0 | 14 | 68,327 | 488,581 | 0 | 5248.8 |
| DeepSeek-V4.1-Flash | cards | 0 | 0 | 11 | 74,631 | 473,807 | 0 | 5040.8 |
| DeepSeek-V4.1-Flash | goals | 0 | 0 | 13 | 147,368 | 485,296 | 0 | 5104.5 |
| DeepSeek-V4.1-Flash | cards_goals | 0 | 0 | 13 | 153,672 | 475,308 | 0 | 5003.2 |
| DeepSeek-V4.1-Flash | cards_goals_costs | 0 | 0 | 12 | 158,947 | 481,854 | 0 | 5140.1 |
| Qwen3.5-397B-A17B | plain | 0 | 0 | 0 | 66,948 | 54,038 | 0 | 6144.7 |
| Qwen3.5-397B-A17B | cards | 0 | 0 | 0 | 73,848 | 53,676 | 0 | 7036.3 |
| Qwen3.5-397B-A17B | goals | 2 | 0 | 0 | 127,013 | 47,948 | 2 | 11620.7 |
| Qwen3.5-397B-A17B | cards_goals | 0 | 0 | 0 | 153,822 | 49,284 | 0 | 7806.1 |
| Qwen3.5-397B-A17B | cards_goals_costs | 1 | 0 | 0 | 147,703 | 39,102 | 1 | 8441.9 |
| Qwen3.6-35B-A3B | plain | 0 | 0 | 4 | 66,948 | 290,630 | 0 | 2164.4 |
| Qwen3.6-35B-A3B | cards | 0 | 0 | 4 | 73,848 | 258,048 | 0 | 1913.1 |
| Qwen3.6-35B-A3B | goals | 0 | 0 | 0 | 146,922 | 176,020 | 0 | 1297.3 |
| Qwen3.6-35B-A3B | cards_goals | 0 | 0 | 1 | 153,822 | 184,743 | 0 | 1437.2 |
| Qwen3.6-35B-A3B | cards_goals_costs | 0 | 0 | 1 | 160,166 | 187,548 | 0 | 1466.3 |

Token counts are provider-reported. Missing usage is not estimated. Concurrent request durations overlap, so their sum is not elapsed experiment time. No monetary price is inferred.

Recorded outcome categories: `evaluation_failed`: 137, `generation_truncated`: 73, `passed`: 12, `transport_error`: 3.

## Context preparation

Prepared context for 15 proofs: 88 selected sites, 87 observed goal sites, and 54 sites with incumbent-tactic cost measurements. Goal text is truncated at 33 sites. Unavailable costs are left unmeasured; they are not zeros.

The saved extraction-duration fields sum to 95.871 seconds; 15 saved contexts are marked cached. These recorded timings are not a measurement of fresh preparation time in this generation run. Input hashes and extractor implementation hashes are retained in the report. Costs describe instrumented execution of the original tactic at its state, not a portable tactic price or the replacement's score.

## Paired context comparisons

Each contrast uses the same proof under the same model, with incumbent fallback after each single attempt. Positive values favor the named addition. Full means require every configured pair. This is one stochastic draw on a development cohort; these are descriptive differences, not causal or significant effects.

| Model | Cards − plain | Goals − plain | Cards+goals − plain | Cards+goals+costs − plain | Costs − cards+goals |
| --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | +0.000 | +0.606 | +0.000 | +1.876 | +1.876 |
| Qwen3.5-397B-A17B | +0.098 | +0.012 | +0.004 | +0.773 | +0.768 |
| Qwen3.6-35B-A3B | +0.000 | +0.000 | +0.000 | +0.000 | +0.000 |

The 2×2 card main effect averages `(cards − plain)` and `(cards_goals − goals)`. The goal main effect averages `(goals − plain)` and `(cards_goals − cards)`. The interaction is `cards_goals − cards − goals + plain`. Cost context is isolated only by `cards_goals_costs − cards_goals`.

| Model | Card main effect pp | Goal main effect pp | Interaction pp |
| --- | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | -0.303 | +0.303 | -0.606 |
| Qwen3.5-397B-A17B | +0.045 | -0.041 | -0.106 |
| Qwen3.6-35B-A3B | +0.000 | +0.000 | +0.000 |

## Per-problem evidence

Use [per_problem.csv](per_problem.csv) for candidate outcomes, gains, source, and request hashes, [source_results.csv](source_results.csv) for source-level means, and [pairwise.csv](pairwise.csv) for the individual paired comparisons. [report.json](report.json) records full axis metrics, error-category counts, provenance hashes, partial observations, and all contrast denominators.

Among the 15 completed conditions in this snapshot, the highest selected score is **deepseek-ai/DeepSeek-V4.1-Flash / cards_goals_costs**, 48.124% (+1.876 pp over the incumbent). This identifies an observed result, not a statistically established best configuration.

Largest individual accepted changes observed so far (each is a separate single-call cell):

| Proof | Model | Arm | Gain pp |
| --- | --- | --- | ---: |
| `Cslib.CCS.bisimilarity_congr_choice` | DeepSeek-V4.1-Flash | cards_goals_costs | +28.141 |
| `Cslib.SKI.parallelReduction_diamond` | Qwen3.5-397B-A17B | cards_goals_costs | +11.588 |
| `putnam_1964_a4` | DeepSeek-V4.1-Flash | goals | +9.095 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | Qwen3.5-397B-A17B | cards | +1.471 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | Qwen3.5-397B-A17B | goals | +0.177 |

## Interpretation limits

- One stochastic draw per cell on a small development cohort; effects are descriptive and not statistically established.
- Fallback-selected scores include the shared incumbent when a request fails or its candidate is not accepted.
- Transport and indeterminate outcomes have unknown raw scores, not zeros; full raw means remain null if any are unavailable.
- Observed partial-cohort means are not full-cohort results and may change as slower cells finish.
- Request duration sums overlap under concurrency and are not end-to-end wall time; missing token usage is uncounted.
- Goal costs describe incumbent-state replay and do not predict replacement cost.
- This report reads saved evaluations; it does not recompile candidates or remeasure references.

Rebuild this snapshot without model calls or reference measurements:

```bash
python src/report_one_shot.py --input results/one_shot/01_context_ablation
```

Add `--portfolio` only after all configured cells finish to export the separate pooled selection.
