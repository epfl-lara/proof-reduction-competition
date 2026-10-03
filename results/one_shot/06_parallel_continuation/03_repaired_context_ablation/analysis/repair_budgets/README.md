# Recorded repair budgets

**incomplete**: 188/225 terminal trajectories available. Budgets 0/1/2/3 replay the same saved proposals and repair prefixes.

D0 averages **46.248122%** local combined score. Means remain blank for incomplete conditions.

| Model | Arm | Complete / expected | L at 0 | L at 1 | L at 2 | L at 3 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | plain | 15/15 | 46.248 | 46.248 | 46.248 | 46.248 |
| Qwen3.5-397B-A17B | plain | 8/15 | — | — | — | — |
| Qwen3.6-35B-A3B | plain | 15/15 | 46.248 | 46.248 | 46.396 | 46.396 |
| DeepSeek-V4.1-Flash | cards | 15/15 | 46.248 | 46.828 | 48.470 | 48.470 |
| Qwen3.5-397B-A17B | cards | 7/15 | — | — | — | — |
| Qwen3.6-35B-A3B | cards | 15/15 | 46.248 | 46.248 | 46.248 | 46.248 |
| DeepSeek-V4.1-Flash | goals | 15/15 | 46.854 | 47.267 | 47.267 | 47.267 |
| Qwen3.5-397B-A17B | goals | 8/15 | — | — | — | — |
| Qwen3.6-35B-A3B | goals | 15/15 | 46.248 | 46.348 | 46.348 | 46.348 |
| DeepSeek-V4.1-Flash | cards_goals | 15/15 | 46.248 | 46.434 | 46.434 | 46.434 |
| Qwen3.5-397B-A17B | cards_goals | 7/15 | — | — | — | — |
| Qwen3.6-35B-A3B | cards_goals | 15/15 | 46.248 | 46.248 | 46.248 | 46.248 |
| DeepSeek-V4.1-Flash | cards_goals_costs | 15/15 | 48.124 | 48.124 | 48.124 | 48.124 |
| Qwen3.5-397B-A17B | cards_goals_costs | 8/15 | — | — | — | — |
| Qwen3.6-35B-A3B | cards_goals_costs | 15/15 | 46.248 | 46.248 | 46.248 | 46.248 |

The following count sequences correspond to budgets **0 / 1 / 2 / 3**. They concern the same completed trajectories in each row; they are not independent samples.

| Model | Arm | All-version valid | Changed valid | Returned incumbent | Accepted improvement |
| --- | --- | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | plain | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Qwen3.5-397B-A17B | plain | 1 / 5 / 6 / 7 | 1 / 4 / 5 / 6 | 0 / 1 / 1 / 1 | 0 / 1 / 2 / 2 |
| Qwen3.6-35B-A3B | plain | 0 / 3 / 5 / 5 | 0 / 1 / 3 / 3 | 0 / 2 / 2 / 2 | 0 / 0 / 1 / 1 |
| DeepSeek-V4.1-Flash | cards | 1 / 3 / 4 / 4 | 1 / 2 / 3 / 3 | 0 / 1 / 1 / 1 | 0 / 1 / 2 / 2 |
| Qwen3.5-397B-A17B | cards | 0 / 5 / 5 / 6 | 0 / 3 / 3 / 4 | 0 / 2 / 2 / 2 | 0 / 1 / 1 / 2 |
| Qwen3.6-35B-A3B | cards | 0 / 5 / 6 / 6 | 0 / 1 / 1 / 1 | 0 / 4 / 5 / 5 | 0 / 0 / 0 / 0 |
| DeepSeek-V4.1-Flash | goals | 1 / 2 / 2 / 2 | 1 / 2 / 2 / 2 | 0 / 0 / 0 / 0 | 1 / 2 / 2 / 2 |
| Qwen3.5-397B-A17B | goals | 0 / 4 / 4 / 5 | 0 / 3 / 3 / 3 | 0 / 1 / 1 / 2 | 0 / 0 / 0 / 0 |
| Qwen3.6-35B-A3B | goals | 0 / 9 / 9 / 10 | 0 / 2 / 2 / 3 | 0 / 7 / 7 / 7 | 0 / 1 / 1 / 1 |
| DeepSeek-V4.1-Flash | cards_goals | 0 / 1 / 1 / 1 | 0 / 1 / 1 / 1 | 0 / 0 / 0 / 0 | 0 / 1 / 1 / 1 |
| Qwen3.5-397B-A17B | cards_goals | 0 / 5 / 5 / 5 | 0 / 4 / 4 / 4 | 0 / 1 / 1 / 1 | 0 / 1 / 1 / 1 |
| Qwen3.6-35B-A3B | cards_goals | 1 / 6 / 7 / 7 | 1 / 3 / 3 / 3 | 0 / 3 / 4 / 4 | 0 / 0 / 0 / 0 |
| DeepSeek-V4.1-Flash | cards_goals_costs | 1 / 3 / 3 / 4 | 1 / 2 / 2 / 2 | 0 / 1 / 1 / 2 | 1 / 1 / 1 / 1 |
| Qwen3.5-397B-A17B | cards_goals_costs | 1 / 3 / 5 / 5 | 1 / 2 / 3 / 3 | 0 / 1 / 2 / 2 | 1 / 1 / 1 / 1 |
| Qwen3.6-35B-A3B | cards_goals_costs | 0 / 5 / 6 / 6 | 0 / 4 / 5 / 5 | 0 / 1 / 1 / 1 | 0 / 0 / 0 / 0 |

These diagnostic totals sum physical request records represented once in this directory; they do not form a pooled proof score. Each budget is cumulative: do not add the four rows together. Only completed trajectories are included. Initial calls are separate and shared by every replay.

| Maximum repairs | Extra calls | Known prompt tokens | Known completion tokens | Usage missing | Empty length-truncated outputs |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 | 0 | 0 |
| 1 | 110 | 678,007 | 1,016,812 | 1 | 7 |
| 2 | 159 | 1,003,837 | 1,501,403 | 1 | 11 |
| 3 | 195 | 1,241,366 | 1,886,448 | 2 | 14 |

Full per-condition cumulative and marginal usage, selected-score gains, raw unknown outcomes, and provenance hashes are in [report.json](report.json). [per_problem.csv](per_problem.csv) contains the exact replayed prefixes; [conditions.csv](conditions.csv) contains budget-specific condition statistics.


- These are deterministic replays of saved prefixes, not newly sampled stochastic experiments at each budget.
- Only complete terminal trajectories enter any budget; a condition mean requires every declared proof. Pending trajectory prefixes are excluded even from budget zero.
- The first all-version-valid candidate stops repair even if it is inferior. Empty outputs and unavailable outcomes stop too; no later candidate is fabricated.
- Selection preserves the exact strict score > D0 + 0.05 threshold and otherwise retains D0. Unknown raw scores remain null; known invalid/failed outputs have zero raw score.
- Calls and known provider usage are cumulative additional repairs. Reasoning tokens are part of completion tokens; missing usage is counted rather than estimated.
- Each declared cell is counted once, including copied completed trajectories. Do not add original or pilot folders to continuation totals.
- Duration sums include overlapping service/admission waiting and are not model latency or counterfactual elapsed-time savings.
- Budget replays share the same sampled prefixes and have no significance claim. Their outcomes do not cover post-model deterministic cleanup.
- Run the independent saved-evidence audit before final interpretation; this report executes no model or Lean calls.
