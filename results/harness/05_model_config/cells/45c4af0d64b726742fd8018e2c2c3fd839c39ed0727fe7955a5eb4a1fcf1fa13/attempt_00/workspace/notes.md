# Local trials
- Initial shortening (attempt1.lean, 211 proof tokens): failed; generic recursive simp_rw descended twice and unconstrained sampling rewrite failed. Need specialize to the input stack and affine predicate.
- Repair in candidate: specialize multilinear recursion and sampling predicate; use explicit interleaveWordStack to disambiguate transpose notation; base threshold uses ENNReal.coe_one.

- Repair 2 (attempt2.lean, 254 tokens): failed. Recursion replacement creates a term invalid at instances transparency for rewrite; base n=0+1 not normalized for simp. New trial uses positive-index Nat.le_induction and Fin.snoc_init_self in the sampling lemma.

- Positive-induction/snocs version (attempt3.lean, 292 tokens): first failure is underconstrained scalar type in sampling predicate. Current candidate pins F in sampling lemma.
- Trial 5 (valid1.lean): all versions pass. Positive-index induction; snoc split normalized via reverse Fin.init_def and snoc_init_self; explicit local multilinear snoc identity. 300 tokens, 3474.933 primary heartbeats; score 80.025948.
- Trial 6 (valid2.lean): derive the sampling equality directly for the affine-split predicate, fold it back with reverse recursion. Eliminates local snoc identity. All versions valid; 241 tokens, 2914.151 heartbeats; score 83.510154.
- Trial 7 (attempt7.lean, 192 tokens): failed. Generic singleton-sampling simp does not match the affine predicate. Successor's omitted pair arguments caused no reported errors.
- Trial 8 (attempt8.lean, 216 tokens): positive induction with combined base simpa and inferred interleaved pair arguments passes v4.30/v4.29 but primary fails comparing direct ENNReal natural casts with NNReal coerced casts. Added ENNReal.coe_natCast explicitly for trial 9.
- Trial 9 (valid3.lean): explicit coe_natCast repairs primary. Single base simpa, no successor pair let; all versions valid. 218 tokens, 2783.587 heartbeats; score 84.549581.
- Trial 10 (valid4.lean): positional code arguments and hs ▸ hp instead of a tactic rewrite. All versions valid; 192 tokens, 2776.993 heartbeats; score 85.214010.
- Trial 11 (valid5.lean): pin F in base multilinear/singleton lemmas and inverse recursive lemma. All versions valid; 207 tokens, 2652.161 heartbeats; score 85.296490. Small improvement over unpinned applications.
- Trial 12 (attempt12.lean): equality transport in base and term-level trans_le probability composition is valid but worse: 216 tokens, 3034.687 heartbeats, score 83.689597. Restore tactic composition for subsequent trials.
- Trial 13 (attempt13.lean): use ih directly on filter membership instead of the R-star helper. Valid but slightly worse: 205 tokens, 2696.692 heartbeats, score 85.184512. Retain helper.
- Trial 14 (attempt14.lean): direct rewrite of the R-star premise instead of deriving/folding a sampling equality. v4.30/v4.29 valid; primary's simpa needs explicit ENNReal.coe_mul for the threshold.
- Trial 15 (attempt15.lean): coe_mul/coe_natCast repairs direct R-star premise proof. All versions valid; 209 tokens, 2650.202 heartbeats, score 85.254310, slightly below saved best.
- Trial 16 (attempt16.lean): omit classical; all versions valid, 206 tokens, 2650.865 heartbeats, score 85.325819. Tool did not replace saved best (status remains trial 11).
- Trial 17: retain F annotation only on singleton sampling, omit unused classical. All versions valid; 196 tokens, 2694.184 heartbeats; accepted score 85.415323.
- Stopping locally: main structural blocks eliminated; term composition, direct filter induction, and direct R-star premise rewrites did not improve the saved score. Remaining hint-level changes are unlikely to justify further trials.
