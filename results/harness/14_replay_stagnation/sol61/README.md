# Offline stopping-policy replay

Gate: **NO-GO** (no_eligible_threshold).

No new model or Lean calls. Scores are local raw accepted incumbents before cleanup. Spliced histories assume unchanged behavior under shifted restart prompts. Reinvestment and cost interpolation are model-based estimates.

Protocol thresholds: 12/15 on support; mean loss <=0.10 pp; freed time >=8 min/problem; estimated reinvestment >=2x lost gain; <=0.10 pp loss separately on stages 06 and 08; leave-one-out within one grid step.

| Cohort | Policy | Raw score | Loss pp | Freed min/problem | On support |
| --- | --- | ---: | ---: | ---: | ---: |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | identity | 89.357422 | 0.000000 | 0.000 | 15/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_3m | 73.124073 | 16.233349 | 40.137 | 0/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_4m | 81.073262 | 8.284160 | 24.761 | 4/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_5m | 85.195052 | 4.162370 | 19.900 | 5/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_6m | 88.495145 | 0.862277 | 16.501 | 7/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_8m | 88.911347 | 0.446075 | 8.579 | 9/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_10m | 89.172809 | 0.184613 | 5.928 | 11/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_12m | 89.357422 | 0.000000 | 0.000 | 15/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_15m | 89.357422 | 0.000000 | 0.000 | 15/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_20m | 89.357422 | 0.000000 | 0.000 | 15/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_3m_delta_0.25 | 72.727987 | 16.629435 | 43.929 | 0/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_4m_delta_0.25 | 80.420659 | 8.936763 | 34.014 | 0/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_5m_delta_0.25 | 84.736085 | 4.621337 | 28.652 | 0/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_6m_delta_0.25 | 88.209314 | 1.148108 | 23.440 | 3/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_8m_delta_0.25 | 88.565440 | 0.791982 | 17.992 | 5/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_10m_delta_0.25 | 88.655898 | 0.701524 | 14.726 | 6/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_12m_delta_0.25 | 88.711023 | 0.646399 | 12.101 | 7/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_15m_delta_0.25 | 88.980447 | 0.376975 | 7.227 | 10/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_20m_delta_0.25 | 89.287793 | 0.069629 | 1.475 | 14/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_3m_delta_0.5 | 72.599876 | 16.757546 | 45.466 | 0/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_4m_delta_0.5 | 80.149742 | 9.207680 | 37.121 | 0/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_5m_delta_0.5 | 84.373705 | 4.983717 | 33.174 | 0/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_6m_delta_0.5 | 88.076349 | 1.281073 | 26.281 | 2/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_8m_delta_0.5 | 88.247743 | 1.109679 | 21.562 | 4/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_10m_delta_0.5 | 88.361103 | 0.996319 | 18.230 | 4/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_12m_delta_0.5 | 88.600431 | 0.756991 | 15.451 | 5/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_15m_delta_0.5 | 88.923901 | 0.433521 | 8.658 | 9/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | stagnation_20m_delta_0.5 | 89.231247 | 0.126175 | 2.692 | 13/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | attempt_cap_1 | 86.992706 | 2.364716 | 35.142 | 15/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | attempt_cap_2 | 88.699412 | 0.658010 | 13.834 | 15/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | attempt_cap_3 | 89.321756 | 0.035666 | 3.566 | 15/15 |
| 10_budget_resets/sol61_max_3usd::gpt-6.1-sol/max (full_declared_cohort) | attempt_cap_4 | 89.357422 | 0.000000 | 0.675 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | identity | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_3m | 80.363891 | 6.549415 | 8.287 | 9/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_4m | 80.384282 | 6.529024 | 7.222 | 10/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_5m | 81.153314 | 5.759993 | 5.419 | 12/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_6m | 83.640667 | 3.272640 | 2.225 | 13/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_8m | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_10m | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_12m | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_15m | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_20m | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_3m_delta_0.25 | 80.220938 | 6.692369 | 10.152 | 6/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_4m_delta_0.25 | 80.295047 | 6.618260 | 9.110 | 7/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_5m_delta_0.25 | 81.108735 | 5.804572 | 6.982 | 9/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_6m_delta_0.25 | 83.600356 | 3.312951 | 3.637 | 10/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_8m_delta_0.25 | 86.712668 | 0.200638 | 1.638 | 11/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_10m_delta_0.25 | 86.895914 | 0.017393 | 0.495 | 14/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_12m_delta_0.25 | 86.904866 | 0.008440 | 0.179 | 14/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_15m_delta_0.25 | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_20m_delta_0.25 | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_3m_delta_0.5 | 79.684837 | 7.228470 | 12.210 | 4/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_4m_delta_0.5 | 79.691285 | 7.222021 | 11.591 | 4/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_5m_delta_0.5 | 80.626154 | 6.287153 | 9.411 | 6/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_6m_delta_0.5 | 83.147453 | 3.765853 | 5.826 | 7/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_8m_delta_0.5 | 86.701336 | 0.211971 | 2.562 | 11/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_10m_delta_0.5 | 86.868949 | 0.044357 | 1.144 | 12/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_12m_delta_0.5 | 86.882169 | 0.031137 | 0.798 | 12/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_15m_delta_0.5 | 86.913307 | 0.000000 | 0.175 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | stagnation_20m_delta_0.5 | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | attempt_cap_1 | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | attempt_cap_2 | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | attempt_cap_3 | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 08_tactic_profiles/sol61_max::gpt-6.1-sol/max (full_declared_cohort) | attempt_cap_4 | 86.913307 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | identity | 86.557428 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_3m | 74.604431 | 11.952997 | 11.466 | 4/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_4m | 77.574105 | 8.983323 | 8.674 | 7/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_5m | 80.735000 | 5.822428 | 3.530 | 12/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_6m | 80.735000 | 5.822428 | 3.275 | 12/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_8m | 86.557428 | 0.000000 | 0.050 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_10m | 86.557428 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_12m | 86.557428 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_15m | 86.557428 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_20m | 86.557428 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_3m_delta_0.25 | 74.550871 | 12.006556 | 12.122 | 3/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_4m_delta_0.25 | 77.254918 | 9.302510 | 10.029 | 4/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_5m_delta_0.25 | 80.111055 | 6.446372 | 6.768 | 6/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_6m_delta_0.25 | 80.631413 | 5.926015 | 4.984 | 8/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_8m_delta_0.25 | 86.557428 | 0.000000 | 0.579 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_10m_delta_0.25 | 86.557428 | 0.000000 | 0.253 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_12m_delta_0.25 | 86.557428 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_15m_delta_0.25 | 86.557428 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_20m_delta_0.25 | 86.557428 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_3m_delta_0.5 | 74.070952 | 12.486476 | 12.747 | 2/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_4m_delta_0.5 | 77.178435 | 9.378993 | 10.542 | 3/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_5m_delta_0.5 | 79.929342 | 6.628086 | 8.068 | 3/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_6m_delta_0.5 | 80.343435 | 6.213992 | 6.721 | 5/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_8m_delta_0.5 | 86.406869 | 0.150559 | 2.329 | 11/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_10m_delta_0.5 | 86.423837 | 0.133591 | 1.483 | 12/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_12m_delta_0.5 | 86.534512 | 0.022916 | 0.321 | 14/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_15m_delta_0.5 | 86.557428 | 0.000000 | 0.075 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | stagnation_20m_delta_0.5 | 86.557428 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | attempt_cap_1 | 86.557428 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | attempt_cap_2 | 86.557428 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | attempt_cap_3 | 86.557428 | 0.000000 | 0.000 | 15/15 |
| 06_refactor_regression::gpt-6.1-sol/max (full_declared_cohort) | attempt_cap_4 | 86.557428 | 0.000000 | 0.000 | 15/15 |

Exclusions: none.
