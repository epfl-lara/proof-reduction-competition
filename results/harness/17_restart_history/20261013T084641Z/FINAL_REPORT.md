# Completed step-4 restart-history experiment

Step 4 finished at **2026-10-13 14:50:31 CEST**, after 4.003 hours. Both conditions completed all 15 theorems, retained proofs passing all 36 required version checks, and passed independent saved-evidence audit confirmations. Scores are local fixed-reference measurements, not organizer scores.

| Condition | Combined | Length reduction | Heartbeat reduction | Compatibility |
|---|---:|---:|---:|---:|
| Revised 1–3 control | 89.448630% | 80.092250% | 88.253641% | 100% |
| Revised 1–3 + step 4 | 89.904622% | 81.010171% | 88.703694% | 100% |
| Difference | **+0.455991 pp** | +0.917921 pp | +0.450053 pp | 0 pp |

History improved 10 theorems and regressed 5; none tied. The largest gain was Fsub.Typing.progress (+5.457503 points); the largest loss was SKI.parallelReduction_diamond (-2.530273 points). The Fsub gain accounts for about 80% of the net aggregate improvement, so aggregate improvement alone should not hide variation across problems.

The historical reference is 89.357422%: step 4 is +0.547200 points higher. The recovered fresh baseline is 89.265062%: step 4 is +0.639560 points higher. That baseline required two manually cooled continuations and gained 0.006844 cohort points from repeated deterministic cleanup; those qualifications do not apply to the direct step-4 versus revised comparison.

## Controls and recovery

The saved matched preflight confirms the same 15 original/D0 input seeds, gpt-6.1-sol/max, five workers, $3 per-problem best-effort target, no wall-time watchdog, 20 optimization and two transport restarts, canonical prompt/cards, feedback, tool instructions, references and proof-selection rule. Configuration differences are only the history version, its supporting code hashes and the separate deterministic-job location. No prior condition's optimized proofs seeded step 4. Frozen runtime hashes still match.

Step 4 required no manual recovery or budget carryover. Its 151 native attempts comprise 95 received responses, 54 controlled budget stops and two terminal transport errors handled within configured recovery. The control used 173 attempts (111 received, 61 controlled budget stops and one terminal transport error). All 15 cells in each condition ended at their cumulative cost limit. Final cleanup mean gain was 0.028114 points for history and 0.026168 for control; no repeat-recovery cleanup was needed in either direct comparison arm.

## Usage and history

| Quantity | Revised control | Step 4 |
|---|---:|---:|
| Cumulative API-equivalent estimate | $45.075914 | $45.133420 |
| Reported-counter cost subtotal | $45.075914 | $45.133420 |
| Estimated unreported subtotal | $0 (assumption) | $0 (assumption) |
| Problems with incomplete usage | 7 | 10 |
| Calls with unknown usage | 10 | 14 |
| Native attempts | 173 | 151 |
| Reported completion tokens | 1128029 | 1198214 |

Missing usage remains unknown. Zero heuristic amounts for some unreported requests are not observed zero charges. These are estimated API-equivalent costs, not invoices or certified hard caps. Native response boundaries can overshoot the $3 target. The runs do not establish a model-dollar saving.

History saved **149 model notes across 15 theorems** and **1625 source observations**. 130 requests received prior notes, 136 received prior checked trials, and 136 received prior source observations. The largest history payload was 11992 characters, below the 12,000-character bound. Audits reconstructed summaries from earlier same-condition host records and verified event provenance. Notes remain unverified hypotheses; they never replace all-version proof checks.

## Interpretation and completion

This is a promising improvement on one exploratory warm-up cohort. It does not isolate which history component caused the gain, establish repeatability, or demonstrate held-out generalization. Keep history opt-in pending a separately authorized replication; no default behavior was changed and no additional model experiment was launched.

Implementation validation before launch: 586 offline tests and 102 subtests passed, with formatting/lint checks passed. The completed audit was independently rerun for both arms without new Lean measurements or model requests. Exact artifact hashes, costs, utilization and component deltas are in [FINAL_COMPARISON.json](FINAL_COMPARISON.json). Runtime pins and protocol remain unchanged. The workflow is complete. The host monitor timer is stopped and disabled; its service is inactive.

## Per-theorem combined scores

| Theorem | Revised control | Step 4 | Difference (pp) |
|---|---:|---:|---:|
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | 84.747311 | 87.253584 | +2.506273 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | 92.232290 | 93.899948 | +1.667658 |
| CallElimCorrect.extractedOldExprInVars | 93.976339 | 93.522023 | -0.454316 |
| CallElimCorrect.substOldPostSubset | 89.441932 | 89.956694 | +0.514761 |
| Core.InitsUpdatesComm | 87.255312 | 88.646371 | +1.391059 |
| Cslib.CCS.bisimilarity_congr_choice | 85.386156 | 85.600696 | +0.214540 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | 83.629230 | 89.086733 | +5.457503 |
| Cslib.SKI.parallelReduction_diamond | 79.366871 | 76.836598 | -2.530273 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | 86.239878 | 86.625139 | +0.385261 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | 84.233103 | 82.512170 | -1.720932 |
| fundamental_theorem_of_variational_calculus' | 91.273849 | 90.384449 | -0.889400 |
| interleaved_affine_gaps_imply_tensor_gaps | 91.410862 | 91.949618 | +0.538756 |
| putnam_1964_a4 | 96.996944 | 96.626502 | -0.370442 |
| putnam_1964_b2 | 99.102526 | 99.157164 | +0.054638 |
| putnam_1995_a3 | 96.436853 | 96.511637 | +0.074785 |
