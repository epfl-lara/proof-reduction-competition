# One-shot strategy and context ablation

Snapshot: **incomplete**, 47/75 cells recorded. Common deterministic incumbent: **46.248122%** local combined score across 15 proofs.

Each model/arm/proof receives one independent request at temperature 0.3, high reasoning, and a 32,768-token output limit. There are no repair calls, automatic transport retries, or cross-arm feedback. A candidate replaces its incumbent only under the frozen 0.05-percentage-point gain policy.

`plain` has the common proof, objective, and environment context. `cards` adds selected strategy cards; `goals` adds actual goal annotations; `cards_goals` combines these. `cards_goals_costs` adds measured costs to the same selected goal sites. No random seed is fixed or repeated draws averaged.

Full-cohort scores are blank until the condition completes. A raw score is also blank if any output could not be scored. Invalid or failed proofs keep their recorded zero score. Selected scores use the incumbent after an unavailable, invalid, or non-improving output. Counts and costs cover recorded cells.

## Scores and passing outputs

| Model | Arm | Recorded | Raw score | Selected score | Gain pp | Primary pass | All versions pass | Improved |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3.8-27B | plain | 10/15 | — | — | — | 0 | 0 | 0 |
| Qwen3.8-27B | cards | 10/15 | — | — | — | 0 | 0 | 0 |
| Qwen3.8-27B | goals | 9/15 | — | — | — | 0 | 0 | 0 |
| Qwen3.8-27B | cards_goals | 9/15 | — | — | — | 0 | 0 | 0 |
| Qwen3.8-27B | cards_goals_costs | 9/15 | — | — | — | 0 | 0 | 0 |

The report JSON includes length, heartbeat, and compatibility axes for raw and selected outputs. Passing counts describe the generated candidate, not the fallback.

## Generation cost and failures

| Model | Arm | Transport errors | Indeterminate | Truncated | Prompt tokens | Completion tokens | Missing usage | Request seconds sum |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3.8-27B | plain | 0 | 0 | 10 | 43,535 | 327,680 | 0 | 5397.0 |
| Qwen3.8-27B | cards | 0 | 0 | 10 | 48,125 | 327,680 | 0 | 5364.8 |
| Qwen3.8-27B | goals | 0 | 0 | 9 | 78,103 | 294,912 | 0 | 4766.1 |
| Qwen3.8-27B | cards_goals | 0 | 0 | 9 | 82,230 | 294,912 | 0 | 4929.0 |
| Qwen3.8-27B | cards_goals_costs | 0 | 0 | 9 | 86,033 | 294,912 | 0 | 4911.7 |

Token counts are provider-reported. Missing usage is not estimated. Concurrent request durations overlap, so their sum is not elapsed experiment time. No monetary price is inferred.

Recorded outcome categories: `generation_truncated`: 47.

## Context preparation

Prepared context for 15 proofs: 88 selected sites, 87 observed goal sites, and 54 sites with incumbent-tactic cost measurements. Goal text is truncated at 33 sites. Unavailable costs are left unmeasured; they are not zeros.

The saved extraction-duration fields sum to 95.871 seconds; 15 saved contexts are marked cached. These recorded timings are not a measurement of fresh preparation time in this generation run. Input hashes and extractor implementation hashes are retained in the report. Costs describe instrumented execution of the original tactic at its state, not a portable tactic price or the replacement's score.

## Paired context comparisons

Each contrast uses the same proof under the same model, with incumbent fallback after each single attempt. Positive values favor the named addition. Full means require every configured pair. This is one stochastic draw on a development cohort; these are descriptive differences, not causal or significant effects.

| Model | Cards − plain | Goals − plain | Cards+goals − plain | Cards+goals+costs − plain | Costs − cards+goals |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3.8-27B | — | — | — | — | — |

The 2×2 card main effect averages `(cards − plain)` and `(cards_goals − goals)`. The goal main effect averages `(goals − plain)` and `(cards_goals − cards)`. The interaction is `cards_goals − cards − goals + plain`. Cost context is isolated only by `cards_goals_costs − cards_goals`.

| Model | Card main effect pp | Goal main effect pp | Interaction pp |
| --- | ---: | ---: | ---: |
| Qwen3.8-27B | — | — | — |

## Per-problem evidence

Use [per_problem.csv](per_problem.csv) for candidate outcomes, gains, source, and request hashes, [source_results.csv](source_results.csv) for source-level means, and [pairwise.csv](pairwise.csv) for the individual paired comparisons. [report.json](report.json) records full axis metrics, error-category counts, provenance hashes, partial observations, and all contrast denominators.

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
