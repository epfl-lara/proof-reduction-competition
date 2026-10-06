# Sol 6.1/max fresh-attempt comparison

Status: validated. 15/15 terminal; 15 complete. The full mean requires all outcomes and a passed audit.

Primary baseline: 86.951351% local combined, 15/15 complete; $16.037530 estimated total. Matched seeds, inputs, scoring, references and cleanup: True.

New local combined: 89.357422% (+2.406071 percentage points).

Mean raw gain after the first attempt: 2.364716 percentage points.

Attempts: 57; fresh restarts: 42. Wins/ties/losses among complete outcomes: 14/0/1.

Cost: 4 problems with known total, 11 with unknown total; known subtotal $10.233819. Native limits check between responses; this is not a certified invoice cap.

| Problem | Status | Attempts | First raw | All raw | Restart gain pp | Final | Baseline change pp | Cost USD | Stop |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| CallElimCorrect.substOldPostSubset | complete | 3 | 87.079055 | 90.625224 | 3.546169 | 90.625224 | 4.480727 | 2.478429 | time_limit |
| CallElimCorrect.extractedOldExprInVars | complete | 5 | 91.137786 | 94.190829 | 3.053043 | 94.190829 | 6.754293 | 2.765382 | time_limit |
| Core.InitsUpdatesComm | complete | 6 | 85.571069 | 87.515606 | 1.944537 | 87.515606 | 1.756317 | unknown | time_limit |
| fundamental_theorem_of_variational_calculus' | complete | 3 | 90.033377 | 90.970541 | 0.937164 | 90.970541 | 0.470360 | unknown | cost_limit |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | complete | 4 | 84.378112 | 85.886909 | 1.508797 | 85.886909 | 1.180416 | unknown | time_limit |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | complete | 3 | 80.367416 | 81.402488 | 1.035073 | 81.402488 | 0.540230 | unknown | time_limit |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | complete | 3 | 81.681344 | 85.205857 | 3.524513 | 85.205857 | 2.951737 | 2.584648 | time_limit |
| Cslib.SKI.parallelReduction_diamond | complete | 4 | 71.131656 | 75.077129 | 3.945473 | 75.077129 | -0.237867 | 2.405360 | time_limit |
| Cslib.CCS.bisimilarity_congr_choice | complete | 4 | 85.174571 | 86.934466 | 1.759895 | 86.934466 | 1.776300 | unknown | time_limit |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | complete | 3 | 79.323736 | 85.251222 | 5.927486 | 85.251222 | 9.897288 | unknown | time_limit |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | complete | 3 | 90.008563 | 93.407634 | 3.399071 | 93.407634 | 2.085102 | unknown | cost_limit |
| interleaved_affine_gaps_imply_tensor_gaps | complete | 4 | 89.811619 | 91.345737 | 1.534119 | 91.345737 | 1.958719 | unknown | time_limit |
| putnam_1964_a4 | complete | 4 | 95.384830 | 97.219136 | 1.834306 | 97.219136 | 1.478331 | unknown | time_limit |
| putnam_1964_b2 | complete | 4 | 98.757893 | 99.217583 | 0.459690 | 99.217583 | 0.212639 | unknown | time_limit |
| putnam_1995_a3 | complete | 4 | 95.049558 | 96.110969 | 1.061412 | 96.110969 | 0.786475 | unknown | cost_limit |

Within-run restart gain compares verified raw scores after attempt 0 versus all attempts, before final cleanup. Baseline differences also include CLI version, wall deadline, budget feedback and native guard. No causal reset-only estimate or organizer score is claimed.

Evidence: [report](report.json), [comparison data](comparison.json), [protocol](PROTOCOL.md), [completion status](completion.json).
