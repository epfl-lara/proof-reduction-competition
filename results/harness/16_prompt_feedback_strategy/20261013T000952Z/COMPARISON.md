# Completed changes 1–3 comparison

Both cohorts completed all 15 theorems, retained proofs passing every required version, and passed their saved-evidence audits. These are local scores.

| Condition | Combined | Length reduction | Heartbeat reduction | Compatibility |
|---|---:|---:|---:|---:|
| Revised 1–3 | 89.448630% | 80.092250% | 88.253641% | 100% |
| Baseline, recovered | 89.265062% | 80.708014% | 87.087172% | 100% |

The revised arm wins by **0.183568 percentage points**, and exceeds the historical 89.357422% reference by **0.091208 points**. The authorized gate therefore selects revised for the separate step-4 restart-history experiment. Start that experiment from the same original/D0 seeds, with the same model, effort, cohort, tools, $3 per-theorem target and 20+2 restart limits; do not seed from either arm's optimized results.

The baseline needed two manual cooldown continuations after confirmed terminal capacity failures. Every earlier attempt and cumulative cost was preserved, with at most 23 total admissions per funded theorem. This qualifies the comparison: it is not a pristine matched completion. Repeated final deterministic cleanup in recovery_01 added 0.102654 points to one theorem (FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time), or 0.006844 points to the cohort mean; recovery_02 added no final-cleanup gains.

API-equivalent cumulative totals are $45.075914 for revised and $45.1045224 for recovered baseline. Reported usage is incomplete in 7 and 10 problems respectively. Zero estimates for some unreported failed requests are assumptions, not known zero charges. These totals do not establish complete usage, an invoice, or a hard cap.

This is one exploratory 15-theorem warm-up replicate; it does not isolate which of changes 1–3 helped or demonstrate held-out generalization.

Exact report/audit hashes, metrics and gate are in [comparison_decision.json](comparison_decision.json). The historical failed run artifacts remain unchanged.

| Theorem | Revised minus recovered baseline (pp) |
|---|---:|
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | -0.223066 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | -1.623562 |
| CallElimCorrect.extractedOldExprInVars | +1.818610 |
| CallElimCorrect.substOldPostSubset | -0.023726 |
| Core.InitsUpdatesComm | +0.469533 |
| Cslib.CCS.bisimilarity_congr_choice | -0.604482 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | -6.757414 |
| Cslib.SKI.parallelReduction_diamond | +3.871902 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | +0.232991 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | +4.026023 |
| fundamental_theorem_of_variational_calculus' | +0.712494 |
| interleaved_affine_gaps_imply_tensor_gaps | -0.072039 |
| putnam_1964_a4 | +0.427760 |
| putnam_1964_b2 | -0.015363 |
| putnam_1995_a3 | +0.513868 |
