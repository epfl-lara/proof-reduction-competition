# Recorded repair budgets

**complete**: 225/225 terminal trajectories available. Budgets 0/1/2/3 replay the same saved proposals and repair prefixes.

D0 averages **46.248122%** local combined score. Means remain blank for incomplete conditions.

| Model | Arm | Complete / expected | L at 0 | L at 1 | L at 2 | L at 3 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | plain | 15/15 | 46.248 | 46.248 | 46.248 | 46.248 |
| Qwen3.5-397B-A17B | plain | 15/15 | 46.248 | 46.308 | 46.363 | 46.363 |
| Qwen3.6-35B-A3B | plain | 15/15 | 46.248 | 46.248 | 46.396 | 46.396 |
| DeepSeek-V4.1-Flash | cards | 15/15 | 46.248 | 46.828 | 48.470 | 48.470 |
| Qwen3.5-397B-A17B | cards | 15/15 | 46.346 | 46.464 | 46.464 | 46.482 |
| Qwen3.6-35B-A3B | cards | 15/15 | 46.248 | 46.248 | 46.248 | 46.248 |
| DeepSeek-V4.1-Flash | goals | 15/15 | 46.854 | 47.267 | 47.267 | 47.267 |
| Qwen3.5-397B-A17B | goals | 15/15 | 46.260 | 46.260 | 46.260 | 46.260 |
| Qwen3.6-35B-A3B | goals | 15/15 | 46.248 | 46.348 | 46.348 | 46.348 |
| DeepSeek-V4.1-Flash | cards_goals | 15/15 | 46.248 | 46.434 | 46.434 | 46.434 |
| Qwen3.5-397B-A17B | cards_goals | 15/15 | 46.252 | 46.627 | 46.627 | 46.627 |
| Qwen3.6-35B-A3B | cards_goals | 15/15 | 46.248 | 46.248 | 46.248 | 46.248 |
| DeepSeek-V4.1-Flash | cards_goals_costs | 15/15 | 48.124 | 48.124 | 48.124 | 48.124 |
| Qwen3.5-397B-A17B | cards_goals_costs | 15/15 | 47.021 | 47.021 | 47.380 | 47.380 |
| Qwen3.6-35B-A3B | cards_goals_costs | 15/15 | 46.248 | 46.248 | 46.248 | 46.248 |

The following count sequences correspond to budgets **0 / 1 / 2 / 3**. They concern the same completed trajectories in each row; they are not independent samples.

| Model | Arm | All-version valid | Changed valid | Returned incumbent | Accepted improvement |
| --- | --- | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | plain | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Qwen3.5-397B-A17B | plain | 1 / 5 / 6 / 7 | 1 / 4 / 5 / 6 | 0 / 1 / 1 / 1 | 0 / 1 / 2 / 2 |
| Qwen3.6-35B-A3B | plain | 0 / 3 / 5 / 5 | 0 / 1 / 3 / 3 | 0 / 2 / 2 / 2 | 0 / 0 / 1 / 1 |
| DeepSeek-V4.1-Flash | cards | 1 / 3 / 4 / 4 | 1 / 2 / 3 / 3 | 0 / 1 / 1 / 1 | 0 / 1 / 2 / 2 |
| Qwen3.5-397B-A17B | cards | 1 / 6 / 8 / 9 | 1 / 4 / 6 / 7 | 0 / 2 / 2 / 2 | 1 / 2 / 2 / 3 |
| Qwen3.6-35B-A3B | cards | 0 / 5 / 6 / 6 | 0 / 1 / 1 / 1 | 0 / 4 / 5 / 5 | 0 / 0 / 0 / 0 |
| DeepSeek-V4.1-Flash | goals | 1 / 2 / 2 / 2 | 1 / 2 / 2 / 2 | 0 / 0 / 0 / 0 | 1 / 2 / 2 / 2 |
| Qwen3.5-397B-A17B | goals | 3 / 8 / 8 / 9 | 2 / 6 / 6 / 6 | 1 / 2 / 2 / 3 | 1 / 1 / 1 / 1 |
| Qwen3.6-35B-A3B | goals | 0 / 9 / 9 / 10 | 0 / 2 / 2 / 3 | 0 / 7 / 7 / 7 | 0 / 1 / 1 / 1 |
| DeepSeek-V4.1-Flash | cards_goals | 0 / 1 / 1 / 1 | 0 / 1 / 1 / 1 | 0 / 0 / 0 / 0 | 0 / 1 / 1 / 1 |
| Qwen3.5-397B-A17B | cards_goals | 2 / 9 / 9 / 9 | 2 / 8 / 8 / 8 | 0 / 1 / 1 / 1 | 1 / 3 / 3 / 3 |
| Qwen3.6-35B-A3B | cards_goals | 1 / 6 / 7 / 7 | 1 / 3 / 3 / 3 | 0 / 3 / 4 / 4 | 0 / 0 / 0 / 0 |
| DeepSeek-V4.1-Flash | cards_goals_costs | 1 / 3 / 3 / 4 | 1 / 2 / 2 / 2 | 0 / 1 / 1 / 2 | 1 / 1 / 1 / 1 |
| Qwen3.5-397B-A17B | cards_goals_costs | 1 / 3 / 7 / 7 | 1 / 2 / 5 / 5 | 0 / 1 / 2 / 2 | 1 / 1 / 2 / 2 |
| Qwen3.6-35B-A3B | cards_goals_costs | 0 / 5 / 6 / 6 | 0 / 4 / 5 / 5 | 0 / 1 / 1 / 1 | 0 / 0 / 0 / 0 |

