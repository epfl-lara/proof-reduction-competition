# Score-feedback optimization

Updated 2026-10-06T19:50:20.774769+00:00. **partial**: 15/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gemini-3.8-flash | high | 15/15 | pending | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| gemini-3.8-flash / high | — | pending | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.

| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| gemini-3.8-flash / high | 10/15 | 0.459873 USD | 2.887948 USD | 0 |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gemini-3.8-flash / high | 80.781036% | — | 24 |
| CallElimCorrect.extractedOldExprInVars | gemini-3.8-flash / high | 78.950563% | — | 79 |
| Core.InitsUpdatesComm | gemini-3.8-flash / high | 81.261800% | — | 52 |
| fundamental_theorem_of_variational_calculus' | gemini-3.8-flash / high | 87.984860% | — | 54 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gemini-3.8-flash / high | 54.765094% | — | 32 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gemini-3.8-flash / high | 67.024912% | — | 44 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gemini-3.8-flash / high | 63.860907% | — | 20 |
| Cslib.SKI.parallelReduction_diamond | gemini-3.8-flash / high | 33.513756% | — | 0 |
| Cslib.CCS.bisimilarity_congr_choice | gemini-3.8-flash / high | 33.333333% | — | 0 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gemini-3.8-flash / high | 38.043633% | — | 0 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gemini-3.8-flash / high | 39.899173% | — | 0 |
| interleaved_affine_gaps_imply_tensor_gaps | gemini-3.8-flash / high | 42.949222% | — | 0 |
| putnam_1964_a4 | gemini-3.8-flash / high | 73.319454% | — | 0 |
| putnam_1964_b2 | gemini-3.8-flash / high | 87.054294% | — | 0 |
| putnam_1995_a3 | gemini-3.8-flash / high | 55.160632% | — | 0 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
