# Score-feedback optimization

Updated 2026-10-04T16:55:03.318637+00:00. **complete**: 45/45 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6-astra | max | 15/15 | 88.043179% | 78.093430% | — |
| gpt-6-astra | low | 15/15 | 79.118309% | 57.222638% | 59.407773% |
| gpt-6-luna | max | 15/15 | 68.264239% | 53.045428% | 52.740977% |

Deterministic placement: `score_edges`. Both modes share the same selected deterministic seed and final cleanup.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| gpt-6-astra / max | 88.384406% | +0.065451 pp | 0 | 0.00% |
| gpt-6-astra / low | 78.130010% | +0.355821 pp | 0 | 0.00% |
| gpt-6-luna / max | 65.135096% | +0.395794 pp | 0 | 0.00% |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6-astra / low | 80.359956% | +40.273715 pp | 12 |
| CallElimCorrect.substOldPostSubset | gpt-6-astra / max | 87.127696% | +22.383010 pp | 28 |
| CallElimCorrect.substOldPostSubset | gpt-6-luna / max | 49.517284% | +14.431298 pp | 43 |
| CallElimCorrect.extractedOldExprInVars | gpt-6-astra / low | 71.005888% | +36.498881 pp | 8 |
| CallElimCorrect.extractedOldExprInVars | gpt-6-astra / max | 91.127965% | +17.903412 pp | 24 |
| CallElimCorrect.extractedOldExprInVars | gpt-6-luna / max | 69.763361% | +20.014546 pp | 41 |
| Core.InitsUpdatesComm | gpt-6-astra / low | 84.669697% | +0.528403 pp | 3 |
| Core.InitsUpdatesComm | gpt-6-astra / max | 86.239146% | +2.181645 pp | 14 |
| Core.InitsUpdatesComm | gpt-6-luna / max | 71.956045% | +6.959286 pp | 22 |
| fundamental_theorem_of_variational_calculus' | gpt-6-astra / low | 85.476339% | +5.353159 pp | 4 |
| fundamental_theorem_of_variational_calculus' | gpt-6-astra / max | 89.077768% | +3.766929 pp | 18 |
| fundamental_theorem_of_variational_calculus' | gpt-6-luna / max | 70.648317% | +33.166411 pp | 34 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6-astra / low | 67.955196% | +34.621863 pp | 5 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6-astra / max | 84.973781% | +11.422275 pp | 21 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6-luna / max | 52.561886% | +18.746766 pp | 43 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6-astra / low | 62.227719% | +28.456060 pp | 8 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6-astra / max | 84.078207% | +16.857400 pp | 25 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6-luna / max | 43.718815% | +4.703087 pp | 27 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6-astra / low | 74.032721% | +36.379240 pp | 7 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6-astra / max | 81.519187% | +18.033632 pp | 18 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6-luna / max | 60.485588% | +3.460695 pp | 28 |
| Cslib.SKI.parallelReduction_diamond | gpt-6-astra / low | 68.802549% | +23.346443 pp | 11 |
| Cslib.SKI.parallelReduction_diamond | gpt-6-astra / max | 73.695268% | +13.242125 pp | 23 |
| Cslib.SKI.parallelReduction_diamond | gpt-6-luna / max | 60.544315% | +14.913282 pp | 23 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6-astra / low | 79.956563% | +7.177865 pp | 4 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6-astra / max | 85.719200% | +12.423890 pp | 17 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6-luna / max | 75.478259% | +2.164310 pp | 14 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6-astra / low | 65.703224% | +30.299419 pp | 4 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6-astra / max | 86.117216% | +8.732641 pp | 13 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6-luna / max | 64.134074% | +28.008420 pp | 36 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6-astra / low | 83.083596% | +35.076893 pp | 7 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6-astra / max | 91.559448% | +5.024414 pp | 15 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6-luna / max | 65.322911% | +19.242105 pp | 20 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6-astra / low | 81.379688% | +35.928814 pp | 6 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6-astra / max | 88.921578% | +6.974551 pp | 15 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6-luna / max | 67.029838% | +23.715156 pp | 49 |
| putnam_1964_a4 | gpt-6-astra / low | 93.297580% | +6.089922 pp | 4 |
| putnam_1964_a4 | gpt-6-astra / max | 95.800135% | +2.470751 pp | 11 |
| putnam_1964_a4 | gpt-6-luna / max | 86.498682% | +7.021083 pp | 25 |
| putnam_1964_b2 | gpt-6-astra / low | 97.135698% | +4.891803 pp | 6 |
| putnam_1964_b2 | gpt-6-astra / max | 99.061052% | +3.823176 pp | 19 |
| putnam_1964_b2 | gpt-6-luna / max | 97.517394% | +12.031665 pp | 27 |
| putnam_1995_a3 | gpt-6-astra / low | 91.688217% | +3.512586 pp | 4 |
| putnam_1995_a3 | gpt-6-astra / max | 95.630033% | +4.006383 pp | 21 |
| putnam_1995_a3 | gpt-6-luna / max | 88.786821% | +19.704060 pp | 39 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
