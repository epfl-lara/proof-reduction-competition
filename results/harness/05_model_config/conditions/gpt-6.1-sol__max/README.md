# Sol 6.1/max warm-up submission

Prepared and checked 2026-10-05 02:29 CEST.

Upload **[selected_candidates.jsonl](selected_candidates.jsonl)** in the [arena Submit tab](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena), selecting **Closed-source LLM**. This is the exact 15-proof export from the completed Sol condition. Use the existing team username/key as appropriate.

The [submission manifest](submission_manifest.json) records the file hash, each source result, all required Lean versions, local component scores, token costs and intake checks. Preparation does not upload or replace a leaderboard entry.

Local combined score: **87.342215%**; length reduction **76.399921%**; heartbeat reduction **85.626723%**; compatibility **100.0%**.

All 36/36 saved problem/version checks pass. The full 30-cell study audit passed; the JSONL matches the selected Sol proofs exactly. Reference measurements were reused, and the live organizer benchmark is byte-identical to the local 15-problem warm-up. These scores are local; the organizer heartbeat baselines can produce different scores.

Estimated API-equivalent cost: **$14.814649 total**, **$0.987643 mean/problem**, **$1.672598 maximum**; **0/15 over $3** at the recorded rates. Counts include reasoning and all attempts. Estimates assume Standard service and short context per request with reported caching; they are not Codex invoices or certified replay costs.

Size: 22,597 bytes. SHA-256: `8656476e52874b1e11a1ebe0c02c9b1b6a202c10a441bb63d8c6806336e63697`.

| Problem | Local combined % | Passing versions | Estimated USD |
| --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | 86.211956 | 1/1 | 1.070565 |
| CallElimCorrect.extractedOldExprInVars | 88.770979 | 1/1 | 0.773350 |
| Core.InitsUpdatesComm | 85.208307 | 3/3 | 0.375426 |
| fundamental_theorem_of_variational_calculus' | 88.775856 | 1/1 | 0.878194 |
| Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema | 85.187085 | 1/1 | 1.187567 |
| FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time | 80.701365 | 1/1 | 1.536155 |
| Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress | 82.316632 | 3/3 | 1.193186 |
| Cslib.SKI.parallelReduction_diamond | 74.286927 | 4/4 | 0.700847 |
| Cslib.CCS.bisimilarity_congr_choice | 85.723860 | 3/3 | 0.899796 |
| Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius | 86.818503 | 4/4 | 1.672598 |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | 91.613119 | 3/3 | 0.816474 |
| interleaved_affine_gaps_imply_tensor_gaps | 85.415323 | 3/3 | 1.086929 |
| putnam_1964_a4 | 94.878654 | 3/3 | 0.936657 |
| putnam_1964_b2 | 99.020099 | 2/2 | 0.743792 |
| putnam_1995_a3 | 95.204557 | 3/3 | 0.943114 |

Method and price sources: [study protocol](../../PROTOCOL.md). Runtime and prompts remain frozen; preparation changes no proofs and launches no new experiments.
