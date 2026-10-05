# Score-feedback optimization

Updated 2026-10-04T20:26:58.314671+00:00. **complete**: 45/45 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6-astra | max | 15/15 | 86.977844% | 78.093430% | — |
| gpt-6-astra | low | 15/15 | 75.301134% | 57.222638% | 59.407773% |
| gpt-6-luna | max | 15/15 | 61.320048% | 53.045428% | 52.740977% |

Deterministic placement: `score_each`. Both modes share the same selected deterministic seed and final cleanup.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| gpt-6-astra / max | 88.384406% | +0.000000 pp | 105 | 100.00% |
| gpt-6-astra / low | 78.130010% | +0.024241 pp | 39 | 90.48% |
| gpt-6-luna / max | 65.135096% | +0.081668 pp | 129 | 96.69% |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6-astra / low | 79.944091% | +39.857850 pp | 8 |
| CallElimCorrect.substOldPostSubset | gpt-6-astra / max | 85.641562% | +20.896875 pp | 10 |
| CallElimCorrect.substOldPostSubset | gpt-6-luna / max | 41.943609% | +6.857623 pp | 14 |
| CallElimCorrect.extractedOldExprInVars | gpt-6-astra / low | 75.450504% | +40.943497 pp | 9 |
| CallElimCorrect.extractedOldExprInVars | gpt-6-astra / max | 90.027375% | +16.802822 pp | 11 |
| CallElimCorrect.extractedOldExprInVars | gpt-6-luna / max | 68.499646% | +18.750831 pp | 33 |
| Core.InitsUpdatesComm | gpt-6-astra / low | 84.063558% | -0.077736 pp | 3 |
| Core.InitsUpdatesComm | gpt-6-astra / max | 85.771672% | +1.714171 pp | 10 |
| Core.InitsUpdatesComm | gpt-6-luna / max | 82.072918% | +17.076159 pp | 32 |
| fundamental_theorem_of_variational_calculus' | gpt-6-astra / low | 85.042867% | +4.919687 pp | 4 |
| fundamental_theorem_of_variational_calculus' | gpt-6-astra / max | 88.768048% | +3.457209 pp | 13 |
| fundamental_theorem_of_variational_calculus' | gpt-6-luna / max | 59.478765% | +21.996860 pp | 18 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6-astra / low | 74.023007% | +40.689674 pp | 10 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6-astra / max | 83.605441% | +10.053935 pp | 9 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6-luna / max | 47.142714% | +13.327593 pp | 9 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6-astra / low | 63.180958% | +29.409299 pp | 4 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6-astra / max | 78.099924% | +10.879117 pp | 12 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6-luna / max | 51.647837% | +12.632110 pp | 24 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6-astra / low | 70.275369% | +32.621888 pp | 4 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6-astra / max | 83.269630% | +19.784074 pp | 19 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6-luna / max | 64.810701% | +7.785808 pp | 41 |
| Cslib.SKI.parallelReduction_diamond | gpt-6-astra / low | 61.424104% | +15.967997 pp | 2 |
| Cslib.SKI.parallelReduction_diamond | gpt-6-astra / max | 74.086721% | +13.633578 pp | 16 |
| Cslib.SKI.parallelReduction_diamond | gpt-6-luna / max | 50.246608% | +4.615575 pp | 14 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6-astra / low | 78.704579% | +5.925881 pp | 4 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6-astra / max | 81.945043% | +8.649732 pp | 14 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6-luna / max | 68.900628% | -4.413320 pp | 4 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6-astra / low | 61.198765% | +25.794960 pp | 4 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6-astra / max | 85.410744% | +8.026169 pp | 10 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6-luna / max | 40.613477% | +4.487822 pp | 15 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6-astra / low | 57.875211% | +9.868508 pp | 4 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6-astra / max | 91.313012% | +4.777978 pp | 8 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6-luna / max | 50.459357% | +4.378551 pp | 11 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6-astra / low | 56.735917% | +11.285044 pp | 9 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6-astra / max | 89.038551% | +7.091524 pp | 8 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6-luna / max | 45.347123% | +2.032441 pp | 7 |
| putnam_1964_a4 | gpt-6-astra / low | 92.641660% | +5.434002 pp | 3 |
| putnam_1964_a4 | gpt-6-astra / max | 94.500173% | +1.170789 pp | 10 |
| putnam_1964_a4 | gpt-6-luna / max | 73.319454% | -6.158144 pp | 5 |
| putnam_1964_b2 | gpt-6-astra / low | 97.048355% | +4.804461 pp | 4 |
| putnam_1964_b2 | gpt-6-astra / max | 99.137058% | +3.899181 pp | 11 |
| putnam_1964_b2 | gpt-6-luna / max | 93.464098% | +7.978370 pp | 3 |
| putnam_1995_a3 | gpt-6-astra / low | 91.908060% | +3.732429 pp | 4 |
| putnam_1995_a3 | gpt-6-astra / max | 94.052702% | +2.429052 pp | 8 |
| putnam_1995_a3 | gpt-6-luna / max | 81.853784% | +12.771022 pp | 7 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
