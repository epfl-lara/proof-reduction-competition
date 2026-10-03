# Codex agent baseline results

**partial**: 17/120 cells at 2026-10-03T10:48:52.523796+00:00.

Tools are enabled. One optimization proposal, correctness-only debugging, and paired original/deterministic seeds. See [protocol](PROTOCOL.md).

All scores use fixed local original references. Original identity: 33.333333%; deterministic D0: 46.248122%. Partial conditions have no full-benchmark mean.

| Model | Effort | Seed | Finished | Initial valid | Final valid | Selected mean | Gain over D0 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| gpt-6-astra | max | deterministic | 9/15 | 9 | 9 | pending | pending |
| gpt-6-astra | max | original | 8/15 | 8 | 8 | pending | pending |
| gpt-6-luna | max | deterministic | 0/15 | 0 | 0 | pending | pending |
| gpt-6-luna | max | original | 0/15 | 0 | 0 | pending | pending |
| gpt-6-luna | high | deterministic | 0/15 | 0 | 0 | pending | pending |
| gpt-6-luna | high | original | 0/15 | 0 | 0 | pending | pending |
| gpt-6-luna | medium | deterministic | 0/15 | 0 | 0 | pending | pending |
| gpt-6-luna | medium | original | 0/15 | 0 | 0 | pending | pending |

| Problem | Model / effort | Seed | Selected score | Gain over D0 | Tool checks |
| --- | --- | --- | ---: | ---: | ---: |
| `CallElimCorrect.substOldPostSubset` | gpt-6-astra / max | deterministic | 74.4879% | +37.0809 pp | 2 |
| `CallElimCorrect.substOldPostSubset` | gpt-6-astra / max | original | 64.7447% | +27.3377 pp | 2 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-astra / max | deterministic | 62.0023% | +24.6067 pp | 2 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-astra / max | original | 73.2246% | +35.8290 pp | 2 |
| `Core.InitsUpdatesComm` | gpt-6-astra / max | deterministic | 84.3934% | +33.9500 pp | 1 |
| `Core.InitsUpdatesComm` | gpt-6-astra / max | original | 84.0575% | +33.6141 pp | 1 |
| `fundamental_theorem_of_variational_calculus'` | gpt-6-astra / max | deterministic | 85.2217% | +41.7597 pp | 1 |
| `fundamental_theorem_of_variational_calculus'` | gpt-6-astra / max | original | 85.3108% | +41.8489 pp | 1 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | gpt-6-astra / max | deterministic | 72.8283% | +25.6856 pp | 5 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | gpt-6-astra / max | original | 73.5515% | +26.4088 pp | 3 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | gpt-6-astra / max | deterministic | 73.2223% | +32.6598 pp | 3 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | gpt-6-astra / max | original | 67.2208% | +26.6583 pp | 4 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | gpt-6-astra / max | deterministic | 68.8351% | +34.7998 pp | 1 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | gpt-6-astra / max | original | 63.4856% | +29.4502 pp | 1 |
| `Cslib.SKI.parallelReduction_diamond` | gpt-6-astra / max | deterministic | 59.8517% | +26.3379 pp | 1 |
| `Cslib.SKI.parallelReduction_diamond` | gpt-6-astra / max | original | 60.4531% | +26.9394 pp | 1 |
| `Cslib.CCS.bisimilarity_congr_choice` | gpt-6-astra / max | deterministic | 72.7765% | +39.4435 pp | 1 |

Usage and tool counts in [per_problem.csv](per_problem.csv) cover terminal cells only. Pending work and excluded pilot usage are additional; unknown usage is never zero. The full report is [report.json](report.json).
