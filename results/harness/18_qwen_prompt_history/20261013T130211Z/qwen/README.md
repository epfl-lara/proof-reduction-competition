# Score-feedback optimization

Updated 2026-10-13T17:49:31.534291+00:00. **complete**: 15/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next | xhigh | 15/15 | 81.769564% | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next / xhigh | — | +0.000000 pp | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.

| Model / effort | Estimated terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next / xhigh | 0/15 | — | — | 0 |

## Terminal cells

| Theorem | Model / effort | Status | Score | Change from historical | Tool checks |
| --- | --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 80.767865% | — | 19 |
| CallElimCorrect.extractedOldExprInVars | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 77.395247% | — | 67 |
| Core.InitsUpdatesComm | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 84.786565% | — | 26 |
| fundamental_theorem_of_variational_calculus' | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 88.466600% | — | 36 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 73.951217% | — | 5 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 62.371974% | — | 72 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 71.736622% | — | 21 |
| Cslib.SKI.parallelReduction_diamond | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 68.108752% | — | 9 |
| Cslib.CCS.bisimilarity_congr_choice | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 86.363566% | — | 54 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 74.464514% | — | 8 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 90.278454% | — | 40 |
| interleaved_affine_gaps_imply_tensor_gaps | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 81.776087% | — | 10 |
| putnam_1964_a4 | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 93.915449% | — | 23 |
| putnam_1964_b2 | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 98.536753% | — | 22 |
| putnam_1995_a3 | Qwen/Qwen3.8-Flash-Next / xhigh | complete | 93.623795% | — | 59 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
