# Proof-theoretic deterministic rewrites: status report

Branch `feat/analysis`, 14 October 2026. Warm-up set (15 problems).

## Summary

- We added a Lean-free analysis of proof structure and six deterministic
  rewrite methods that shorten proofs, for use by the existing engine. All are
  opt-in; the default cleanup portfolio is unchanged.
- On the original benchmark proofs, the proof-theoretic and tokenizer rewrites
  shorten 13 of 15 proofs, from 17,595 to 16,924 tokens, a projected **+0.94
  combined points**. On the LLM's starting proofs the projection is **+0.43**,
  and on final, already optimized proofs **+0.10**.
- These projections assume each rewrite compiles on every required Lean version
  with unchanged heartbeats. The next step is to test them further on the Lean
  machine, where the engine keeps only rewrites that pass and improve the score.
- The harness also gained an opt-in final rewrite pass and a tree search with
  zero-cost policy replay, ready for a first run.

## What was implemented

### Proof analysis (`optimization/proof_theory/`)

Reads a proof's source and reports, in proof-theory terms: local lemmas and how
often each is used (cuts), introduce-then-eliminate steps (detours), runs of
steps that fuse into one, repeated subproofs found by anti-unification (up to
renaming, mirror-image names or substitution), and heavy automation in large
contexts. On the warm-up originals it located the structures the best LLM
proofs later removed, for example a 776-token lemma proved twice in
`putnam_1995_a3`.

### Rewrite methods

Registered in `optimization/proof_theory/methods.py`; each also runs alone as
`proof-transform --method NAME`.

| Method | Shortens by |
| --- | --- |
| `proof_theory` | inlining single-use lemmas (cut elimination), fusing `exists`/`constructor`/`refine` + closing steps into one term, folding destructuring into `rintro`, merging identical branches, removing detours (`by exact t` → `t`) |
| `golf` | tokenizer-aware edits: `tac₁; tac₂` on separate lines, final `f a (g x)` → `f a $ g x`, redundant parentheses |
| `collapse` | turning a split (`induction`, `cases`, `constructor`, …) and its branches into `split <;> closer` |
| `delete` | removing a redundant step, a `<;>` tail or a `try` wrapper |
| `consolidate` | merging consecutive `rw` / `simp only` lists at the same location |
| `relax` | dropping the lemma list of `simp only [...]`, `norm_num [...]`, `simpa only [...]` (trades tokens for heartbeats) |

Inlining writes the lemma's proof at its single use, without parentheses where
the position is already delimited. It is skipped only inside `simp`/`rw` lemma
lists, where the lemma's statement is what the tactic uses.

Safety: proposals that fail the arena's declaration checks are dropped before
they reach the engine, and the engine compiles and scores every candidate. The
flag `proof-transform --require-all-versions` keeps only candidates that pass
every required Lean version.

### Harness additions (opt-in)

| Feature | Flag | Status |
| --- | --- | --- |
| Final rewrite pass: all six methods on the best proof after final cleanup, gated on every version | `--final-rewrites` | ready for testing |
| Tree search: short agent calls from a chosen proof with one strategy card; decisions recorded for replay | `--tree-expansions N` | ready for a first run |
| Policy replay (after Dream-RSI): score alternative tree policies on recorded runs at no cost | `proof-harness dream` | ready |
| Restarted sessions from the best proof | `--restart-sessions N` | superseded by `main`'s budget restarts; drop when merging |

## Projected shortening

`proof_theory` alone, then followed by `golf`:

| Proofs | Methods | Shortened | Tokens | Combined |
| --- | --- | ---: | --- | ---: |
| Original benchmark proofs | proof_theory | 10/15 | 17,595 → 17,051 | +0.69 |
| Original benchmark proofs | + golf | 13/15 | 17,595 → 16,924 | +0.94 |
| LLM starting proofs (after cleanup) | proof_theory | 9/15 | 13,815 → 13,640 | +0.20 |
| LLM starting proofs (after cleanup) | + golf | 12/15 | 13,815 → 13,530 | +0.43 |
| Final Sol proofs (audited run) | + golf | 12/15 | 2,852 → 2,799 | +0.10 |

`delete`, `collapse` and `relax` add further candidates whose effect depends on
testing: some remove whole case analyses (for example 313 → 10 tokens on
`substOldPostSubset` if `induction post <;> simp [substOld] <;> simp_all`
holds).

For an external 15-proof submission, a review of all candidates rated 62 very
likely to pass, 11 plausible and 239 long shots; the likely ones project to
about +0.11 combined points on top of an already short proof set.

Related findings from saved runs:

- Deterministic cleanup gains 22–54 points on machine-written Putnam proofs and
  0–4 on concise library proofs, where the LLM gains come from restructuring.
- No policy over existing models (cascades, repeats, stopping rules) beats a
  single Sol 6.1/max session at about $1 per problem; two identical Sol runs
  differ by 0.77 points, which bounds what one run can detect.

## Validation and testing plan

- 377 offline tests pass (`make test`); lint and format are clean. Reviewing
  candidates led to two parser fixes with regression tests: a multi-line
  statement after a bullet is now one step, and `match` alternatives are no
  longer collapsed into invalid syntax.
- Further testing on the Lean machine (no API cost) measures which rewrites
  pass and what they gain:

```bash
in=results/deterministic/selected_candidates.jsonl
for m in delete collapse consolidate proof_theory relax golf; do
  proof-transform --method $m --input $in --require-all-versions \
    --output results/deterministic/14_$m --workers 8
  in=results/deterministic/14_$m/candidates.jsonl
done
```

## Next steps

- Run the chain above, then a tree-search run at about $1 per problem followed
  by `proof-harness dream`.
- Merge with `main` (14 commits ahead): the optimization code merges cleanly;
  the harness hooks need re-applying on `main`'s new `search.py`, and the tree
  search should become budget-admitted attempts there.
- The proof tree is recovered from indentation, so unusual layouts can yield
  candidates Lean rejects; these cost a compile, never a wrong result. `$` is
  core Lean syntax, though Mathlib's style linter may warn about it.
