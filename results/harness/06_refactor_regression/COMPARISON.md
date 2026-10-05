# Sol 6.1/max refactor replicate

All 15 problems completed and the evidence audit passed. All 36 required
Lean version checks pass. The package refactor preserved the exact prompts,
seed proofs, cached reference records, source-token denominators, selection
margin and cleanup policy. No reference measurements were repeated.

| Metric | Before refactor (05) | After refactor (06) | Change |
| --- | ---: | ---: | ---: |
| Length reduction | 76.399921% | 74.751025% | -1.648896 pp |
| Heartbeat reduction | 85.626723% | 84.976477% | -0.650246 pp |
| Compatibility | 100.000000% | 100.000000% | +0.000000 pp |
| Combined score | 87.342215% | 86.575834% | -0.766381 pp |

The new combined score is **86.575834%**, versus **87.342215%** previously.
Six problems improved and nine worsened; none were omitted.
This is one fresh replicate with an agent that chooses its own search path
and stopping point. It validates the maintained runtime, but does not prove
statistical equivalence or identify a causal score change from refactoring.
The earlier stronger submission remains a separate result; proofs are not
pooled across runs.

| Resource | Before | After |
| --- | ---: | ---: |
| Model calls | 15 | 15 |
| Agent checks | 343 | 321 |
| Accepted improvements | 160 | 144 |
| Completion tokens, including reasoning | 439,344 | 456,353 |
| Estimated total USD | 14.814649 | 15.906938 |
| Estimated mean USD/problem | 0.987643 | 1.060463 |
| Estimated p90 USD/problem | 1.536155 | 1.482645 |
| Estimated maximum USD/problem | 1.672598 | 2.536752 |

Both runs have 0/15 problems above $3 at the saved API-equivalent rates.
The estimates assume Standard service, short context and reported caching;
they are not Codex invoices or certified costs of a future replay.

Quality checks: **293 tests and 102 subtests passed**, with three paid RCP tests
excluded; Black, Ruff and diff checks passed. The final audit covered
**366 saved checks**, **1438 version outcomes**, 15 requests and 15 cleanup jobs.
A limited literal-path scan of 631 completed shell commands flagged
no direct references to other study outputs or credential files. This scan
does not establish filesystem read isolation.

See [structured comparison](comparison.json), [pre-run validation](validation_before_run.json),
[audit](audit.json), [protocol](PROTOCOL.md), and the
[new submission and manifest](conditions/gpt-6.1-sol__max/README.md).

| Problem | Before combined % | After combined % | Change pp | New estimated USD |
| --- | ---: | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | 86.211956 | 82.665762 | -3.546195 | 0.876444 |
| CallElimCorrect.extractedOldExprInVars | 88.770979 | 85.053197 | -3.717782 | 0.676390 |
| Core.InitsUpdatesComm | 85.208307 | 84.941812 | -0.266495 | 0.487593 |
| fundamental_theorem_of_variational_calculus' | 88.775856 | 88.992915 | +0.217059 | 0.986446 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | 85.187085 | 83.512901 | -1.674184 | 0.909233 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | 80.701365 | 78.840365 | -1.861000 | 1.108604 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | 82.316632 | 86.807591 | +4.490960 | 1.482645 |
| Cslib.SKI.parallelReduction_diamond | 74.286927 | 74.679539 | +0.392612 | 0.783248 |
| Cslib.CCS.bisimilarity_congr_choice | 85.723860 | 84.953800 | -0.770060 | 0.852261 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | 86.818503 | 82.519857 | -4.298645 | 2.536752 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | 91.613119 | 90.647808 | -0.965311 | 1.360231 |
| interleaved_affine_gaps_imply_tensor_gaps | 85.415323 | 85.458382 | +0.043059 | 1.100826 |
| putnam_1964_a4 | 94.878654 | 95.590031 | +0.711377 | 1.029495 |
| putnam_1964_b2 | 99.020099 | 98.691726 | -0.328373 | 0.834441 |
| putnam_1995_a3 | 95.204557 | 95.281826 | +0.077269 | 0.882331 |
