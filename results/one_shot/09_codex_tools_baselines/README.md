# Codex agent baseline results

**complete**: 120/120 cells at 2026-10-03T19:36:10.815869+00:00.

Tools are enabled. One optimization proposal, correctness-only debugging, and paired original/deterministic seeds. See [protocol](PROTOCOL.md).

All scores use fixed local original references. Original identity: 33.333333%; deterministic D0: 46.248122%. Partial conditions have no full-benchmark mean.

| Model | Effort | Seed | Finished | Initial valid | Final valid | Selected mean | Gain over D0 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| gpt-6-astra | max | deterministic | 15/15 | 15 | 15 | 78.970302% | +32.722180 pp |
| gpt-6-astra | max | original | 15/15 | 15 | 15 | 78.093430% | +31.845308 pp |
| gpt-6-luna | max | deterministic | 15/15 | 15 | 15 | 59.744910% | +13.496788 pp |
| gpt-6-luna | max | original | 15/15 | 12 | 15 | 53.045428% | +6.797306 pp |
| gpt-6-luna | high | deterministic | 15/15 | 14 | 15 | 50.579408% | +4.331285 pp |
| gpt-6-luna | high | original | 15/15 | 13 | 15 | 39.260352% | -6.987770 pp |
| gpt-6-luna | medium | deterministic | 15/15 | 12 | 15 | 46.506915% | +0.258793 pp |
| gpt-6-luna | medium | original | 15/15 | 13 | 15 | 33.523390% | -12.724732 pp |

