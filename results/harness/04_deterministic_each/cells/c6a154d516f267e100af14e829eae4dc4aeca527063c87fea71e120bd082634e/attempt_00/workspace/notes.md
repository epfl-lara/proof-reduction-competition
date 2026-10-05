## Tried
- Seed: 348 tokens, 22891.684 heartbeats, 87.054294 score.
- Replaced complement bijection/counting with `Set.Intersecting.is_max_iff_card_eq` and explicit maximality from hPS. Both versions passed: 90 tokens, 835.284 heartbeats, score 98.058569. Deterministic cleanup pending.

## Source facts
- Mathlib/Combinatorics/SetFamily/Intersecting.lean: `Intersecting.is_max_iff_card_eq` gives `2 * #s = Fintype.card α` from maximality; signatures unchanged between pinned versions.
- `Disjoint.inter_eq` and `Set.disjoint_iff_inter_eq_empty` convert the given intersection condition.
- `Nat.mul_left_cancel Nat.two_pos` cancels 2, `pow_succ'` and `Nat.sub_add_cancel Fintype.card_pos` close exponent arithmetic.
- Alternative exponent lemma: `Nat.pow_pred_mul` has `x ^ (w-1) * x = x ^ w` under `0 < w`.
- Tool search returned no hits; read pinned dependency sources via shell.
- Deterministic cleanup of 90-token proof unchanged.
- Goal-first application of maximal-family lemma, converting hPP in place: first attempt failed because `simp only [← disjoint_iff_inter_eq_empty]` does not unfold `Ne`. Adding `ne_eq` repaired it. No `classical` needed. Both versions pass: 67 tokens, 625.711 heartbeats, 98.553637 score. Cleanup pending.
- Next promising simplification: convert hPS as well as hPP to disjointness, avoiding the conversion inside the witness; optionally direct proof terms for antisymmetry.
- 67-token deterministic cleanup unchanged.
- Focused grind for maximality failed with only Intersecting: Finset subset and coercion membership stayed opaque. Repaired with Finset.subset_iff and Finset.mem_coe, after converting both hypotheses: 49 tokens, 1267.939 heartbeats, 98.718060 score; deterministic unchanged.
- Combined cardinality lemma into the arithmetic rewrite and let grind handle extensionality directly: 39 tokens, 1296.350 heartbeats, 98.900243 score. Both versions passed; cleanup pending.
- Remaining candidate ideas: rely on normal grind database for subset/coercion facts (fewer tokens); focused aesop after normalization; term proof cannot currently beat the 39-token automatic version.
- 39-token deterministic cleanup unchanged.
- Default grind with only the Intersecting definition supplied was both shorter and faster than grind only with subset/coercion lemmas: 34 tokens, 1135.630 heartbeats, 99.039722 score. Cleanup pending.
- Potential last refinement: rewrite by the negated disjointness equivalence directly (Iff.not) to avoid ne_eq. Nat-specific power rewriting may also reduce typeclass elaboration.
- Negated disjointness equivalence works directly. Nat.pow_succ' produced syntactic `succ` and then the existing subtraction rewrite failed; reverting to generic pow_succ' fixed it.
- Direct `.not` rewrite: 32 tokens, 1191.408 heartbeats, 99.062301 score; both versions pass but tool did not replace saved best (reported delta +0.022579). Deterministic unchanged.
- Right-cancellation and Nat.pow_pred_mul: 32 tokens, 1178.312 heartbeats, 99.065924; tool again retained earlier best; cleanup pending.
- Found a stronger arithmetic lemma in Algebra/Group/Basic.lean: `mul_pow_sub_one (hn : n ≠ 0) (a : M)` rewrites `a * a^(n-1)` directly. Fintype.card_ne_zero supplies its condition. This can replace the two previous arithmetic rewrites.
- Using `mul_pow_sub_one Fintype.card_ne_zero` and direct disjointness rewriting throughout reduced the proof to 28 tokens: 1195.965 heartbeats, 99.137058 score, accepted as best on both versions. Deterministic cleanup pending.
- Local stopping rationale: main combinatorial argument now comes entirely from the maximal intersecting-family cardinality lemma; remaining arithmetic is a single power identity and cancellation. Explicit maximality terms were longer; focused grind was slower than default grind. Further small tactic spelling changes have low expected benefit.
