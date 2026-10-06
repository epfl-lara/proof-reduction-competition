# Score-feedback optimization

Updated 2026-10-06T12:41:29.168553+00:00. **complete**: 15/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol | max | 15/15 | 86.951351% | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | — | +0.038044 pp | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.

| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | 15/15 | 1.069169 USD | 1.733278 USD | 0 |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6.1-sol / max | 86.144497% | — | 33 |
| CallElimCorrect.extractedOldExprInVars | gpt-6.1-sol / max | 87.436536% | — | 28 |
| Core.InitsUpdatesComm | gpt-6.1-sol / max | 85.759290% | — | 10 |
| fundamental_theorem_of_variational_calculus' | gpt-6.1-sol / max | 90.500181% | — | 38 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6.1-sol / max | 84.706493% | — | 30 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6.1-sol / max | 80.862259% | — | 27 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6.1-sol / max | 82.254121% | — | 27 |
| Cslib.SKI.parallelReduction_diamond | gpt-6.1-sol / max | 75.314995% | — | 14 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6.1-sol / max | 85.158166% | — | 28 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6.1-sol / max | 75.353935% | — | 6 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6.1-sol / max | 91.322532% | — | 19 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6.1-sol / max | 89.387019% | — | 23 |
| putnam_1964_a4 | gpt-6.1-sol / max | 95.740805% | — | 16 |
| putnam_1964_b2 | gpt-6.1-sol / max | 99.004944% | — | 24 |
| putnam_1995_a3 | gpt-6.1-sol / max | 95.324495% | — | 20 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
