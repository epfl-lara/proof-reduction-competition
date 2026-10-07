# Offline stopping-policy replay

Gate: **NOT_EVALUATED** (descriptive_only).

No new model or Lean calls. Scores are local raw accepted incumbents before cleanup. Spliced histories assume unchanged behavior under shifted restart prompts. Reinvestment and cost interpolation are model-based estimates.

Protocol thresholds: 12/15 on support; mean loss <=0.10 pp; freed time >=8 min/problem; estimated reinvestment >=2x lost gain; <=0.10 pp loss separately on stages 06 and 08; leave-one-out within one grid step.

| Cohort | Policy | Raw score | Loss pp | Freed min/problem | On support |
| --- | --- | ---: | ---: | ---: | ---: |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | identity | 72.830191 | 0.000000 | 0.001 | 15/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_3m | 49.362776 | 23.467415 | 36.176 | 4/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_4m | 54.050702 | 18.779489 | 34.712 | 4/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_5m | 54.050702 | 18.779489 | 33.815 | 4/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_6m | 55.782654 | 17.047537 | 31.128 | 4/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_8m | 60.534785 | 12.295406 | 26.539 | 5/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_10m | 61.139654 | 11.690538 | 21.005 | 8/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_12m | 61.362970 | 11.467222 | 16.282 | 9/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_15m | 61.362970 | 11.467222 | 15.828 | 9/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_20m | 67.555148 | 5.275043 | 7.439 | 12/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_3m_delta_0.25 | 49.362776 | 23.467415 | 36.176 | 4/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_4m_delta_0.25 | 54.050702 | 18.779489 | 34.712 | 4/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_5m_delta_0.25 | 54.050702 | 18.779489 | 33.815 | 4/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_6m_delta_0.25 | 55.782654 | 17.047537 | 31.128 | 4/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_8m_delta_0.25 | 60.534785 | 12.295406 | 26.539 | 5/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_10m_delta_0.25 | 61.139654 | 11.690538 | 21.005 | 8/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_12m_delta_0.25 | 61.152873 | 11.677318 | 17.542 | 8/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_15m_delta_0.25 | 61.152873 | 11.677318 | 17.089 | 8/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_20m_delta_0.25 | 67.555148 | 5.275043 | 7.439 | 12/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_3m_delta_0.5 | 49.362776 | 23.467415 | 36.176 | 4/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_4m_delta_0.5 | 54.050702 | 18.779489 | 34.712 | 4/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_5m_delta_0.5 | 54.050702 | 18.779489 | 33.815 | 4/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_6m_delta_0.5 | 55.639199 | 17.190992 | 32.075 | 4/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_8m_delta_0.5 | 60.226394 | 12.603798 | 29.213 | 5/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_10m_delta_0.5 | 60.848091 | 11.982100 | 23.863 | 7/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_12m_delta_0.5 | 60.869980 | 11.960211 | 20.368 | 7/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_15m_delta_0.5 | 61.004766 | 11.825426 | 18.589 | 7/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_20m_delta_0.5 | 67.429138 | 5.401053 | 8.506 | 11/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | attempt_cap_1 | 72.830191 | 0.000000 | 0.001 | 15/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | attempt_cap_2 | 72.830191 | 0.000000 | 0.001 | 15/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | attempt_cap_3 | 72.830191 | 0.000000 | 0.001 | 15/15 |
| 09_qwen_flash_next/qwen38_xhigh_57m::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | attempt_cap_4 | 72.830191 | 0.000000 | 0.001 | 15/15 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | identity | 90.066861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_3m | 76.946546 | 13.120315 | 35.990 | 1/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_4m | 76.946546 | 13.120315 | 35.778 | 1/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_5m | 77.005635 | 13.061225 | 32.129 | 1/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_6m | 77.005635 | 13.061225 | 32.035 | 1/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_8m | 82.603028 | 7.463833 | 18.535 | 2/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_10m | 82.614801 | 7.452060 | 16.170 | 3/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_12m | 89.698454 | 0.368407 | 7.340 | 4/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_15m | 90.066861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_20m | 90.066861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_3m_delta_0.25 | 76.372457 | 13.694404 | 46.559 | 0/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_4m_delta_0.25 | 76.394871 | 13.671990 | 46.320 | 0/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_5m_delta_0.25 | 76.394871 | 13.671990 | 46.170 | 0/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_6m_delta_0.25 | 76.394871 | 13.671990 | 45.686 | 0/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_8m_delta_0.25 | 82.543938 | 7.522922 | 22.396 | 2/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_10m_delta_0.25 | 82.580327 | 7.486534 | 21.833 | 2/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_12m_delta_0.25 | 89.663981 | 0.402880 | 13.023 | 3/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_15m_delta_0.25 | 89.689470 | 0.377391 | 11.838 | 3/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_20m_delta_0.25 | 89.701053 | 0.365808 | 8.102 | 3/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_3m_delta_0.5 | 76.372457 | 13.694404 | 46.559 | 0/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_4m_delta_0.5 | 76.394871 | 13.671990 | 46.320 | 0/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_5m_delta_0.5 | 76.394871 | 13.671990 | 46.170 | 0/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_6m_delta_0.5 | 76.394871 | 13.671990 | 45.686 | 0/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_8m_delta_0.5 | 82.543938 | 7.522922 | 22.396 | 2/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_10m_delta_0.5 | 82.580327 | 7.486534 | 21.833 | 2/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_12m_delta_0.5 | 89.663981 | 0.402880 | 13.023 | 3/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_15m_delta_0.5 | 89.689470 | 0.377391 | 11.838 | 3/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_20m_delta_0.5 | 89.701053 | 0.365808 | 8.102 | 3/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | attempt_cap_1 | 90.066861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | attempt_cap_2 | 90.066861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | attempt_cap_3 | 90.066861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_recovery::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | attempt_cap_4 | 90.066861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | identity | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_3m | 59.676555 | 6.319306 | 1.801 | 4/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_4m | 59.676555 | 6.319306 | 0.834 | 4/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_5m | 65.995861 | 0.000000 | 0.025 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_6m | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_8m | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_10m | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_12m | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_15m | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_20m | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_3m_delta_0.25 | 59.676555 | 6.319306 | 1.801 | 4/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_4m_delta_0.25 | 59.676555 | 6.319306 | 0.834 | 4/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_5m_delta_0.25 | 65.995861 | 0.000000 | 0.025 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_6m_delta_0.25 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_8m_delta_0.25 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_10m_delta_0.25 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_12m_delta_0.25 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_15m_delta_0.25 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_20m_delta_0.25 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_3m_delta_0.5 | 59.676555 | 6.319306 | 1.801 | 4/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_4m_delta_0.5 | 59.676555 | 6.319306 | 0.834 | 4/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_5m_delta_0.5 | 65.995861 | 0.000000 | 0.025 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_6m_delta_0.5 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_8m_delta_0.5 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_10m_delta_0.5 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_12m_delta_0.5 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_15m_delta_0.5 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | stagnation_20m_delta_0.5 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | attempt_cap_1 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | attempt_cap_2 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | attempt_cap_3 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 09_qwen_flash_next/qwen38_xhigh_57m_retry01::Qwen/Qwen3.8-Flash-Next/xhigh (loaded_subset_only) | attempt_cap_4 | 65.995861 | 0.000000 | 0.000 | 5/5 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | identity | 61.177126 | 0.000000 | 0.000 | 15/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_3m | 48.605318 | 12.571808 | 12.202 | 8/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_4m | 51.367441 | 9.809685 | 10.888 | 8/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_5m | 53.869777 | 7.307349 | 9.106 | 9/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_6m | 58.868226 | 2.308900 | 4.248 | 11/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_8m | 60.615998 | 0.561128 | 2.450 | 12/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_10m | 60.668967 | 0.508159 | 1.495 | 14/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_12m | 61.177126 | 0.000000 | 0.000 | 15/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_15m | 61.177126 | 0.000000 | 0.000 | 15/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_20m | 61.177126 | 0.000000 | 0.000 | 15/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_3m_delta_0.25 | 48.605318 | 12.571808 | 12.202 | 8/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_4m_delta_0.25 | 51.350728 | 9.826398 | 11.259 | 8/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_5m_delta_0.25 | 53.869777 | 7.307349 | 9.106 | 9/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_6m_delta_0.25 | 58.868226 | 2.308900 | 4.248 | 11/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_8m_delta_0.25 | 59.722121 | 1.455005 | 2.834 | 11/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_10m_delta_0.25 | 59.775091 | 1.402035 | 1.751 | 13/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_12m_delta_0.25 | 61.170955 | 0.006171 | 0.111 | 14/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_15m_delta_0.25 | 61.177126 | 0.000000 | 0.000 | 15/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_20m_delta_0.25 | 61.177126 | 0.000000 | 0.000 | 15/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_3m_delta_0.5 | 48.605318 | 12.571808 | 12.202 | 8/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_4m_delta_0.5 | 51.350728 | 9.826398 | 11.259 | 8/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_5m_delta_0.5 | 53.869777 | 7.307349 | 9.106 | 9/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_6m_delta_0.5 | 58.799919 | 2.377207 | 4.535 | 9/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_8m_delta_0.5 | 59.716844 | 1.460282 | 3.401 | 11/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_10m_delta_0.5 | 59.759620 | 1.417506 | 2.868 | 12/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_12m_delta_0.5 | 60.261608 | 0.915518 | 1.168 | 12/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_15m_delta_0.5 | 60.277972 | 0.899154 | 0.714 | 14/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | stagnation_20m_delta_0.5 | 61.177126 | 0.000000 | 0.000 | 15/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | attempt_cap_1 | 60.201493 | 0.975633 | 5.528 | 15/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | attempt_cap_2 | 61.039009 | 0.138117 | 0.989 | 15/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | attempt_cap_3 | 61.177126 | 0.000000 | 0.000 | 15/15 |
| 11_antigravity/gemini38_flash_high_3usd_full::gemini-3.8-flash/high (loaded_subset_only) | attempt_cap_4 | 61.177126 | 0.000000 | 0.000 | 15/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | identity | 78.785519 | 0.000000 | 0.000 | 15/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_3m | 61.000705 | 17.784814 | 32.709 | 1/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_4m | 61.525021 | 17.260498 | 31.192 | 1/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_5m | 61.794767 | 16.990751 | 28.473 | 1/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_6m | 63.997500 | 14.788018 | 26.928 | 1/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_8m | 71.974582 | 6.810936 | 19.800 | 5/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_10m | 75.522666 | 3.262853 | 15.048 | 8/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_12m | 76.117232 | 2.668287 | 9.351 | 10/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_15m | 76.200493 | 2.585025 | 5.301 | 13/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_20m | 78.785519 | 0.000000 | 0.810 | 15/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_3m_delta_0.25 | 60.853426 | 17.932092 | 33.517 | 1/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_4m_delta_0.25 | 61.377743 | 17.407776 | 32.000 | 1/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_5m_delta_0.25 | 61.794767 | 16.990751 | 28.593 | 1/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_6m_delta_0.25 | 63.997500 | 14.788018 | 27.048 | 1/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_8m_delta_0.25 | 71.956939 | 6.828579 | 20.181 | 4/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_10m_delta_0.25 | 75.522666 | 3.262853 | 15.376 | 8/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_12m_delta_0.25 | 75.755521 | 3.029998 | 11.730 | 9/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_15m_delta_0.25 | 75.795875 | 2.989644 | 9.558 | 10/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_20m_delta_0.25 | 78.780482 | 0.005036 | 2.326 | 14/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_3m_delta_0.5 | 60.853426 | 17.932092 | 33.517 | 1/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_4m_delta_0.5 | 61.377743 | 17.407776 | 32.000 | 1/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_5m_delta_0.5 | 61.525021 | 17.260498 | 30.771 | 1/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_6m_delta_0.5 | 63.727754 | 15.057765 | 29.226 | 1/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_8m_delta_0.5 | 71.944689 | 6.840829 | 20.557 | 4/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_10m_delta_0.5 | 75.522666 | 3.262853 | 15.721 | 8/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_12m_delta_0.5 | 75.743526 | 3.041993 | 12.720 | 8/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_15m_delta_0.5 | 75.783008 | 3.002510 | 10.802 | 9/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | stagnation_20m_delta_0.5 | 78.763794 | 0.021725 | 3.231 | 13/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | attempt_cap_1 | 78.785519 | 0.000000 | 0.000 | 15/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | attempt_cap_2 | 78.785519 | 0.000000 | 0.000 | 15/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | attempt_cap_3 | 78.785519 | 0.000000 | 0.000 | 15/15 |
| 12_source_discovery/qwen38_xhigh_local_57m::Qwen/Qwen3.8-Flash-Next/xhigh (full_declared_cohort) | attempt_cap_4 | 78.785519 | 0.000000 | 0.000 | 15/15 |

## Exclusions

{"name": "CallElimCorrect.substOldPostSubset", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "CallElimCorrect.extractedOldExprInVars", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "Core.InitsUpdatesComm", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "fundamental_theorem_of_variational_calculus'", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "FieldSpecification.WickAlgebra.\u03b9_timeOrderF_superCommuteF_eq_time", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "Cslib.SKI.parallelReduction_diamond", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "Cslib.CCS.bisimilarity_congr_choice", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "CallElimCorrect.substOldPostSubset", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "CallElimCorrect.extractedOldExprInVars", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "Core.InitsUpdatesComm", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "fundamental_theorem_of_variational_calculus'", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "FieldSpecification.WickAlgebra.\u03b9_timeOrderF_superCommuteF_eq_time", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "Cslib.SKI.parallelReduction_diamond", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "Cslib.CCS.bisimilarity_congr_choice", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
{"name": "Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius", "condition": ["Qwen/Qwen3.8-Flash-Next", "xhigh"], "reason": "declared_cell_not_loaded"}
