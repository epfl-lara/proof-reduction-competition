# Harness comparison snapshot

Updated 2026-10-04T23:15:44.918769+00:00. Full means are shown only for complete conditions.

| Stage | Model / effort | Terminal | Historical score | New score |
| --- | --- | ---: | ---: | ---: |
| correctness | gpt-6-astra / low | 15/15 | 57.222638% | 59.407773% |
| correctness | gpt-6-luna / max | 15/15 | 53.045428% | 52.740977% |
| score | gpt-6-astra / max | 15/15 | 78.093430% | 88.384406% |
| score | gpt-6-astra / low | 15/15 | 57.222638% | 78.130010% |
| score | gpt-6-luna / max | 15/15 | 53.045428% | 65.135096% |
| score_edges | gpt-6-astra / max | 15/15 | 78.093430% | 88.043179% |
| score_edges | gpt-6-astra / low | 15/15 | 57.222638% | 79.118309% |
| score_edges | gpt-6-luna / max | 15/15 | 53.045428% | 68.264239% |
| score_each | gpt-6-astra / max | 15/15 | 78.093430% | 86.977844% |
| score_each | gpt-6-astra / low | 15/15 | 57.222638% | 75.301134% |
| score_each | gpt-6-luna / max | 15/15 | 53.045428% | 61.320048% |
| model_config | gpt-6.1-sol / max | 15/15 | — | 87.342215% |
| model_config | gpt-6-astra / high | 15/15 | — | 84.319957% |

| Model / effort | Gain over stage 01 | Mean gain after first changed valid proposal | Agent checks | Completion tokens |
| --- | ---: | ---: | ---: | ---: |
| gpt-6-astra / max | no stage-01 control | +12.267598 pp | 286 | 339,648 |
| gpt-6-astra / low | +18.722237 pp | +11.649248 pp | 116 | 61,335 |
| gpt-6-luna / max | +12.394120 pp | +14.835491 pp | 466 | 630,496 |

| Mode / model / effort | Score-only control | Combined score | Change | Model gain above seed | In-loop cleanup gain | Final cleanup gain | Tool calls / coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| score_edges / gpt-6-astra / max | 88.384406% | 88.043179% | -0.341227 pp | +41.729589 pp | +0.000000 pp | +0.065451 pp | 0 / 0.0% |
| score_edges / gpt-6-astra / low | 78.130010% | 79.118309% | +0.988299 pp | +32.514349 pp | +0.000000 pp | +0.355821 pp | 0 / 0.0% |
| score_edges / gpt-6-luna / max | 65.135096% | 68.264239% | +3.129143 pp | +21.620306 pp | +0.000000 pp | +0.395794 pp | 0 / 0.0% |
| score_each / gpt-6-astra / max | 88.384406% | 86.977844% | -1.406562 pp | +39.891184 pp | +0.838521 pp | +0.000000 pp | 105 / 100.0% |
| score_each / gpt-6-astra / low | 78.130010% | 75.301134% | -2.828876 pp | +28.142282 pp | +0.886471 pp | +0.024241 pp | 39 / 90.5% |
| score_each / gpt-6-luna / max | 65.135096% | 61.320048% | -3.815048 pp | +13.508442 pp | +1.481799 pp | +0.081668 pp | 129 / 96.7% |

## Cost comparison

Estimates use public Standard API rates, short context per request and reported cache counters. They are API-equivalent estimates, not Codex invoices. Missing usage is unknown. Running cells are excluded until terminal usage is available. Reasoning is included in output; the $3 cap applies to every problem.

| Stage / model / effort | Priced problems | Mean USD | Maximum USD | Over $3 |
| --- | ---: | ---: | ---: | ---: |
| correctness / gpt-6-astra / low | 15/15 | 0.428894 | 0.856080 | 0 |
| correctness / gpt-6-luna / max | 15/15 | 0.020008 | 0.054749 | 0 |
| score / gpt-6-astra / max | 15/15 | 5.153749 | 8.690906 | 14 |
| score / gpt-6-astra / low | 15/15 | 1.241894 | 4.866198 | 2 |
| score / gpt-6-luna / max | 15/15 | 0.090313 | 0.251066 | 0 |
| score_edges / gpt-6-astra / max | 15/15 | 5.151091 | 7.935048 | 15 |
| score_edges / gpt-6-astra / low | 15/15 | 0.929707 | 2.156566 | 0 |
| score_edges / gpt-6-luna / max | 15/15 | 0.090727 | 0.244687 | 0 |
| score_each / gpt-6-astra / max | 15/15 | 7.431051 | 11.397110 | 15 |
| score_each / gpt-6-astra / low | 15/15 | 1.969864 | 4.037396 | 3 |
| score_each / gpt-6-luna / max | 15/15 | 0.124064 | 0.366331 | 0 |
| model_config / gpt-6.1-sol / max | 15/15 | 0.987643 | 1.672598 | 0 |
| model_config / gpt-6-astra / high | 15/15 | 1.926246 | 3.543124 | 3 |

In-loop cleanup is retired; stage 04 remains historical evidence. New model configurations use beginning/end cleanup. Refactoring is paused while selecting the model configuration.

Stages use independent generations and measured inference varies. These are not budget-matched comparisons.

The per-problem CSV separates the selected seed, model-generated gains, accepted in-loop cleanup gains and final cleanup. These increments describe the saved-best trajectory, not isolated causal effects. Further-search gain excludes final cleanup and merely checking the seed. Valid-proposal coverage measures unique changed valid proposals sent to the cleanup tool; it does not assume prompt compliance.

Across terminal cells there are 352 unique cleanup jobs and 40 reused calls. The comparison JSON sums optimizer counters once per shared job across all conditions; do not add per-cell job counts to estimate total work. Initial/final evaluator validation and the original saved D0 construction are outside those counters.

Completion-token counts use provider-reported usage, including reasoning, across completed CLI calls. Tool checks count agent requests, including duplicate code; trajectories mark duplicates. Cost estimation is documented in stage 05.

This is a snapshot. The per-stage README/report files refresh automatically while runs continue. Regenerate with `python src/summarize_agent_harness.py`, or add `--watch --suite models` to refresh until the model-configuration controller finishes.
