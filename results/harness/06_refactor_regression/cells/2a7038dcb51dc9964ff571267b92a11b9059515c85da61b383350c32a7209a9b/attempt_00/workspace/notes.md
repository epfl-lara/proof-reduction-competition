# Attempts
1. Replaced norm/Cauchy–Schwarz neighborhood with continuity of scalar inner product; direct bump and continuous nonnegative nonzero integral lemma. Valid: tokens 227, heartbeats 2012.286, score 85.4962914.
2. Removed redundant bump instance; `lt_of_le_of_ne'` instead of symmetry. Valid: 217 tokens, 2017.042 heartbeats, score 85.8747231.
3. Focused `funext`, combined final contradiction and integral identity with `simpa only`. Valid: 209 tokens, 2087.159 heartbeats, score 85.9925256.
4. Removed repeated type annotations from `hc`, `hp`, and integral positivity (explicit μ). Failed: scalar of `Continuous.inner'` underdetermined.
5. Added explicit ℝ scalar for `hc`. Failed: final `simpa only` did not unfold pointwise multiplication in the inferred integral type.
6. Added `Pi.mul_apply` to final simplification. Valid: 176 tokens, 2002.667 heartbeats, score 87.5207683.
7. Switched bump to `exists_contDiff_tsupport_subset`. Failed parsing explicit `∞` (scope not open here).
8. Used `⊤` for smoothness order. Failed: nonzero proof needed to fix the point and unfold pointwise multiplication.
9. Existence lemma with explicit term for nonzero at x. Valid: 174 tokens, 1844.910 heartbeats, score 88.0390873.
10. Case split directly on φ y = 0 instead of support membership. Valid: 173 tokens, 1808.429 heartbeats, score 88.1800014.
11. Inlined nonnegativity in integral lemma. Failed: rewrite needed `Pi.mul_apply` on the inferred product function.
12. Added `Pi.mul_apply` to zero branch. Failed: remaining goal was `0 y ≤ 0`.
13. Added zero-function evaluation rewrite too. Valid: 159 tokens, 1806.363 heartbeats, score 88.7341379.
14. Focused `simp only` zero branch, range witness constructor and `Eq.trans_ne`. Valid but regressive: 162 tokens, 1786.779 heartbeats, score 88.6712483.
15. Let ordinary `simp [hy]` discharge only the zero branch. Valid: 153 tokens, 1797.844 heartbeats, score 88.9929148.
16. Tried `real_inner_self_pos` in `WithLp 2 V` directly; failed because nonzero hypotheses require conversion, adding overhead. Retained the best approach.
17. Constructed smul test function fields directly. Valid but regressive: 150 tokens, 2469.786 heartbeats, score 87.2363965. The `IsTestFunction.smul_right` abstraction is substantially faster.
18. Explicit integral congruence and transitivity instead of final simplification. Valid but regressive: 176 tokens, 1816.133 heartbeats, score 88.0410064.
Stopping locally: scalar continuity, smooth bump existence, and integral positivity remove the substantive overhead; additional explicit constructions and final congruence were worse.