These diagnostic totals sum physical request records represented once in this directory; they do not form a pooled proof score. Each budget is cumulative: do not add the four rows together. Only completed trajectories are included. Initial calls are separate and shared by every replay.

| Maximum repairs | Extra calls | Known prompt tokens | Known completion tokens | Usage missing | Empty length-truncated outputs |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 | 0 | 0 |
| 1 | 140 | 876,915 | 1,103,350 | 7 | 7 |
| 2 | 210 | 1,371,169 | 1,651,782 | 9 | 11 |
| 3 | 261 | 1,700,650 | 2,088,070 | 13 | 14 |

Full per-condition cumulative and marginal usage, selected-score gains, raw unknown outcomes, and provenance hashes are in [report.json](report.json). [per_problem.csv](per_problem.csv) contains the exact replayed prefixes; [conditions.csv](conditions.csv) contains budget-specific condition statistics.

The largest observed individual marginal gains are listed below. This is a post hoc description of saved outcomes, not a proof portfolio or evidence that a later round will help a new request.

| Model | Arm | Proof | Additional round | Selected gain pp |
| --- | --- | --- | ---: | ---: |
| DeepSeek-V4.1-Flash | cards | `putnam_1995_a3` | 2 | +24.638213 |
| DeepSeek-V4.1-Flash | cards | `putnam_1964_a4` | 1 | +8.691461 |
| DeepSeek-V4.1-Flash | goals | `Binius.BinaryBasefold.fold_advances_evaluation_poly` | 1 | +6.182071 |
| Qwen3.5-397B-A17B | cards_goals_costs | `Binius.BinaryBasefold.fold_advances_evaluation_poly` | 2 | +5.396480 |
| Qwen3.5-397B-A17B | cards_goals | `CallElimCorrect.substOldPostSubset` | 1 | +4.368674 |
| DeepSeek-V4.1-Flash | cards_goals | `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | 1 | +2.787744 |
| Qwen3.6-35B-A3B | plain | `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | 2 | +2.219686 |
| Qwen3.5-397B-A17B | cards | `CallElimCorrect.extractedOldExprInVars` | 1 | +1.769920 |

- These are deterministic replays of saved prefixes, not newly sampled stochastic experiments at each budget.
- Only complete terminal trajectories enter any budget; a condition mean requires every declared proof. Pending trajectory prefixes are excluded even from budget zero.
- The first all-version-valid candidate stops repair even if it is inferior. Empty outputs and unavailable outcomes stop too; no later candidate is fabricated.
- Selection preserves the exact strict score > D0 + 0.05 threshold and otherwise retains D0. Unknown raw scores remain null; known invalid/failed outputs have zero raw score.
- Calls and known provider usage are cumulative additional repairs. Reasoning tokens are part of completion tokens; missing usage is counted rather than estimated.
- Each declared cell is counted once, including copied completed trajectories. Do not add original or pilot folders to continuation totals.
- Duration sums include overlapping service/admission waiting and are not model latency or counterfactual elapsed-time savings.
- Budget replays share the same sampled prefixes and have no significance claim. Their outcomes do not cover post-model deterministic cleanup.
- Run the independent saved-evidence audit before final interpretation; this report executes no model or Lean calls.
