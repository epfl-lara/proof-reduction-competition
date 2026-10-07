# Offline stopping-policy replay

Gate: **NOT_EVALUATED** (one_problem_pilot).

No new model or Lean calls. Scores are local raw accepted incumbents before cleanup. Spliced histories assume unchanged behavior under shifted restart prompts. Reinvestment and cost interpolation are model-based estimates.

Protocol thresholds: 12/15 on support; mean loss <=0.10 pp; freed time >=8 min/problem; estimated reinvestment >=2x lost gain; <=0.10 pp loss separately on stages 06 and 08; leave-one-out within one grid step.

| Cohort | Policy | Raw score | Loss pp | Freed min/problem | On support |
| --- | --- | ---: | ---: | ---: | ---: |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | identity | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_3m | 76.924769 | 13.700454 | 50.884 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_4m | 76.924769 | 13.700454 | 50.188 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_5m | 86.681265 | 3.943959 | 34.073 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_6m | 86.681265 | 3.943959 | 32.532 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_8m | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_10m | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_12m | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_15m | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_20m | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_3m_delta_0.25 | 76.924769 | 13.700454 | 50.884 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_4m_delta_0.25 | 76.924769 | 13.700454 | 50.188 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_5m_delta_0.25 | 86.681265 | 3.943959 | 34.073 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_6m_delta_0.25 | 86.681265 | 3.943959 | 32.532 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_8m_delta_0.25 | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_10m_delta_0.25 | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_12m_delta_0.25 | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_15m_delta_0.25 | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_20m_delta_0.25 | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_3m_delta_0.5 | 76.924769 | 13.700454 | 50.884 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_4m_delta_0.5 | 76.924769 | 13.700454 | 50.188 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_5m_delta_0.5 | 86.681265 | 3.943959 | 34.073 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_6m_delta_0.5 | 86.681265 | 3.943959 | 32.532 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_8m_delta_0.5 | 87.507075 | 3.118149 | 22.604 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_10m_delta_0.5 | 87.507075 | 3.118149 | 20.347 | 0/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_12m_delta_0.5 | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_15m_delta_0.5 | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | stagnation_20m_delta_0.5 | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | attempt_cap_1 | 87.079055 | 3.546169 | 30.654 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | attempt_cap_2 | 90.625224 | 0.000000 | 7.323 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | attempt_cap_3 | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (loaded_subset_only) | attempt_cap_4 | 90.625224 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | identity | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_3m | 83.492699 | 2.651798 | 12.754 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_4m | 83.492699 | 2.651798 | 10.816 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_5m | 83.492699 | 2.651798 | 10.816 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_6m | 83.492699 | 2.651798 | 9.463 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_8m | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_10m | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_12m | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_15m | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_20m | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_3m_delta_0.25 | 83.492699 | 2.651798 | 14.230 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_4m_delta_0.25 | 83.492699 | 2.651798 | 13.192 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_5m_delta_0.25 | 83.492699 | 2.651798 | 10.816 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_6m_delta_0.25 | 83.492699 | 2.651798 | 10.816 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_8m_delta_0.25 | 83.630291 | 2.514206 | 9.237 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_10m_delta_0.25 | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_12m_delta_0.25 | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_15m_delta_0.25 | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_20m_delta_0.25 | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_3m_delta_0.5 | 83.492699 | 2.651798 | 14.230 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_4m_delta_0.5 | 83.492699 | 2.651798 | 13.192 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_5m_delta_0.5 | 83.492699 | 2.651798 | 10.816 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_6m_delta_0.5 | 83.492699 | 2.651798 | 10.816 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_8m_delta_0.5 | 83.630291 | 2.514206 | 9.237 | 0/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_10m_delta_0.5 | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_12m_delta_0.5 | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_15m_delta_0.5 | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | stagnation_20m_delta_0.5 | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | attempt_cap_1 | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | attempt_cap_2 | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | attempt_cap_3 | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (loaded_subset_only) | attempt_cap_4 | 86.144497 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | identity | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_3m | 78.562620 | 4.103142 | 6.312 | 0/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_4m | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_5m | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_6m | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_8m | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_10m | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_12m | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_15m | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_20m | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_3m_delta_0.25 | 78.562620 | 4.103142 | 8.702 | 0/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_4m_delta_0.25 | 78.562620 | 4.103142 | 8.203 | 0/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_5m_delta_0.25 | 78.562620 | 4.103142 | 6.605 | 0/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_6m_delta_0.25 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_8m_delta_0.25 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_10m_delta_0.25 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_12m_delta_0.25 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_15m_delta_0.25 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_20m_delta_0.25 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_3m_delta_0.5 | 78.562620 | 4.103142 | 8.702 | 0/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_4m_delta_0.5 | 78.562620 | 4.103142 | 8.203 | 0/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_5m_delta_0.5 | 78.562620 | 4.103142 | 6.605 | 0/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_6m_delta_0.5 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_8m_delta_0.5 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_10m_delta_0.5 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_12m_delta_0.5 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_15m_delta_0.5 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | stagnation_20m_delta_0.5 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | attempt_cap_1 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | attempt_cap_2 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | attempt_cap_3 | 82.665762 | 0.000000 | 0.000 | 1/1 |
| 06_refactor_regression::gpt-6.1-sol/max (loaded_subset_only) | attempt_cap_4 | 82.665762 | 0.000000 | 0.000 | 1/1 |

Exclusions: none.
