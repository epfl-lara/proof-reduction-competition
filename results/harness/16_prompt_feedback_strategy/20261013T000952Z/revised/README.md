# Score-feedback optimization

Updated 2026-10-13T03:33:21.288780+00:00. **complete**: 15/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol | max | 15/15 | 89.448630% | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | — | +0.026168 pp | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. Best-effort estimates combine reported usage with explicitly recorded estimates for missing counters. The budget is an approximate per-problem target; unreported spending remains flagged. Running cells are excluded.

| Model / effort | Estimated terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| gpt-6.1-sol / max | 15/15 | 3.005061 USD | 3.013651 USD | 15 |

Best-effort usage policy: 7 terminal problems include estimated missing usage. Failed requests without partial output are estimated at zero; partial responses and compaction use recorded payload estimates. Reported counters and missing-usage flags are retained. The per-problem budget is an approximate cost target.

## Terminal cells

| Theorem | Model / effort | Status | Score | Change from historical | Tool checks |
| --- | --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6.1-sol / max | complete | 89.441932% | — | 121 |
| CallElimCorrect.extractedOldExprInVars | gpt-6.1-sol / max | complete | 93.976339% | — | 115 |
| Core.InitsUpdatesComm | gpt-6.1-sol / max | complete | 87.255312% | — | 83 |
| fundamental_theorem_of_variational_calculus' | gpt-6.1-sol / max | complete | 91.273849% | — | 96 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | gpt-6.1-sol / max | complete | 86.239878% | — | 86 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | gpt-6.1-sol / max | complete | 84.233103% | — | 99 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | gpt-6.1-sol / max | complete | 83.629230% | — | 71 |
| Cslib.SKI.parallelReduction_diamond | gpt-6.1-sol / max | complete | 79.366871% | — | 102 |
| Cslib.CCS.bisimilarity_congr_choice | gpt-6.1-sol / max | complete | 85.386156% | — | 89 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | gpt-6.1-sol / max | complete | 84.747311% | — | 39 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | gpt-6.1-sol / max | complete | 92.232290% | — | 65 |
| interleaved_affine_gaps_imply_tensor_gaps | gpt-6.1-sol / max | complete | 91.410862% | — | 57 |
| putnam_1964_a4 | gpt-6.1-sol / max | complete | 96.996944% | — | 81 |
| putnam_1964_b2 | gpt-6.1-sol / max | complete | 99.102526% | — | 123 |
| putnam_1995_a3 | gpt-6.1-sol / max | complete | 96.436853% | — | 81 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
