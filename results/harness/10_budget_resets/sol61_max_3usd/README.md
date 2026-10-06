# Score-feedback optimization

Updated 2026-10-06T19:02:51.716674+00:00. **complete**: 15/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol | max | 15/15 | 89.357422% | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | — | +0.000000 pp | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.

| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | 4/15 | 2.558455 USD | 2.765382 USD | 0 |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6.1-sol / max | 90.625224% | — | 60 |
| CallElimCorrect.extractedOldExprInVars | gpt-6.1-sol / max | 94.190829% | — | 101 |
| Core.InitsUpdatesComm | gpt-6.1-sol / max | 87.515606% | — | 72 |
| fundamental_theorem_of_variational_calculus' | gpt-6.1-sol / max | 90.970541% | — | 80 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6.1-sol / max | 85.886909% | — | 70 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6.1-sol / max | 81.402488% | — | 69 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6.1-sol / max | 85.205857% | — | 54 |
| Cslib.SKI.parallelReduction_diamond | gpt-6.1-sol / max | 75.077129% | — | 79 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6.1-sol / max | 86.934466% | — | 75 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6.1-sol / max | 85.251222% | — | 42 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6.1-sol / max | 93.407634% | — | 56 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6.1-sol / max | 91.345737% | — | 38 |
| putnam_1964_a4 | gpt-6.1-sol / max | 97.219136% | — | 63 |
| putnam_1964_b2 | gpt-6.1-sol / max | 99.217583% | — | 72 |
| putnam_1995_a3 | gpt-6.1-sol / max | 96.110969% | — | 76 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
