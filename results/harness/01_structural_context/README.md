# Structural context and correctness tools

Updated 2026-10-03T21:10:35.579619+00:00. **complete**: 30/30 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6-astra | low | 15/15 | 59.407773% | 57.222638% | — |
| gpt-6-luna | max | 15/15 | 52.740977% | 53.045428% | — |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6-astra / low | 67.728791% | +27.642551 pp | 2 |
| CallElimCorrect.substOldPostSubset | gpt-6-luna / max | 33.333333% | -1.752653 pp | 5 |
| CallElimCorrect.extractedOldExprInVars | gpt-6-astra / low | 52.004299% | +17.497292 pp | 4 |
| CallElimCorrect.extractedOldExprInVars | gpt-6-luna / max | 39.747819% | -10.000996 pp | 18 |
| Core.InitsUpdatesComm | gpt-6-astra / low | 81.089129% | -3.052166 pp | 1 |
| Core.InitsUpdatesComm | gpt-6-luna / max | 57.882511% | -7.114248 pp | 2 |
| fundamental_theorem_of_variational_calculus' | gpt-6-astra / low | 57.972379% | -22.150801 pp | 2 |
| fundamental_theorem_of_variational_calculus' | gpt-6-luna / max | 55.637310% | +18.155404 pp | 2 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6-astra / low | 35.593999% | +2.260665 pp | 1 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6-luna / max | 33.333333% | -0.481787 pp | 2 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6-astra / low | 38.841393% | +5.069734 pp | 1 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6-luna / max | 38.970713% | -0.045014 pp | 4 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6-astra / low | 37.076339% | -0.577143 pp | 1 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6-luna / max | 53.059408% | -3.965485 pp | 2 |
| Cslib.SKI.parallelReduction_diamond | gpt-6-astra / low | 34.376263% | -11.079843 pp | 1 |
| Cslib.SKI.parallelReduction_diamond | gpt-6-luna / max | 34.376263% | -11.254770 pp | 3 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6-astra / low | 72.778698% | +0.000000 pp | 1 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6-luna / max | 73.313767% | -0.000181 pp | 1 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6-astra / low | 39.738601% | +4.334796 pp | 3 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6-luna / max | 35.310008% | -0.815646 pp | 5 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6-astra / low | 38.948583% | -9.058120 pp | 1 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6-luna / max | 52.372684% | +6.291879 pp | 3 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6-astra / low | 65.886938% | +20.436065 pp | 1 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6-luna / max | 39.497118% | -3.817563 pp | 1 |
| putnam_1964_a4 | gpt-6-astra / low | 87.390619% | +0.182961 pp | 2 |
| putnam_1964_a4 | gpt-6-luna / max | 79.421669% | -0.055929 pp | 5 |
| putnam_1964_b2 | gpt-6-astra / low | 92.590865% | +0.346970 pp | 3 |
| putnam_1964_b2 | gpt-6-luna / max | 85.786133% | +0.300404 pp | 2 |
| putnam_1995_a3 | gpt-6-astra / low | 89.099696% | +0.924064 pp | 2 |
| putnam_1995_a3 | gpt-6-luna / max | 79.072578% | +9.989817 pp | 2 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
