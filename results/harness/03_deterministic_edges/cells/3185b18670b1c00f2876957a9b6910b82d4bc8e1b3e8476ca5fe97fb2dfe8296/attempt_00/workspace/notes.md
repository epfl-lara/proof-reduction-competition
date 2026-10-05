- Attempt 1 (524 tokens): replace counting by Finset.card_le_card_of_surjOn on bad fibers × Fin(2^steps); nat arithmetic then distFromCode_le_dist_to_mem. Failed: q bound needs positivity of rate, subtype g needs .val for application, pointToIterateQuotientIndex arguments must be named.

- Attempt 2 (535 tokens): repaired q bound and explicit subtype/index. Only remaining error: Set.toFinset_card yields Fintype.card rather than ncard.

- Attempt 3 (536 tokens): ncard conversion fixed 3 versions, primary needs explicit unfolding of hammingDist/D/Y in final simpa.

- Attempt 4: valid all versions; 542 tokens, 7078.914 heartbeats, score 72.57536. Surjective counting eliminates exact fiber counts and disjointness; direct codeword bound avoids ENat.toNat.

- Attempt 5: valid all versions; 422 tokens, 5938.062 heartbeats, score 77.73908. Scale the nat premise and rewrite in-place, deleting the separate algebraic identity and final calc.

- Attempt 6: valid all versions; 400 tokens, 4129.542 heartbeats, score 82.09184. Existing index-bound lemmas, explicit zero witness for nonempty image, and Nat.sub_add_comm replace all body omega calls.

- Attempt 7: valid all versions; 329 tokens, 3559.272 heartbeats, score 84.92400. Infer the nat upper bound and let the reconstruction theorem determine the surjection witnesses.

- Attempt 8: valid all versions; 318 tokens, 3604.724 heartbeats, score 85.07783. Factor disagreement-set function; leave counting as the final natural-number goal.

- Attempt 9 (278 tokens): backwards cardinal rewrites failed because the ncard expression retained a beta redex from the minimum witness.

- Attempt 10: valid all versions; 276 tokens, 4860.290 heartbeats, score 83.36085 (regressive). Backwards cardinal rewrites cost more than typed surjection + simp. Retain attempt 8.

- Attempt 11: valid all versions; 293 tokens, 4396.485 heartbeats, score 83.96126 (regressive). Merged scaled nat bound using dsimp plus uncurry does not beat explicit change.

- Attempt 12: 316 tokens, 3098.949 primary heartbeats; passes 4.31/4.30 only. Set.fintypeCard_eq_ncard is unavailable in 4.29/4.28. Repair via Nat.card_eq_fintype_card and Nat.card_coe_set_eq.

- Attempt 13: valid all four versions; 319 tokens, 3105.968 heartbeats, score 86.11722. Shared cardinal function and direct Fintype-to-Nat.card simplification improve elaboration, with old-version-compatible lemmas.
- Stopping: core counting and arithmetic have been factored; shorter backwards rewrites/unfolding regressed, and further generic counting helpers would add substantial setup without eliminating another argument block.
