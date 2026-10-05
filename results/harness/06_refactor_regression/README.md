# Score-feedback optimization

Updated 2026-10-05T02:45:46.779416+00:00. **complete**: 15/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol | max | 15/15 | 86.575834% | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | — | +0.018407 pp | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.

| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | 15/15 | 1.060463 USD | 2.536752 USD | 0 |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6.1-sol / max | 82.665762% | — | 29 |
| CallElimCorrect.extractedOldExprInVars | gpt-6.1-sol / max | 85.053197% | — | 22 |
| Core.InitsUpdatesComm | gpt-6.1-sol / max | 84.941812% | — | 17 |
| fundamental_theorem_of_variational_calculus' | gpt-6.1-sol / max | 88.992915% | — | 18 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6.1-sol / max | 83.512901% | — | 22 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6.1-sol / max | 78.840365% | — | 20 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6.1-sol / max | 86.807591% | — | 28 |
| Cslib.SKI.parallelReduction_diamond | gpt-6.1-sol / max | 74.679539% | — | 23 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6.1-sol / max | 84.953800% | — | 14 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6.1-sol / max | 82.519857% | — | 25 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6.1-sol / max | 90.647808% | — | 24 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6.1-sol / max | 85.458382% | — | 18 |
| putnam_1964_a4 | gpt-6.1-sol / max | 95.590031% | — | 23 |
| putnam_1964_b2 | gpt-6.1-sol / max | 98.691726% | — | 20 |
| putnam_1995_a3 | gpt-6.1-sol / max | 95.281826% | — | 18 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
