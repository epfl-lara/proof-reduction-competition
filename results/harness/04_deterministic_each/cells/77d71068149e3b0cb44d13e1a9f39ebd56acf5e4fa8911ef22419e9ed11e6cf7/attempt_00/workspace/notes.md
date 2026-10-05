Seed: score 39.8992 (L 13.5362, H 6.1613, C 100).
Argument: split evaluation polynomial into even/odd refinements, quotient sends each fiber to y, two fibers differ by 1, then bilinear interpolation and linearity of coefficient sum.
Proposal 1: retain theorem's lets via intro; use qMap_total_fiber_one_level_eq + get_sDomain_first_basis_eq_1 instead of basis sum/casts; shared quotient and split identities; explicit witness for generates_quotient_point_if_is_fiber_of_y; one ring calculation and termwise sum linearity. Awaiting check.
Proposal 1 failed only final sum: Polynomial.eval_sum is for polynomial coefficient sums, not Finset.sum. Replaced with Polynomial.eval_finset_sum (legacy alias needed for v4.29).
Proposal 2 valid all versions: 342 tokens, 8114.348 HB, score 88.044579 (L=82.0567 H=82.0771). Running deterministic cleanup.
Deterministic 2: all valid, score 88.449518, 356 tokens, 7231.813 HB. Replaced broad simp with specific simp-only and removed Nat.sub_add_eq.
Proposal 3: single simp for fiber difference; use i.isLt for i+1≤ℓ; simplify fold and split directly instead of hs and change; final sum by distributivity/associativity simp alone.
Proposal 3 failed: simp did not unfold local x in hq; last sum equality was only definitionally reflexive. Repair 4: dsimp x at hq/hd; expand P₀/P₁ for ring; final rfl. All versions valid: 251 tokens, 6361.061 HB, score 90.926928. Cleanup running.
Deterministic 4 made no improvement.
Proposal 5 generalized polynomial evaluation atoms and fiber coordinate before ring: all valid but regressive, 269 tokens/6443.181 HB, score 90.551671. Scalar abstraction is not helping this ring calculation. Cleanup requested as required.
Deterministic 5 unchanged.
Proposal 6: infer quotient evaluation equality from explicit congrArg of transitivity of fiber-generation theorem and one-step quotient identity. Valid all versions, 237 tokens, 6169.224 HB, score 91.313012. Cleanup running.
Deterministic 6 unchanged, best 91.313012.
Proposal 7 attempted replacing simplified hq by explicit rw instances and eliminating dsimp; invalid due to unreduced subtype projection/local x in rewrite pattern.
Repair 8 restored dsimp and used explicit rw instances: valid all versions but regressive, 241 tokens, 6308.861 HB, score 91.140248. Cleanup requested. The generalized simp hq of proposal 6 is better than these explicit rewrites. Plan to retain best after final cleanup; remaining local tweaks unlikely to justify further attempts.
Deterministic 8 unchanged. Final status selects proposal 6: score 91.313012, 237 tokens, 6169.224 HB, all 3 versions valid. Stopping after explicit quotient proof improvement and two regressive alternatives; retained exact saved best declaration.