| Problem | Model / effort | Seed | Selected score | Gain over D0 | Tool checks |
| --- | --- | --- | ---: | ---: | ---: |
| `CallElimCorrect.substOldPostSubset` | gpt-6-astra / max | deterministic | 74.4879% | +37.0809 pp | 2 |
| `CallElimCorrect.substOldPostSubset` | gpt-6-astra / max | original | 64.7447% | +27.3377 pp | 2 |
| `CallElimCorrect.substOldPostSubset` | gpt-6-luna / high | deterministic | 37.4070% | +0.0000 pp | 2 |
| `CallElimCorrect.substOldPostSubset` | gpt-6-luna / high | original | 33.3333% | -4.0737 pp | 3 |
| `CallElimCorrect.substOldPostSubset` | gpt-6-luna / max | deterministic | 46.6554% | +9.2484 pp | 16 |
| `CallElimCorrect.substOldPostSubset` | gpt-6-luna / max | original | 35.0860% | -2.3210 pp | 6 |
| `CallElimCorrect.substOldPostSubset` | gpt-6-luna / medium | deterministic | 39.8030% | +2.3960 pp | 1 |
| `CallElimCorrect.substOldPostSubset` | gpt-6-luna / medium | original | 33.3333% | -4.0737 pp | 1 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-astra / max | deterministic | 62.0023% | +24.6067 pp | 2 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-astra / max | original | 73.2246% | +35.8290 pp | 2 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-luna / high | deterministic | 37.3956% | +0.0000 pp | 3 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-luna / high | original | 33.3333% | -4.0623 pp | 2 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-luna / max | deterministic | 54.2062% | +16.8106 pp | 13 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-luna / max | original | 49.7488% | +12.3532 pp | 7 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-luna / medium | deterministic | 37.3956% | +0.0000 pp | 1 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-luna / medium | original | 33.3333% | -4.0623 pp | 1 |
| `Core.InitsUpdatesComm` | gpt-6-astra / max | deterministic | 84.3934% | +33.9500 pp | 1 |
| `Core.InitsUpdatesComm` | gpt-6-astra / max | original | 84.0575% | +33.6141 pp | 1 |
| `Core.InitsUpdatesComm` | gpt-6-luna / high | deterministic | 53.2419% | +2.7985 pp | 3 |
| `Core.InitsUpdatesComm` | gpt-6-luna / high | original | 33.7803% | -16.6631 pp | 5 |
| `Core.InitsUpdatesComm` | gpt-6-luna / max | deterministic | 65.5010% | +15.0576 pp | 1 |
| `Core.InitsUpdatesComm` | gpt-6-luna / max | original | 64.9968% | +14.5533 pp | 3 |
| `Core.InitsUpdatesComm` | gpt-6-luna / medium | deterministic | 50.4434% | +0.0000 pp | 1 |
| `Core.InitsUpdatesComm` | gpt-6-luna / medium | original | 33.3333% | -17.1101 pp | 1 |
| `fundamental_theorem_of_variational_calculus'` | gpt-6-astra / max | deterministic | 85.2217% | +41.7597 pp | 1 |
| `fundamental_theorem_of_variational_calculus'` | gpt-6-astra / max | original | 85.3108% | +41.8489 pp | 1 |
| `fundamental_theorem_of_variational_calculus'` | gpt-6-luna / high | deterministic | 43.5391% | +0.0771 pp | 1 |
| `fundamental_theorem_of_variational_calculus'` | gpt-6-luna / high | original | 36.7562% | -6.7058 pp | 3 |
| `fundamental_theorem_of_variational_calculus'` | gpt-6-luna / max | deterministic | 68.3862% | +24.9242 pp | 2 |
| `fundamental_theorem_of_variational_calculus'` | gpt-6-luna / max | original | 37.4819% | -5.9801 pp | 2 |
| `fundamental_theorem_of_variational_calculus'` | gpt-6-luna / medium | deterministic | 43.6191% | +0.1571 pp | 0 |
| `fundamental_theorem_of_variational_calculus'` | gpt-6-luna / medium | original | 34.3026% | -9.1594 pp | 0 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | gpt-6-astra / max | deterministic | 72.8283% | +25.6856 pp | 5 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | gpt-6-astra / max | original | 73.5515% | +26.4088 pp | 3 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | gpt-6-luna / high | deterministic | 47.1427% | +0.0000 pp | 1 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | gpt-6-luna / high | original | 33.3333% | -13.8094 pp | 2 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | gpt-6-luna / max | deterministic | 47.1427% | +0.0000 pp | 2 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | gpt-6-luna / max | original | 33.8151% | -13.3276 pp | 3 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | gpt-6-luna / medium | deterministic | 47.4218% | +0.2791 pp | 0 |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | gpt-6-luna / medium | original | 33.3333% | -13.8094 pp | 0 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | gpt-6-astra / max | deterministic | 73.2223% | +32.6598 pp | 3 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | gpt-6-astra / max | original | 67.2208% | +26.6583 pp | 4 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | gpt-6-luna / high | deterministic | 40.5626% | +0.0000 pp | 2 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | gpt-6-luna / high | original | 33.3333% | -7.2292 pp | 0 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | gpt-6-luna / max | deterministic | 43.1172% | +2.5546 pp | 15 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | gpt-6-luna / max | original | 39.0157% | -1.5468 pp | 7 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | gpt-6-luna / medium | deterministic | 40.5626% | +0.0000 pp | 2 |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | gpt-6-luna / medium | original | 33.3333% | -7.2292 pp | 2 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | gpt-6-astra / max | deterministic | 68.8351% | +34.7998 pp | 1 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | gpt-6-astra / max | original | 63.4856% | +29.4502 pp | 1 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | gpt-6-luna / high | deterministic | 34.3610% | +0.3257 pp | 2 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | gpt-6-luna / high | original | 33.3333% | -0.7020 pp | 2 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | gpt-6-luna / max | deterministic | 53.7037% | +19.6683 pp | 3 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | gpt-6-luna / max | original | 57.0249% | +22.9896 pp | 5 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | gpt-6-luna / medium | deterministic | 34.0353% | +0.0000 pp | 1 |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | gpt-6-luna / medium | original | 33.3333% | -0.7020 pp | 1 |
| `Cslib.SKI.parallelReduction_diamond` | gpt-6-astra / max | deterministic | 59.8517% | +26.3379 pp | 1 |
| `Cslib.SKI.parallelReduction_diamond` | gpt-6-astra / max | original | 60.4531% | +26.9394 pp | 1 |
| `Cslib.SKI.parallelReduction_diamond` | gpt-6-luna / high | deterministic | 48.2783% | +14.7645 pp | 2 |
| `Cslib.SKI.parallelReduction_diamond` | gpt-6-luna / high | original | 33.3333% | -0.1804 pp | 4 |
| `Cslib.SKI.parallelReduction_diamond` | gpt-6-luna / max | deterministic | 48.2752% | +14.7615 pp | 3 |
| `Cslib.SKI.parallelReduction_diamond` | gpt-6-luna / max | original | 45.6310% | +12.1173 pp | 1 |
| `Cslib.SKI.parallelReduction_diamond` | gpt-6-luna / medium | deterministic | 33.5862% | +0.0724 pp | 1 |
| `Cslib.SKI.parallelReduction_diamond` | gpt-6-luna / medium | original | 33.3333% | -0.1804 pp | 0 |
| `Cslib.CCS.bisimilarity_congr_choice` | gpt-6-astra / max | deterministic | 72.7765% | +39.4435 pp | 1 |
| `Cslib.CCS.bisimilarity_congr_choice` | gpt-6-astra / max | original | 73.2953% | +39.9622 pp | 1 |
| `Cslib.CCS.bisimilarity_congr_choice` | gpt-6-luna / high | deterministic | 63.2844% | +29.9513 pp | 3 |
| `Cslib.CCS.bisimilarity_congr_choice` | gpt-6-luna / high | original | 63.3202% | +29.9872 pp | 3 |
| `Cslib.CCS.bisimilarity_congr_choice` | gpt-6-luna / max | deterministic | 72.5012% | +39.1682 pp | 1 |
| `Cslib.CCS.bisimilarity_congr_choice` | gpt-6-luna / max | original | 73.3139% | +39.9809 pp | 1 |
| `Cslib.CCS.bisimilarity_congr_choice` | gpt-6-luna / medium | deterministic | 33.3331% | +0.0000 pp | 1 |
| `Cslib.CCS.bisimilarity_congr_choice` | gpt-6-luna / medium | original | 33.3333% | +0.0003 pp | 1 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | gpt-6-astra / max | deterministic | 76.1389% | +38.0953 pp | 3 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | gpt-6-astra / max | original | 77.3846% | +39.3409 pp | 2 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | gpt-6-luna / high | deterministic | 38.1759% | +0.1322 pp | 0 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | gpt-6-luna / high | original | 33.8255% | -4.2181 pp | 4 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | gpt-6-luna / max | deterministic | 41.8822% | +3.8385 pp | 4 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | gpt-6-luna / max | original | 36.1257% | -1.9180 pp | 7 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | gpt-6-luna / medium | deterministic | 38.0436% | +0.0000 pp | 0 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | gpt-6-luna / medium | original | 33.4033% | -4.6404 pp | 0 |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | gpt-6-astra / max | deterministic | 88.5262% | +48.6270 pp | 3 |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | gpt-6-astra / max | original | 86.5350% | +46.6359 pp | 1 |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | gpt-6-luna / high | deterministic | 54.2829% | +14.3837 pp | 6 |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | gpt-6-luna / high | original | 33.3333% | -6.5658 pp | 3 |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | gpt-6-luna / max | deterministic | 56.4340% | +16.5349 pp | 5 |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | gpt-6-luna / max | original | 46.0808% | +6.1816 pp | 5 |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | gpt-6-luna / medium | deterministic | 39.8992% | +0.0000 pp | 1 |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | gpt-6-luna / medium | original | 33.3333% | -6.5658 pp | 0 |
| `interleaved_affine_gaps_imply_tensor_gaps` | gpt-6-astra / max | deterministic | 84.2589% | +41.3097 pp | 3 |
| `interleaved_affine_gaps_imply_tensor_gaps` | gpt-6-astra / max | original | 81.9470% | +38.9978 pp | 3 |
| `interleaved_affine_gaps_imply_tensor_gaps` | gpt-6-luna / high | deterministic | 42.9492% | +0.0000 pp | 6 |
| `interleaved_affine_gaps_imply_tensor_gaps` | gpt-6-luna / high | original | 34.6718% | -8.2775 pp | 6 |
| `interleaved_affine_gaps_imply_tensor_gaps` | gpt-6-luna / max | deterministic | 45.7305% | +2.7813 pp | 4 |
| `interleaved_affine_gaps_imply_tensor_gaps` | gpt-6-luna / max | original | 43.3147% | +0.3655 pp | 5 |
| `interleaved_affine_gaps_imply_tensor_gaps` | gpt-6-luna / medium | deterministic | 42.9492% | +0.0000 pp | 0 |
| `interleaved_affine_gaps_imply_tensor_gaps` | gpt-6-luna / medium | original | 34.5491% | -8.4002 pp | 1 |
| `putnam_1964_a4` | gpt-6-astra / max | deterministic | 91.5995% | +18.2801 pp | 3 |
| `putnam_1964_a4` | gpt-6-astra / max | original | 93.3294% | +20.0099 pp | 1 |
| `putnam_1964_a4` | gpt-6-luna / high | deterministic | 73.3195% | +0.0000 pp | 0 |
| `putnam_1964_a4` | gpt-6-luna / high | original | 86.5513% | +13.2318 pp | 1 |
| `putnam_1964_a4` | gpt-6-luna / max | deterministic | 78.7606% | +5.4411 pp | 5 |
| `putnam_1964_a4` | gpt-6-luna / max | original | 79.4776% | +6.1581 pp | 2 |
| `putnam_1964_a4` | gpt-6-luna / medium | deterministic | 73.3952% | +0.0758 pp | 0 |
| `putnam_1964_a4` | gpt-6-luna / medium | original | 33.9293% | -39.3902 pp | 1 |
| `putnam_1964_b2` | gpt-6-astra / max | deterministic | 97.8854% | +10.8312 pp | 1 |
| `putnam_1964_b2` | gpt-6-astra / max | original | 95.2379% | +8.1836 pp | 2 |
| `putnam_1964_b2` | gpt-6-luna / high | deterministic | 89.5905% | +2.5363 pp | 3 |
| `putnam_1964_b2` | gpt-6-luna / high | original | 33.3333% | -53.7210 pp | 4 |
| `putnam_1964_b2` | gpt-6-luna / max | deterministic | 92.8328% | +5.7785 pp | 3 |
| `putnam_1964_b2` | gpt-6-luna / max | original | 85.4857% | -1.5686 pp | 5 |
| `putnam_1964_b2` | gpt-6-luna / medium | deterministic | 87.0543% | +0.0000 pp | 2 |
| `putnam_1964_b2` | gpt-6-luna / medium | original | 33.3333% | -53.7210 pp | 0 |
| `putnam_1995_a3` | gpt-6-astra / max | deterministic | 92.5263% | +37.3656 pp | 2 |
| `putnam_1995_a3` | gpt-6-astra / max | original | 91.6237% | +36.4630 pp | 1 |
| `putnam_1995_a3` | gpt-6-luna / high | deterministic | 55.1606% | +0.0000 pp | 7 |
| `putnam_1995_a3` | gpt-6-luna / high | original | 33.3333% | -21.8273 pp | 4 |
| `putnam_1995_a3` | gpt-6-luna / max | deterministic | 81.0448% | +25.8842 pp | 1 |
| `putnam_1995_a3` | gpt-6-luna / max | original | 69.0828% | +13.9221 pp | 6 |
| `putnam_1995_a3` | gpt-6-luna / medium | deterministic | 56.0621% | +0.9014 pp | 1 |
| `putnam_1995_a3` | gpt-6-luna / medium | original | 33.3333% | -21.8273 pp | 0 |

New calls after the [Luna recovery](recovery/README.md) keep source projects read-only and route validity checks through the host. Prompts and scoring stay fixed; `isolated_calls` records the execution-policy change.

Usage and tool counts in [per_problem.csv](per_problem.csv) cover terminal cells only. Pending work and excluded pilot usage are additional; unknown usage is never zero. The full report is [report.json](report.json).
