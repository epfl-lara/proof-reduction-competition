Optimization notes:
- Factored four repeated sorted-list Wick elements into local names; this improved score over the seed.
- Replaced broad list simplification with `simp only` using the needed list/Bool lemmas; this reduced heartbeats.
- Aliased the supercommutator and used it in the span predicates; `dsimp [c]` at the two required computation points improved combined score to 45.1103.
- Tested partial-relation/list aliases, untyped span predicate binders, and other rewrites; they were invalid or scored lower. Selected proof is all-version valid for v4.32.0.
