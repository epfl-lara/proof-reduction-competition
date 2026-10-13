# Score-feedback optimization

Updated 2026-10-13T08:33:15.804239+00:00. **complete**: 15/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol | max | 15/15 | 89.265062% | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | — | +0.000000 pp | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. Best-effort estimates combine reported usage with explicitly recorded estimates for missing counters. The budget is an approximate per-problem target; unreported spending remains flagged. Running cells are excluded.

| Model / effort | Estimated terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | 15/15 | 3.006968 USD | 3.016934 USD | 15 |

Best-effort usage policy: 10 terminal problems include estimated missing usage. Failed requests without partial output are estimated at zero; partial responses and compaction use recorded payload estimates. Reported counters and missing-usage flags are retained. The per-problem budget is an approximate cost target.

## Terminal cells

| Theorem | Model / effort | Status | Score | Change from historical | Tool checks |
| --- | --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6.1-sol / max | complete | 89.465659% | — | 0 |
| CallElimCorrect.extractedOldExprInVars | gpt-6.1-sol / max | complete | 92.157729% | — | 0 |
| Core.InitsUpdatesComm | gpt-6.1-sol / max | complete | 86.785779% | — | 0 |
| fundamental_theorem_of_variational_calculus' | gpt-6.1-sol / max | complete | 90.561355% | — | 0 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6.1-sol / max | complete | 86.006887% | — | 0 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6.1-sol / max | complete | 80.207080% | — | 0 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6.1-sol / max | complete | 90.386644% | — | 0 |
| Cslib.SKI.parallelReduction_diamond | gpt-6.1-sol / max | complete | 75.494969% | — | 0 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6.1-sol / max | complete | 85.990638% | — | 0 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6.1-sol / max | complete | 84.970378% | — | 0 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6.1-sol / max | complete | 93.855852% | — | 0 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6.1-sol / max | complete | 91.482902% | — | 0 |
| putnam_1964_a4 | gpt-6.1-sol / max | complete | 96.569185% | — | 0 |
| putnam_1964_b2 | gpt-6.1-sol / max | complete | 99.117889% | — | 31 |
| putnam_1995_a3 | gpt-6.1-sol / max | complete | 95.922985% | — | 0 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
