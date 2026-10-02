# Deterministic optimization findings

The completed portfolio raises the local combined score from the unchanged
measured control's **33.329562%** to **46.248122%**, a **12.918560 pp** gain.
Final mean length reduction is **12.187241%**, heartbeat reduction **26.557125%**,
and compatibility **100%**. The eight new first-pass methods reach **44.711685%**,
adding **7.612024 pp** over stage 02's 37.099661%; two full repeat sweeps add a
further **1.536438 pp**. The run ends at its declared two-sweep limit, with
remaining unvisited discovery sites.

All selected proofs pass all **36 required version checks** for the 15 warm-up
problems. These are local measurements against the cached original heartbeat
denominators, not results from the private arena worker. Benchmark metrics
average per-problem reductions; they are not ratios of summed token or heartbeat
counts.

Acceptance uses the mean of length reduction, heartbeat reduction and version
compatibility, with a minimum 0.05 pp complete-candidate gain. Passing proofs can
therefore grow if their heartbeat savings improve the combined objective. The
heartbeat component uses each problem's first listed Lean version; every listed
version contributes to compatibility. The original control's heartbeat reduction
is −0.011314% rather than exactly zero; these runs do not estimate a
repeated-measurement noise interval, so the smallest
individual gains should not be interpreted as precision guarantees.

| Completed stage | Marginal gain (pp) | Changed proofs | Candidate trials | Recorded stage wall time (s) |
| --- | ---: | ---: | ---: | ---: |
| [01 Linter deletion](01_linter_deletion/) | +0.327984 | 4 | 4 | Not recorded |
| [02 Explicit simplification](02_explicit_simp/) | +3.442115 | 8 | 99 | Not recorded |
| [03 Return wrappers](03_wrappers/) | +0.747806 | 5 | 14 | 170.309 |
| [04 Local fact deletion](04_local_facts/) | +1.730512 | 7 | 195 | 605.930 |
| [05 Fact reuse](05_fact_reuse/) | +0.272893 | 3 | 11 | 98.934 |
| [06 Fixed tactic menu](06_tactic_menu/) | +3.042029 | 13 | 539 | 1,521.792 |
| [07 Library search, repaired retry](07_library_search/) | +0.861233 | 9 | 172 | 399.244 |
| [08 Simplifier-list minimization](08_simp_minimization/) | +0.396038 | 10 | 462 | 845.963 |
| [09 Arithmetic-hint minimization](09_arithmetic_minimization/) | +0.465390 | 1 | 1 | 9.904 |
| [10 Rewrite-list minimization](10_rewrite_minimization/) | +0.096123 | 5 | 212 | 512.257 |

The [repeat-sweep report](11_repeated_sweeps/) gives each method's later gains and
accepted examples. Sweep 1 adds **1.400308 pp** using 1,594 candidates; sweep 2
adds **0.136130 pp** using 1,540. Menu gains decline from 3.042029 pp initially
to 0.435727 and 0.112688 pp. Library-search gains decline from 0.861233 to
0.180232 and 0.008466 pp. This is diminishing return under the tested order and
budgets, not an independent comparison of methods or proof-search exhaustion.

## Work accounting

The continuation comprises stages **03–10 plus both ten-stage sweeps**. It adds
**9.148461 pp** over stage 02 through **195 accepted full-candidate transitions**
(234 individual edits).

| Work scope | Candidate trials | Uncached candidate-version checks | Analysis/probe requests | Candidate cache hits | Summed stage wall seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| New first pass, 03–10 | 1,606 | 1,770 | 494 | 457 | 4,164.333 |
| Repeat sweep 1 | 1,594 | 1,619 | 460 | 171 | 3,179.801 |
| Repeat sweep 2 | 1,540 | 1,327 | 428 | 221 | 2,437.465 |
| **Continuation total** | **4,740** | **4,716** | **1,382** | **849** | **9,781.599** |
| Archived failed stage-07 attempt, separate | 165 | 178 | 160 | 22 | 751.780 |
| Early-arithmetic branch, separate | 1 | 1 | 16 | 1 | 4.165 |

The continuation's menu/search discovery logs contain **405 uncached probe
batches** and **50 cached batches**, with **7,810.495 summed fresh compiler-process
seconds**. Their 32,186 logged tactic outcomes include cached replay and are not
32,186 fresh compiler runs or independent goals. AST analysis and explicit
simplification are additional work represented in the request counter; the
menu/search timing subtotal does not cover them.

