# Score-feedback optimization

Updated 2026-10-06T15:22:55.067288+00:00. **partial**: 15/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next | xhigh | 15/15 | pending | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next / xhigh | — | pending | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.

| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next / xhigh | 0/15 | — | — | 0 |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | Qwen/Qwen3.8-Flash-Next / xhigh | 77.426846% | — | 9 |
| CallElimCorrect.extractedOldExprInVars | Qwen/Qwen3.8-Flash-Next / xhigh | 76.833663% | — | 86 |
| Core.InitsUpdatesComm | Qwen/Qwen3.8-Flash-Next / xhigh | 85.359625% | — | 44 |
| fundamental_theorem_of_variational_calculus' | Qwen/Qwen3.8-Flash-Next / xhigh | 88.389779% | — | 73 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | Qwen/Qwen3.8-Flash-Next / xhigh | 66.588066% | — | 9 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | Qwen/Qwen3.8-Flash-Next / xhigh | 48.316832% | — | 30 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | Qwen/Qwen3.8-Flash-Next / xhigh | 71.362103% | — | 20 |
| Cslib.SKI.parallelReduction_diamond | Qwen/Qwen3.8-Flash-Next / xhigh | 56.954635% | — | 32 |
| Cslib.CCS.bisimilarity_congr_choice | Qwen/Qwen3.8-Flash-Next / xhigh | 77.450464% | — | 25 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | Qwen/Qwen3.8-Flash-Next / xhigh | 74.283052% | — | 13 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | Qwen/Qwen3.8-Flash-Next / xhigh | 76.066030% | — | 6 |
| interleaved_affine_gaps_imply_tensor_gaps | Qwen/Qwen3.8-Flash-Next / xhigh | 42.949222% | — | 1 |
| putnam_1964_a4 | Qwen/Qwen3.8-Flash-Next / xhigh | 73.319454% | — | 0 |
| putnam_1964_b2 | Qwen/Qwen3.8-Flash-Next / xhigh | 87.054294% | — | 24 |
| putnam_1995_a3 | Qwen/Qwen3.8-Flash-Next / xhigh | 91.396840% | — | 18 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
