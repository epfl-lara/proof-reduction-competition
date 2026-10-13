# Score-feedback optimization

Updated 2026-10-13T07:19:16.250624+00:00. **partial**: 15/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol | max | 15/15 | pending | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | — | pending | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. Best-effort estimates combine reported usage with explicitly recorded estimates for missing counters. The budget is an approximate per-problem target; unreported spending remains flagged. Running cells are excluded.

| Model / effort | Estimated terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | 15/15 | 2.906607 USD | 3.016934 USD | 13 |

Best-effort usage policy: 10 terminal problems include estimated missing usage. Failed requests without partial output are estimated at zero; partial responses and compaction use recorded payload estimates. Reported counters and missing-usage flags are retained. The per-problem budget is an approximate cost target.

## Terminal cells

| Theorem | Model / effort | Status | Score | Change from historical | Tool checks |
| --- | --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6.1-sol / max | complete | 89.465659% | — | 116 |
| CallElimCorrect.extractedOldExprInVars | gpt-6.1-sol / max | complete | 92.157729% | — | 104 |
| Core.InitsUpdatesComm | gpt-6.1-sol / max | complete | 86.785779% | — | 74 |
| fundamental_theorem_of_variational_calculus' | gpt-6.1-sol / max | complete | 90.561355% | — | 104 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6.1-sol / max | complete | 86.006887% | — | 72 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6.1-sol / max | complete | 80.104425% | — | 79 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6.1-sol / max | complete | 90.386644% | — | 78 |
| Cslib.SKI.parallelReduction_diamond | gpt-6.1-sol / max | complete | 75.494969% | — | 80 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6.1-sol / max | complete | 85.990638% | — | 97 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6.1-sol / max | complete | 84.970378% | — | 56 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6.1-sol / max | complete | 93.855852% | — | 70 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6.1-sol / max | complete | 91.482902% | — | 67 |
| putnam_1964_a4 | gpt-6.1-sol / max | complete | 96.569185% | — | 86 |
| putnam_1964_b2 | gpt-6.1-sol / max | incomplete | 99.117889% | — | 92 |
| putnam_1995_a3 | gpt-6.1-sol / max | incomplete | 95.922985% | — | 73 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