The failed stage-07 attempt separately adds 80 fresh probe batches and 1,966.577
summed discovery-process seconds. Its repaired retry in the main chain uses
candidate caches, performing only nine uncached candidate-version checks.
The repair preflight adds 12 batches over 64 sites and **249.941 summed
compiler-process seconds**; no preflight wall total was recorded. The early
arithmetic branch overlaps the main run, so its 4.165 seconds must not simply be
added to elapsed wall time. Worker counts changed from four to eight for later
main stages. Session durations exclude gaps between resumes, while process times
overlap across workers; these are observed costs, not cold-cache speed comparisons.

## What the completed stages establish

- Return-wrapper contraction removed 768 tokens (17,917 → 17,149) using only 14
  candidates. It recovered the extra proof length introduced by explicit
  simplification while retaining its heartbeat savings. No row hit a search cap.
- Local fact deletion produced useful gains, but 166 of 195 candidates failed
  on the primary version. Source-level nonreference is only a proposal signal:
  automation can still depend on a local fact without naming it explicitly.
- Alias contraction/fact reuse was cheap on this benchmark: all 11 tried
  candidates improved their incumbents. This is a result for the identified
  patterns, not a claim that arbitrary local lemma sharing is beneficial.
- The fixed menu improved 13 of 15 problems. Only 32 of its 166 improving
  alternatives became selected transitions; treating every improving trial as
  an accepted edit would overstate the result.
- Library search was primarily a heartbeat optimization: its average length
  reduction worsened by 0.018434 pp while heartbeat reduction improved by
  2.602134 pp. The combined score correctly retained that tradeoff.
- Simplifier-list minimization added 0.396038 pp, but 415 of its 462 candidates
  failed on the primary version. Its 26 selected deletions prove that the
  post-stage-07 proofs contain removable simplifier arguments. Intervening
  accepted edits changed their surrounding contexts, so this result does not
  establish that stage 02's `simp?` sets were nonminimal in their original
  contexts. Rechecking argument lists after other edits can still add value.
- Arithmetic-hint removal was the cheapest new win. Removing all six hints from
  a `nlinarith [...]` call in `fundamental_theorem_of_variational_calculus'`
  produced `nlinarith []` and gained **6.980846 pp** on that complete proof,
  or **0.465390 pp** over the benchmark. This was the only eligible arithmetic
  hint list at this stage, so its success rate does not establish generality.
- Rewrite-list minimization added 0.096123 pp across five proofs. It used 212
  candidates: eight improved, 196 failed on the primary version, two timed out,
  four were rejected by candidate validation, and two were pruned by score.
  This is useful measured cleanup, with a relatively high search cost here.

Two concrete full-candidate examples illustrate the distinction between proof
length and the actual objective. In `Core.InitsUpdatesComm`, replacing a selected
`simp_all` with `norm_cast` gained **4.026892 pp**; replacing another selected
`simp [isDefined] at *` with `exact UpdateStatesDefined Hups` later gained
**4.214152 pp**. Both replacements were produced by deterministic Lean discovery,
then measured and verified as complete declarations on all listed versions.
The stage reports identify the exact accepted trials and before/after fragments.

## Coverage and interpretation

At the final stage, [`11_repeated_sweeps/sweep_02/10_simp`](11_repeated_sweeps/sweep_02/10_simp/),
within-source gains over the original control are PutnamBench **38.513130 pp**,
PhysLean **10.403476 pp**, Strata **8.415937 pp**, ArkLib **6.963491 pp**, and CSLib
**0.296767 pp**. Each source contributes three problems; Putnam therefore supplies
approximately **59.6%** of the final overall gain.
The benchmark is small, and these gains should not be presented as a general
ranking of mathematical domains.

