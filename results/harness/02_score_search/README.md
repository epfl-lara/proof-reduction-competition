# Score-feedback optimization

Updated 2026-10-03T23:46:55.202028+00:00. **complete**: 45/45 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6-astra | max | 15/15 | 88.384406% | 78.093430% | — |
| gpt-6-astra | low | 15/15 | 78.130010% | 57.222638% | 59.407773% |
| gpt-6-luna | max | 15/15 | 65.135096% | 53.045428% | 52.740977% |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6-astra / low | 75.519306% | +35.433065 pp | 7 |
| CallElimCorrect.substOldPostSubset | gpt-6-astra / max | 90.063364% | +25.318678 pp | 35 |
| CallElimCorrect.substOldPostSubset | gpt-6-luna / max | 45.322907% | +10.236920 pp | 42 |
| CallElimCorrect.extractedOldExprInVars | gpt-6-astra / low | 71.211834% | +36.704827 pp | 12 |
| CallElimCorrect.extractedOldExprInVars | gpt-6-astra / max | 90.780279% | +17.555726 pp | 29 |
| CallElimCorrect.extractedOldExprInVars | gpt-6-luna / max | 66.350401% | +16.601586 pp | 43 |
| Core.InitsUpdatesComm | gpt-6-astra / low | 84.669760% | +0.528465 pp | 4 |
| Core.InitsUpdatesComm | gpt-6-astra / max | 85.960723% | +1.903222 pp | 14 |
| Core.InitsUpdatesComm | gpt-6-luna / max | 78.058566% | +13.061807 pp | 15 |
| fundamental_theorem_of_variational_calculus' | gpt-6-astra / low | 87.021528% | +6.898348 pp | 6 |
| fundamental_theorem_of_variational_calculus' | gpt-6-astra / max | 90.025648% | +4.714809 pp | 18 |
| fundamental_theorem_of_variational_calculus' | gpt-6-luna / max | 70.245738% | +32.763832 pp | 25 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6-astra / low | 63.720817% | +30.387484 pp | 9 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6-astra / max | 84.920570% | +11.369064 pp | 25 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6-luna / max | 34.598049% | +0.782929 pp | 21 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6-astra / low | 59.785624% | +26.013964 pp | 9 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6-astra / max | 78.495324% | +11.274516 pp | 22 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6-luna / max | 45.110347% | +6.094619 pp | 33 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6-astra / low | 71.435086% | +33.781604 pp | 10 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6-astra / max | 87.826024% | +24.340468 pp | 16 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6-luna / max | 66.174202% | +9.149310 pp | 39 |
| Cslib.SKI.parallelReduction_diamond | gpt-6-astra / low | 61.113527% | +15.657420 pp | 5 |
| Cslib.SKI.parallelReduction_diamond | gpt-6-astra / max | 74.967454% | +14.514312 pp | 21 |
| Cslib.SKI.parallelReduction_diamond | gpt-6-luna / max | 61.082457% | +15.451424 pp | 22 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6-astra / low | 79.424517% | +6.645819 pp | 4 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6-astra / max | 84.394397% | +11.099087 pp | 17 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6-luna / max | 75.117101% | +1.803152 pp | 29 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6-astra / low | 72.637529% | +37.233724 pp | 13 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6-astra / max | 87.898784% | +10.514209 pp | 19 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6-luna / max | 40.558949% | +4.433294 pp | 29 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6-astra / low | 85.426374% | +37.419671 pp | 6 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6-astra / max | 91.523903% | +4.988870 pp | 14 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6-luna / max | 74.320038% | +28.239232 pp | 40 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6-astra / low | 78.856367% | +33.405493 pp | 17 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6-astra / max | 89.099390% | +7.152363 pp | 17 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6-luna / max | 61.072230% | +17.757548 pp | 87 |
| putnam_1964_a4 | gpt-6-astra / low | 93.449833% | +6.242174 pp | 4 |
| putnam_1964_a4 | gpt-6-astra / max | 95.645857% | +2.316473 pp | 10 |
| putnam_1964_a4 | gpt-6-luna / max | 84.228328% | +4.750729 pp | 12 |
| putnam_1964_b2 | gpt-6-astra / low | 95.406240% | +3.162346 pp | 7 |
| putnam_1964_b2 | gpt-6-astra / max | 98.975115% | +3.737239 pp | 15 |
| putnam_1964_b2 | gpt-6-luna / max | 90.480526% | +4.994797 pp | 10 |
| putnam_1995_a3 | gpt-6-astra / low | 92.271805% | +4.096173 pp | 3 |
| putnam_1995_a3 | gpt-6-astra / max | 95.189260% | +3.565610 pp | 14 |
| putnam_1995_a3 | gpt-6-luna / max | 84.306608% | +15.223847 pp | 19 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
