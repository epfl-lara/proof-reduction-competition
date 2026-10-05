1. Sliding quadruple state + finite interval pigeonhole (420 tokens): failed because lambda membership expected type and index subtraction normalization.
2. Membership tactic and add_sub_cancel (433 tokens): membership repaired; rewrite cannot reduce a+4-3 to a+1.
3. norm_num only add_sub_assoc normalizes subtraction, but leaves a+0, failed.
4. Added add_zero, all versions valid, 435 tokens, 4285.79 heartbeats, S=90.79083. Saved tuple435.lean.
5. Tuple bounds inferred indices and Nat.exists_eq_add final; default simp recurrence normalization: valid 377 tokens, 6754.434 heartbeats, S=91.30055.
6. Focused norm_num restored: valid 380 tokens, 3643.804 heartbeats, S=91.97886, saved tuple380.lean.
7. Fin4 function state: 316 tokens, failed because rewriting congrFun h numeric Fin arguments does not unfold.
8. Bounded natural-index helper H fixes rewriting: valid 364 tokens, 3510.316 heartbeats, S=92.31188. Saved pi364.lean.
9. Combined normalization and H rewriting via norm_num: valid 334 tokens, 3433.23 heartbeats, S=92.89538. Saved pi334.lean.
10. Inline state induction removes step helper: valid 296 tokens, 3698.825 heartbeats, S=93.54867. Saved pi296.lean.
11. Direct casting/rewrite last branch: valid 310 tokens, 3541.923 heartbeats, S=93.32194 (regressive).
12. Fin.forall_iff simplifies induction hypothesis directly: valid 267 tokens, 3672.986 heartbeats, S=94.10123. Saved pi267.lean.
13. Explicit addition/subtraction final rewrite and recurrence bounds: valid 262 tokens, 3121.783 heartbeats, S=94.32565. Saved pi262.lean.
14. forall_and membership and sub_pos_of_lt period: valid 257 tokens, 3038.918 heartbeats, S=94.43944. Saved pi257.lean.
15. Targeted simp reductions instead of norm_num: valid 263 tokens, 2338.159 heartbeats, S=94.49193. Saved pi263.lean.
16. Nat.rec proof term and inferred n; dropped k type failed membership (249 tokens).
17. Restored k type: valid 252 tokens, 2285.319 heartbeats, S=94.71168. Saved pi252.lean.
18. Explicit nested Fin.cases: valid 269 tokens, 2138.81 heartbeats, S=94.42596 (regressive).
19. Encode values in bounded integer subtype, universe finite automatically: valid 244 tokens, 2216.637 heartbeats, S=94.87865. Saved subtype244.lean.
20. Use finite range and mem_range_self rather than universe: valid 244 tokens, 2238.012 heartbeats, S=94.87360 (slightly regressive).
21. Universe membership via trivial lambda: failed because dot application leaves target set unspecified while elaborating membership proof.
Stopping locally: bounded subtype + finite-state induction is compact; range/nested eliminator alternatives regress, and further small membership shortening failed. Best all-version proof: 244 tokens, 2216.637 heartbeats, S=94.87865.