The initial local-fact pass stopped at its round cap on four problems; alias
contraction did so on one. Initial menu/search passes hit round/trial caps on
12/10 problems, respectively. Sweep 2 still caps 10 menu runs and seven search
runs. In [sweep 2's search stage](11_repeated_sweeps/sweep_02/05_search/), the final
incumbent of ArkLib's fold theorem has only **36/133** selected syntax sites,
its fiberwise theorem **36/115**, and `putnam_1995_a3` **36/108**. Each saved cursor
is 36. Fold and `putnam_1995_a3` retain those proof hashes through the final stage;
the fiberwise proof changes during subsequent simplifier-list cleanup, so its
36/115 count belongs specifically to the search-stage snapshot. Some selected
probes can also remain unobserved at runtime.

Fresh stages start the discovery cursor at zero. Comparing sweep 1 with sweep 2
on identical proof hashes, offsets and site tuples finds 16/73 duplicated menu
batches and 11/73 duplicated search batches. All were discovery-cache hits:
they used bounded rounds without repeating Lean discovery work. The observed
search duplicates occur in already fully covered proofs, so they do not show
that the large-proof gaps above were caused by repeated Lean execution. Those
unvisited tails support testing cursor continuation before another fresh sweep.
A no-improvement sweep cannot establish exhaustion even of all
sites in the implemented discovery family.

Discovery heartbeat caps and missing tactic syntax are separate outcomes.
At the fixed 5,000-heartbeat search limit, sweep 2's search stage reaches that
cap in **692/1,377** logged tactic outcomes: 249/303 for ArkLib, 195/297 for
PhysLean and 238/360 for Putnam. Every one of ArkLib's 101 `exact?` outcomes
records a heartbeat cap. Strata records 91 unavailable `aesop?` outcomes because
that tactic was absent from the proof contexts. These counts include revisits
and cached discovery results, not independent goals or failed complete proofs.

The first library-search attempt's instrumentation failed on two PhysLean
declarations. The repaired selector excludes conversion tactics and patterns,
and probe insertion now respects changed columns for inline proof terms. The
[repair record](failed_attempts/07_library_search_v1/REPAIR.md) preserves the old
implementation snapshot and explains the 12-batch, 64-site preflight. The scoring
backend and cached reference fingerprints were unchanged; the full stage was
rerun from stage 06 rather than silently continuing from partially searched data.
Stage 06 also used the archived discovery implementation. Repeated tactic-menu
passes use the repaired implementation, so subsequent gains can reflect corrected
discovery coverage as well as new proof contexts and additional search budget.

These stages belong in the shared harness for both competition tracks. They
produce verified candidate proofs and feedback without requiring either model
to learn tool syntax. No model training or model calls are part of this portfolio.
The emerging loop is to apply inexpensive structural/hint cleanup, spend a
bounded budget on tactic discovery, then revisit cleanup on changed proofs.
Sweep 1 demonstrates a concrete dependency: rewrite-list minimization leaves
`rw [] at hx`, which linter deletion subsequently removes. This motivates
tracking which proofs changed, while retaining candidate and evaluation caches;
the complete reordered schedule has not yet been tested.

## Next isolated experiment

Prioritize **coverage continuation on unchanged proofs**. Start from the final
selected candidates and, for the fixed tactic menu, evaluate the first unvisited
six-site window on each eligible incumbent. Preserve the existing 5,000-heartbeat
per-tactic discovery limit, 0.05 pp acceptance margin, cached reference values and
all-version checks. Carry unchanged proofs for the other rows so the result still
has the full 15-problem denominator. Report newly covered sites, full-candidate
trials, marginal score and actual tool cost. Keep the discovery cursor keyed by
proof hash and implementation/environment identity; accepted edits require new
syntax and a new cursor. Do not increase heartbeat limits in the same experiment.

This tests a specific coverage gap before adding another solver family or model.
If capped retrieval remains the limiting factor after coverage improves, a later
matched `exact?` experiment can raise only the discovery heartbeat limit on the
already identified capped ArkLib sites.

## Separate early-arithmetic probe

The [early arithmetic branch](12_early_arithmetic_probe/) starts directly from
stage 03, before local-fact deletion, tactic-menu search and library search.
With the same method and candidate budget, it improved **37.847467% → 38.314458%**
(**+0.466991 pp**) using one candidate. All **36 version checks** pass. Removing
the same six `nlinarith` hints gains **7.004870 pp** on the complete variational
calculus proof in this earlier context. The branch records 16 syntax analyses,
one uncached candidate check and 4.165 wall seconds; it overlaps the main run
and uses two workers, so this is not a controlled speed comparison.

This demonstrates that the cheap arithmetic win was already available after
wrapper contraction. Only one eligible hint list was present. It supports
scheduling arithmetic-hint minimization early, but does not measure a full
reordered pipeline: the branch was not fed through the subsequent methods, and
its gain must not be added to the main cumulative score. A later ordering test
can keep the remaining methods' relative order and budgets fixed, then compare
the actual final score and candidate/discovery work.
