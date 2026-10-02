# Repeated deterministic sweeps

The initial portfolio finished at **44.711685%** combined score, with all 36
version checks passing. Both repeat sweeps are complete at **46.248122%**, a
further **1.536438 pp** gain, with **36/36 version checks passing**. The runner
stopped at its declared `sweep_limit`; the second sweep still improved proofs.

| Sweep | Marginal gain (pp) | Final score (%) | Candidate trials | Accepted transitions | Summed stage wall seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | +1.400308 | 46.111992 | 1,594 | 48 | 3,179.801 |
| 2 | +0.136130 | 46.248122 | 1,540 | 12 | 2,437.465 |

## Sweep 1

| Stage | Marginal gain (pp) | Changed proofs | Candidate trials | Recorded wall seconds |
| --- | ---: | ---: | ---: | ---: |
| [Return wrappers](sweep_01/01_wrappers/) | 0.000000 | 0 | 0 | 0.905 |
| [Local fact deletion](sweep_01/02_facts/) | +0.601938 | 6 | 309 | 604.607 |
| [Fact reuse](sweep_01/03_reuse/) | +0.032061 | 1 | 2 | 32.115 |
| [Fixed tactic menu](sweep_01/04_menu/) | +0.435727 | 9 | 528 | 725.421 |
| [Library search](sweep_01/05_search/) | +0.180232 | 2 | 192 | 736.092 |
| [Simplifier-list minimization](sweep_01/06_simp_min/) | +0.054153 | 2 | 310 | 497.763 |
| [Arithmetic-hint minimization](sweep_01/07_arith_min/) | 0.000000 | 0 | 0 | 0.938 |
| [Rewrite-list minimization](sweep_01/08_rw_min/) | +0.009227 | 1 | 174 | 402.412 |
| [Linter deletion](sweep_01/09_lint/) | +0.045283 | 4 | 7 | 44.284 |
| [Explicit simplification](sweep_01/10_simp/) | +0.041687 | 3 | 72 | 135.264 |

The local-fact stage selected 16 further deletions across six proofs, including
deleting an intermediate cardinality fact from `putnam_1964_b2` after intervening
proof changes. Its complete-candidate gain was +1.116012 pp. Fact reuse removed
two remaining aliases in `putnam_1995_a3`. The wrapper pass found no new proposals.
The repeated menu selected 16 changes across nine proofs. One accepted change
replaced `simp_all [Set.ext_iff]` with `simp_all` inside `putnam_1964_b2`, gaining
2.326096 pp for that complete candidate. Its stage-level gain was smaller than
the first menu pass (+0.435727 versus +3.042029 pp), with a similar number of
candidate trials (528 versus 539). Different worker counts and cache reuse make
their raw wall times unsuitable as a controlled speed comparison.

The repeated library search selected three transitions across two Putnam proofs,
using 192 candidate trials. It gained 0.180232 pp while increasing average proof
length slightly; the heartbeat saving justified the tradeoff. Its largest
accepted change replaced `linarith` with `exact id (Eq.symm h₅)` inside
`putnam_1964_a4`, gaining 2.301556 pp for the complete candidate. Eight proofs
still ended at the round cap.

Repeated simplifier-list minimization selected three deletions across two proofs
from 310 trials. In the Wick-algebra theorem, reducing
`[ofListBasis_eq_ofList, map_mul, pb]` to `[ofListBasis_eq_ofList]` gained
0.604525 pp on the complete candidate. The arithmetic pass found no new lists
to minimize after the first pass had already removed its sole eligible list.

The final cleanup stages expose interactions between methods. Rewrite-list
minimization removes a redundant `Nat.add_zero` rewrite in the ArkLib fold proof
(+0.138402 pp for that candidate). Linter deletion then removes an empty
`rw [] at hx` left by an earlier accepted rewrite-list edit in the variational
calculus proof (+0.217022 pp). These are gains conditional on the evolving proof,
not separate independent ablations.

## Sweep 2

