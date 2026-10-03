# Astra low-reasoning baseline

**complete**: 30/30 cells at 2026-10-03T18:19:50.844233+00:00.

Tools are enabled. One optimization proposal, correctness-only debugging, and paired original/deterministic seeds. See [protocol](PROTOCOL.md).

All scores use fixed local original references. Original identity: 33.333333%; deterministic D0: 46.248122%. Partial conditions have no full-benchmark mean.

| Model | Effort | Seed | Finished | Initial valid | Final valid | Selected mean | Gain over D0 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| gpt-6-astra | low | deterministic | 15/15 | 13 | 15 | 60.719659% | +14.471537 pp |
| gpt-6-astra | low | original | 15/15 | 14 | 15 | 57.222638% | +10.974516 pp |

| Problem | Model / effort | Seed | Selected score | Gain over D0 | Tool checks |
| --- | --- | --- | ---: | ---: | ---: |
| `CallElimCorrect.substOldPostSubset` | gpt-6-astra / low | deterministic | 61.0877% | +23.6807 pp | 5 |
| `CallElimCorrect.substOldPostSubset` | gpt-6-astra / low | original | 40.0862% | +2.6792 pp | 3 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-astra / low | deterministic | 38.7148% | +1.3192 pp | 1 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-astra / low | original | 34.5070% | -2.8886 pp | 1 |
| `Core.InitsUpdatesComm` | gpt-6-astra / low | deterministic | 55.7198% | +5.2764 pp | 1 |
| `Core.InitsUpdatesComm` | gpt-6-astra / low | original | 84.1413% | +33.6979 pp | 1 |
| `fundamental_theorem_of_variational_calculus'` | gpt-6-astra / low | deterministic | 82.6033% | +39.1413 pp | 2 |
| `fundamental_theorem_of_variational_calculus'` | gpt-6-astra / low | original | 80.1232% | +36.6612 pp | 1 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | gpt-6-astra / low | deterministic | 47.1427% | +0.0000 pp | 0 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | gpt-6-astra / low | original | 33.3333% | -13.8094 pp | 1 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | gpt-6-astra / low | deterministic | 40.6225% | +0.0599 pp | 1 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | gpt-6-astra / low | original | 33.7717% | -6.7909 pp | 2 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | gpt-6-astra / low | deterministic | 37.4341% | +3.3988 pp | 1 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | gpt-6-astra / low | original | 37.6535% | +3.6182 pp | 2 |
| `Cslib.SKI.parallelReduction_diamond` | gpt-6-astra / low | deterministic | 45.4573% | +11.9436 pp | 0 |
| `Cslib.SKI.parallelReduction_diamond` | gpt-6-astra / low | original | 45.4561% | +11.9424 pp | 0 |
| `Cslib.CCS.bisimilarity_congr_choice` | gpt-6-astra / low | deterministic | 72.7789% | +39.4458 pp | 1 |
| `Cslib.CCS.bisimilarity_congr_choice` | gpt-6-astra / low | original | 72.7787% | +39.4456 pp | 1 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | gpt-6-astra / low | deterministic | 43.8897% | +5.8461 pp | 1 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | gpt-6-astra / low | original | 35.4038% | -2.6398 pp | 1 |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | gpt-6-astra / low | deterministic | 51.3543% | +11.4552 pp | 1 |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | gpt-6-astra / low | original | 48.0067% | +8.1075 pp | 1 |
| `interleaved_affine_gaps_imply_tensor_gaps` | gpt-6-astra / low | deterministic | 67.9350% | +24.9858 pp | 2 |
| `interleaved_affine_gaps_imply_tensor_gaps` | gpt-6-astra / low | original | 45.4509% | +2.5017 pp | 2 |
| `putnam_1964_a4` | gpt-6-astra / low | deterministic | 86.5513% | +13.2318 pp | 1 |
| `putnam_1964_a4` | gpt-6-astra / low | original | 87.2077% | +13.8882 pp | 1 |
| `putnam_1964_b2` | gpt-6-astra / low | deterministic | 90.0318% | +2.9775 pp | 1 |
| `putnam_1964_b2` | gpt-6-astra / low | original | 92.2439% | +5.1896 pp | 2 |
| `putnam_1995_a3` | gpt-6-astra / low | deterministic | 89.4716% | +34.3110 pp | 1 |
| `putnam_1995_a3` | gpt-6-astra / low | original | 88.1756% | +33.0150 pp | 2 |

New calls after the [Luna recovery](../09_codex_tools_baselines/recovery/README.md) keep source projects read-only and route validity checks through the host. Prompts and scoring stay fixed; `isolated_calls` records the execution-policy change.

Usage and tool counts in [per_problem.csv](per_problem.csv) cover terminal cells only. Pending work and excluded pilot usage are additional; unknown usage is never zero. The full report is [report.json](report.json).

[Paired low/max differences](comparison.json) are reported per case. Full-benchmark differences remain null until all 15 cases in an arm finish. Initial requests match Astra/max exactly except reasoning effort. Low calls use source-write isolation; historical max calls preceded that fix.
