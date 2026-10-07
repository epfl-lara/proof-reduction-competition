# Score-feedback optimization

Updated 2026-10-07T12:06:46.296280+00:00. **partial**: 7/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next | xhigh | 7/15 | pending | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next / xhigh | — | pending | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.

| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next / xhigh | 0/7 | — | — | 0 |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | Qwen/Qwen3.8-Flash-Next / xhigh | 80.839543% | — | 27 |
| CallElimCorrect.extractedOldExprInVars | Qwen/Qwen3.8-Flash-Next / xhigh | 87.135803% | — | 82 |
| Core.InitsUpdatesComm | Qwen/Qwen3.8-Flash-Next / xhigh | 84.587488% | — | 32 |
| fundamental_theorem_of_variational_calculus' | Qwen/Qwen3.8-Flash-Next / xhigh | 89.489531% | — | 116 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | Qwen/Qwen3.8-Flash-Next / xhigh | 68.723734% | — | 22 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | Qwen/Qwen3.8-Flash-Next / xhigh | 52.634524% | — | 12 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | Qwen/Qwen3.8-Flash-Next / xhigh | 71.736339% | — | 14 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
| Cslib.SKI.parallelReduction_diamond | Qwen/Qwen3.8-Flash-Next / xhigh | 6 | 57.758769% |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | Qwen/Qwen3.8-Flash-Next / xhigh | 5 | 38.043633% |
| Cslib.CCS.bisimilarity_congr_choice | Qwen/Qwen3.8-Flash-Next / xhigh | 23 | 74.567695% |