| Stage | Marginal gain (pp) | Changed proofs | Candidate trials | Recorded wall seconds |
| --- | ---: | ---: | ---: | ---: |
| [Return wrappers](sweep_02/01_wrappers/) | +0.005071 | 1 | 1 | 16.545 |
| [Local fact deletion](sweep_02/02_facts/) | 0.000000 | 0 | 216 | 249.770 |
| [Fact reuse](sweep_02/03_reuse/) | 0.000000 | 0 | 0 | 0.813 |
| [Fixed tactic menu](sweep_02/04_menu/) | +0.112688 | 6 | 589 | 656.147 |
| [Library search](sweep_02/05_search/) | +0.008466 | 1 | 186 | 569.910 |
| [Simplifier-list minimization](sweep_02/06_simp_min/) | +0.009905 | 2 | 326 | 512.705 |
| [Arithmetic-hint minimization](sweep_02/07_arith_min/) | 0.000000 | 0 | 0 | 0.863 |
| [Rewrite-list minimization](sweep_02/08_rw_min/) | 0.000000 | 0 | 150 | 305.327 |
| [Linter deletion](sweep_02/09_lint/) | 0.000000 | 0 | 4 | 4.633 |
| [Explicit simplification](sweep_02/10_simp/) | 0.000000 | 0 | 68 | 120.752 |

Sweep 2 selected one new wrapper contraction in `putnam_1964_a4`:
`have h₃ := h_eq.1; exact h₃` becomes `exact h_eq.1`, gaining 0.076067 pp for the
complete candidate and 0.005071 pp over the benchmark. The wrapper pass had no
proposals in sweep 1; later edits created another contraction opportunity.

The menu selected eight transitions across six proofs, including
`linarith` → `omega` in `putnam_1995_a3` (+0.535399 pp for that whole candidate).
Search selected one change in `putnam_1964_a4`, replacing a local `by omega`
with `by exact rfl` (+0.126997 pp). Simplifier-list cleanup selected two deletions,
including removal of `Bool.decide_and` in the Wick-algebra theorem (+0.091798 pp).
All other second-sweep families gained zero at their configured budgets.

The two sweeps together use 3,134 candidate trials, 2,946 uncached candidate-version
checks, 888 analysis/probe requests and 392 candidate-cache hits. There are 60
selected full-candidate transitions. Summing changed-proof counts across stages
gives 28 in sweep 1 and ten in sweep 2; these are repeated stage/problem pairs,
not 38 distinct benchmark problems. The full portfolio's separate discovery and
repair costs are in [FINDINGS.md](../FINDINGS.md#work-accounting).

## Bounds and interpretation

Each configured sweep applies return-wrapper contraction, local fact deletion,
fact reuse, the fixed tactic menu, materialized library search, simplifier-list
minimization, arithmetic-hint minimization, rewrite-list minimization, linter
deletion and explicit simplification in that order. Each stage starts from the
preceding stage's selected proofs and retains the same cached original reference
denominators. A changed proof gets fresh syntax analysis.

The configured limits are six rounds and 64 candidates per problem, six discovery
sites per batch, and a 0.05 pp minimum per-candidate combined-score improvement.
The runner permits at most two sweeps and can stop early if a complete sweep
selects no changed proofs. It reached the two-sweep limit here. Across the 150
stage/problem pairs per sweep, 23 in sweep 1 and 20 in sweep 2 stopped at a round
or candidate cap. This is neither a globally minimal proof result nor exhaustive
discovery.

Each fresh stage starts its discovery cursor at zero. At the end of sweep 2's
search stage, the ArkLib fold proof has covered 36/133 syntax sites and
`putnam_1995_a3` 36/108; both proof hashes survive final cleanup. Their next
recorded cursors are 36. The fiberwise proof covers 36/115 at that search stage
but changes during later simplifier cleanup. Some selected runtime probes also
remain unobserved. A zero-gain sweep would therefore not establish exhaustion
of this tactic family.

Exact same-proof, same-site replay across the two sweeps accounts for 16 menu
batches and 11 search batches, all cache hits. Those repeats spend bounded rounds
without repeating Lean discovery work. The observed search repeats concern
already fully covered proofs; they do not show that the long-proof gaps were
caused by repeated fresh compilation. The next isolated experiment should
continue unvisited windows on unchanged incumbents, preserving the existing
budgets and all-version scoring gate.

The initial tactic-menu stage used the discovery implementation archived during
the library-search repair. Repeated menus use the corrected selector and inline
probe insertion. Their gains therefore combine revisiting edited proofs with
additional search budget and, where relevant, corrected discovery coverage.
The evaluator and original reference fingerprints remain unchanged.

The [portfolio manifest](../portfolio.json) records both completed sweeps and
`sweep_limit`. Individual stage reports link every representative snippet to its
accepted candidate trial; improvements discovered but not selected are excluded.
