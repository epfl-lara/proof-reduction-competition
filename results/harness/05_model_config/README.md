# Score-feedback optimization

Updated 2026-10-04T23:15:36.209923+00:00. **complete**: 30/30 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol | max | 15/15 | 87.342215% | — | — |
| gpt-6-astra | high | 15/15 | 84.319957% | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | — | +0.038737 pp | 0 | 0.00% |
| gpt-6-astra / high | — | +0.129709 pp | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.

| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | 15/15 | 0.987643 USD | 1.672598 USD | 0 |
| gpt-6-astra / high | 15/15 | 1.926246 USD | 3.543124 USD | 3 |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6-astra / high | 80.193178% | — | 16 |
| CallElimCorrect.substOldPostSubset | gpt-6.1-sol / max | 86.211956% | — | 32 |
| CallElimCorrect.extractedOldExprInVars | gpt-6-astra / high | 78.413790% | — | 13 |
| CallElimCorrect.extractedOldExprInVars | gpt-6.1-sol / max | 88.770979% | — | 26 |
| Core.InitsUpdatesComm | gpt-6-astra / high | 84.936326% | — | 6 |
| Core.InitsUpdatesComm | gpt-6.1-sol / max | 85.208307% | — | 11 |
| fundamental_theorem_of_variational_calculus' | gpt-6-astra / high | 86.653514% | — | 10 |
| fundamental_theorem_of_variational_calculus' | gpt-6.1-sol / max | 88.775856% | — | 18 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6-astra / high | 80.639213% | — | 18 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6.1-sol / max | 85.187085% | — | 34 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6-astra / high | 75.684799% | — | 10 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6.1-sol / max | 80.701365% | — | 31 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6-astra / high | 78.400650% | — | 14 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6.1-sol / max | 82.316632% | — | 21 |
| Cslib.SKI.parallelReduction_diamond | gpt-6-astra / high | 73.866491% | — | 16 |
| Cslib.SKI.parallelReduction_diamond | gpt-6.1-sol / max | 74.286927% | — | 24 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6-astra / high | 82.794167% | — | 11 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6.1-sol / max | 85.723860% | — | 25 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6-astra / high | 80.540345% | — | 10 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6.1-sol / max | 86.818503% | — | 26 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6-astra / high | 89.296834% | — | 10 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6.1-sol / max | 91.613119% | — | 16 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6-astra / high | 85.920377% | — | 10 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6.1-sol / max | 85.415323% | — | 17 |
| putnam_1964_a4 | gpt-6-astra / high | 93.624964% | — | 11 |
| putnam_1964_a4 | gpt-6.1-sol / max | 94.878654% | — | 21 |
| putnam_1964_b2 | gpt-6-astra / high | 98.582921% | — | 7 |
| putnam_1964_b2 | gpt-6.1-sol / max | 99.020099% | — | 21 |
| putnam_1995_a3 | gpt-6-astra / high | 95.251785% | — | 9 |
| putnam_1995_a3 | gpt-6.1-sol / max | 95.204557% | — | 20 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
