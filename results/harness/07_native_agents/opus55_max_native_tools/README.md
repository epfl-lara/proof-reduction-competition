# Score-feedback optimization

Updated 2026-10-05T13:29:09.600396+00:00. **partial**: 10/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| claude-opus-5-5 | max | 10/15 | pending | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| claude-opus-5-5 / max | — | pending | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.

| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| claude-opus-5-5 / max | 1/10 | 13.292267 USD | 13.292267 USD | 1 |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | claude-opus-5-5 / max | 88.644182% | — | 50 |
| CallElimCorrect.extractedOldExprInVars | claude-opus-5-5 / max | 92.893493% | — | 14 |
| Core.InitsUpdatesComm | claude-opus-5-5 / max | 86.863652% | — | 8 |
| fundamental_theorem_of_variational_calculus' | claude-opus-5-5 / max | 89.444200% | — | 11 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | claude-opus-5-5 / max | 34.035319% | — | 0 |
| Cslib.SKI.parallelReduction_diamond | claude-opus-5-5 / max | 33.513756% | — | 0 |
| Cslib.CCS.bisimilarity_congr_choice | claude-opus-5-5 / max | 33.333333% | — | 0 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | claude-opus-5-5 / max | 38.043633% | — | 0 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | claude-opus-5-5 / max | 39.899173% | — | 0 |
| interleaved_affine_gaps_imply_tensor_gaps | claude-opus-5-5 / max | 42.949222% | — | 0 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
| putnam_1964_b2 | claude-opus-5-5 / max | 1 | 87.054294% |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | claude-opus-5-5 / max | 9 | 85.966137% |
| putnam_1964_a4 | claude-opus-5-5 / max | 1 | 73.319454% |
| putnam_1995_a3 | claude-opus-5-5 / max | 1 | 55.160632% |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | claude-opus-5-5 / max | 6 | 79.480707% |
