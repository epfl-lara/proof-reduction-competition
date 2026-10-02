# Stage 01: unused and unreachable tactic deletion

**Four of 15 proofs improved; combined score increased by 0.328 percentage points.**
All 36 theorem/version checks still pass. This pass principally saves tokens;
its heartbeat effect is negligible.

| Full warm-up mean | Unchanged control | After deletion | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 0.000% | 0.978% | +0.978 |
| Heartbeat reduction | -0.011% | -0.006% | +0.006 |
| Compatibility | 100.000% | 100.000% | 0.000 |
| Combined | 33.330% | 33.658% | **+0.328** |

These are means of per-problem percentages over **all 15 rows**. The tiny nonzero
heartbeat control is the difference between the unchanged candidate check and the
separately cached reference measurement. It is not meaningful proof optimization.

## What changed

| Problem | Original tokens | Selected tokens | Deleted spans | Combined gain (pp) |
| --- | ---: | ---: | ---: | ---: |
| `putnam_1964_a4` | 1,769 | 1,665 | 24 | +1.966 |
| `putnam_1964_b2` | 1,754 | 1,623 | 21 | +2.487 |
| `putnam_1995_a3` | 4,085 | 4,042 | 16 | +0.374 |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | 1,463 | 1,459 | 1 | +0.092 |

Total: **62 spans and 282 tokens removed**. A typical removal drops an unused
`<;> (try ...)` tail after the preceding tactic has already finished the work.
The other 11 proofs produced no applicable deletion proposals under this method.
That does not establish that those proofs contain no removable material: this
stage depends on the linters imported and enabled by the original context.

## Method and evidence

Lean parses the declaration and elaborates it normally to provide syntax ranges
and linter diagnostics. The proposer selects `unusedTactic` and `unreachableTactic`
spans, lifts through appropriate unary wrappers, and removes adjacent combinators.
The resulting entire declaration is checked with the separate measurement API.
Edits are accepted only if the fully evaluated combined score increases by more
than 0.05 pp; an unchanged proof is the fallback.

The budget was three rounds and 32 candidate trials per problem, with two problem
workers. Four joint candidates were tried and accepted; no individual fallback
search was needed. After one accepted deletion pass, a new analysis found no
further applicable spans. The recorded per-problem elapsed times sum to 104.204 s;
they include cache reuse from development pilots and are **not a cold-run timing**.

- [config.json](config.json): exact budgets, input, context and implementation hashes.
- [summary.json](summary.json): full-precision aggregates and coverage.
- [candidates.jsonl](candidates.jsonl): one complete declaration for every problem.
- `problem_*.json`: initial/final component scores, individual version results and stop reason.
- `trials_*.jsonl`: exact proposed code, edit ranges, evaluation outcomes and selections.

A preliminary instrumentation run exposed the newer Lean module-mode requirement
for a `meta` observer helper. It was superseded before these results; the failure
audit is in [stage 00](../00_reference_baseline/instrumentation_probe.json).

**Decision:** retain this cheap cleanup pass. Test explicit simplifier lemma sets
next, because deleting unused work alone did not materially reduce heartbeats.
