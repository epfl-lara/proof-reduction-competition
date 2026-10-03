# Complete initial one-shot context experiment

All **225/225 cells** finished on 2026-10-03: three models × five context arms ×
the same fifteen warm-up declarations. Each cell received one optimization
request from the deterministic incumbent, with temperature 0.3, requested high
reasoning and a 32,768-token total output cap. There were no repairs or candidate
feedback in this stage. Three pilot cells were retained, and the main runner
scheduled the remaining 222. The [complete evidence audit](validation/evidence_audit.json)
passed for all 225 cells and confirmed that all **36 cached reference records
remained unchanged**. Reporting and auditing made no model calls or Lean checks.

The local deterministic baseline is **46.248122%** combined score: 12.187241%
length reduction, 26.557125% heartbeat reduction and 100% version compatibility.
These are local measurements against fixed references, not official grader
measurements. The selected score below retains that incumbent whenever the
candidate fails or does not improve its combined score by more than 0.05 points.
All six accepted candidates passed every required version; every selected
condition therefore retains 100% compatibility.

| Model | Context arm | Selected mean score % | Gain, percentage points | Raw outputs valid on all versions / 15 | Accepted improvements / 15 |
|---|---|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash | plain | 46.248122 | 0.000000 | 0 | 0 |
| DeepSeek-V4.1-Flash | cards | 46.248122 | 0.000000 | 1 | 0 |
| DeepSeek-V4.1-Flash | goals | 46.854456 | 0.606334 | 1 | 1 |
| DeepSeek-V4.1-Flash | cards_goals | 46.248122 | 0.000000 | 0 | 0 |
| DeepSeek-V4.1-Flash | cards_goals_costs | **48.124185** | **1.876063** | 1 | 1 |
| Qwen3.5-397B-A17B | plain | 46.248122 | 0.000000 | 1 | 0 |
| Qwen3.5-397B-A17B | cards | 46.346194 | 0.098072 | 1 | 1 |
| Qwen3.5-397B-A17B | goals | 46.259921 | 0.011799 | 3 | 1 |
| Qwen3.5-397B-A17B | cards_goals | 46.252442 | 0.004320 | 2 | 1 |
| Qwen3.5-397B-A17B | cards_goals_costs | **47.020639** | **0.772517** | 1 | 1 |
| Qwen3.6-35B-A3B | plain | 46.248122 | 0.000000 | 0 | 0 |
| Qwen3.6-35B-A3B | cards | 46.248122 | 0.000000 | 0 | 0 |
| Qwen3.6-35B-A3B | goals | 46.248122 | 0.000000 | 0 | 0 |
| Qwen3.6-35B-A3B | cards_goals | 46.248122 | 0.000000 | 1 | 0 |
| Qwen3.6-35B-A3B | cards_goals_costs | 46.248122 | 0.000000 | 0 | 0 |

The highest observed arm was `cards_goals_costs` for DeepSeek and Qwen397; all
Qwen35B arms tied the baseline. DeepSeek's leading arm gained 28.140949 points on
`Cslib.CCS.bisimilarity_congr_choice` alone, contributing 1.876063 points to its
fifteen-problem mean. Qwen397's leading arm gained 11.587753 points on
`Cslib.SKI.parallelReduction_diamond` alone. Thus these arm rankings depend on
one improved problem each. Qwen397's `goals` arm had the most valid outputs
(3/15), while its leading score arm had only 1/15. Validity and score rank differ.

Every table row is an independent complete condition. No best-of-arm or
best-of-model submission was constructed. Six accepted cells do not mean six
distinct improved declarations. This is one stochastic sample per cell on
fifteen warm-up problems, so the rankings are descriptive and do not establish
a general causal benefit from strategy cards, goals, or cost context.

| Model, 75 cells each | All-version-valid changed / unchanged | Accepted cells | Evaluator failed | Invalid output | Transport unavailable | Length-cap output empty / nonempty |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash | 3 / 0 | 2 | 9 | 63 | 0 | 60 / 3 |
| Qwen3.5-397B-A17B | 7 / 1 | 4 | 64 | 0 | 3 | 0 / 0 |
| Qwen3.6-35B-A3B | 1 / 0 | 0 | 64 | 10 | 0 | 10 / 0 |

Overall, 12/225 raw outputs passed every required version, including one exact
incumbent return; 11 were changed valid proofs. Of the remaining cells, 137
failed evaluation, 73 were invalid truncated outputs, and three had unavailable
transport results. Truncation is counted once in the outcome totals; the final
column describes those same truncated outputs. Qwen35B's failed evaluations
include three timed-out version checks. Qwen397's three transport failures
occurred in `goals` (two) and `cards_goals_costs` (one). Their raw scores and token
usage are unknown; they are not zero-score compiler failures. The selected
condition scores remain defined because they fall back to verified incumbents.

| Model | Usage coverage | Prompt tokens | Completion tokens | Provider-classified reasoning tokens | Derived other completion tokens |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4.1-Flash | 75/75 | 602,945 | 2,404,846 | 2,387,115 | 17,731 |
| Qwen3.5-397B-A17B | 72/75 | 569,334 | 244,048 | 140,516 | 103,532 |
| Qwen3.6-35B-A3B | 75/75 | 601,706 | 1,096,989 | 1,021,141 | 75,848 |
| Known total | 222/225 | 1,773,985 | 3,745,883 | 3,548,772 | 197,111 |

DeepSeek returned no final answer in 60/75 cells after hitting the output cap.
The saved artifacts contain token classifications and reasoning character
counts, not reasoning content. They cannot distinguish productive reasoning,
repetition, or model-serving/formatting issues. The next DeepSeek diagnostic
should preserve prompts and total cap while varying requested reasoning effort;
this experiment alone cannot assign the failures to the prompt. Wall-clock
request durations are not model-speed comparisons.

For the next harness step, correctness-only debugging can address explicit
compiler errors on nonempty candidates. Empty outputs require a separately
declared generation-policy experiment and are not silently regenerated. Keep
the current independent conditions and deterministic fallback when comparing
those later stages. Cost examples are measurements of specific original proof
sites; this experiment does not establish universal heartbeat costs for tactics.

Reproducible evidence: [full report](report.json), [condition summary and exports](README.md),
[failure analysis](FAILURE_ANALYSIS.md), [machine-readable failure analysis](failure_analysis.json),
and [complete audit](validation/evidence_audit.json). All reports use saved
requests, generations and evaluations without remeasuring references.
