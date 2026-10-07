# Score-feedback optimization

Updated 2026-10-07T08:04:29.454378+00:00. **complete**: 15/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next | xhigh | 15/15 | 78.815525% | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next / xhigh | — | +0.030006 pp | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.

| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next / xhigh | 0/15 | — | — | 0 |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | Qwen/Qwen3.8-Flash-Next / xhigh | 74.512157% | — | 28 |
| CallElimCorrect.extractedOldExprInVars | Qwen/Qwen3.8-Flash-Next / xhigh | 80.818744% | — | 126 |
| Core.InitsUpdatesComm | Qwen/Qwen3.8-Flash-Next / xhigh | 84.709308% | — | 35 |
| fundamental_theorem_of_variational_calculus' | Qwen/Qwen3.8-Flash-Next / xhigh | 88.930888% | — | 101 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | Qwen/Qwen3.8-Flash-Next / xhigh | 68.917669% | — | 11 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | Qwen/Qwen3.8-Flash-Next / xhigh | 58.748858% | — | 13 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | Qwen/Qwen3.8-Flash-Next / xhigh | 69.040447% | — | 18 |
| Cslib.SKI.parallelReduction_diamond | Qwen/Qwen3.8-Flash-Next / xhigh | 57.989770% | — | 12 |
| Cslib.CCS.bisimilarity_congr_choice | Qwen/Qwen3.8-Flash-Next / xhigh | 86.289752% | — | 52 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | Qwen/Qwen3.8-Flash-Next / xhigh | 74.774845% | — | 7 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | Qwen/Qwen3.8-Flash-Next / xhigh | 78.687099% | — | 2 |
| interleaved_affine_gaps_imply_tensor_gaps | Qwen/Qwen3.8-Flash-Next / xhigh | 75.301867% | — | 12 |
| putnam_1964_a4 | Qwen/Qwen3.8-Flash-Next / xhigh | 92.345460% | — | 12 |
| putnam_1964_b2 | Qwen/Qwen3.8-Flash-Next / xhigh | 98.406538% | — | 73 |
| putnam_1995_a3 | Qwen/Qwen3.8-Flash-Next / xhigh | 92.759468% | — | 32 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
