# 07 library search

Stage: `results/07_library_search`.

Ask deterministic Lean search tactics for explicit proof suggestions.

**9 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **43.754%**. Gain over the preceding stage: **+0.861 pp**; gain over the measured original control: **+10.425 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 9.421 | 9.402 | -0.018 |
| Heartbeat reduction | 19.258 | 21.860 | +2.602 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 42.893 | 43.754 | +0.861 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 14, "accepted_transitions": 14, "analysis_requests": 162, "attempts": 172, "cache_hits": 198, "elapsed_seconds": 1972.737, "lean_candidate_checks": 9, "rounds": 81, "wall_seconds": 399.244}`. Null counters were not recorded by that runner.

Budget stops: **10**. Stop reasons: `{"no_improving_proposal": 3, "no_new_proposals": 2, "round_limit": 10}`.

Primary-only screened trial events: 152. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 35, "incomplete": 70, "invalid": 8, "passed": 59}`. Decision outcomes: `{"fully_scored_improvement": 20, "invalid_candidate": 8, "primary_bound_pruned": 109, "primary_failed": 33, "primary_timeout": 2}`.

Discovery statuses: `{"ok": 81}`. Tactic outcomes: `{"failed": 175, "heartbeat_limit": 747, "not_observed": 15, "rejected_sorry": 136, "solved": 300, "unavailable": 116, "unsolved": 56}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `Core.InitsUpdatesComm` | 229 → 228 | +6.082 | no_improving_proposal |
| `putnam_1964_b2` | 542 → 469 | +3.698 | round_limit |
| `CallElimCorrect.extractedOldExprInVars` | 222 → 234 | +1.594 | round_limit |
| `fundamental_theorem_of_variational_calculus'` | 834 → 832 | +0.745 | round_limit |
| `putnam_1964_a4` | 1351 → 1338 | +0.326 | round_limit |
| `Cslib.SKI.parallelReduction_diamond` | 407 → 408 | +0.188 | no_improving_proposal |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | 1311 → 1306 | +0.121 | round_limit |
| `CallElimCorrect.substOldPostSubset` | 303 → 305 | +0.095 | round_limit |
| `putnam_1995_a3` | 3104 → 3103 | +0.068 | round_limit |

## Accepted example

`Core.InitsUpdatesComm` — trial 1 in [trials_b1f6d85dc1f90d1f.jsonl](trials_b1f6d85dc1f90d1f.jsonl). This accepted **single edit** changes the complete candidate's combined score from 42.247% to 46.461% (**+4.214 pp**).

Before (enclosing indentation removed):

```lean
simp [isDefined] at *
```

After:

```lean
exact UpdateStatesDefined Hups
```

## Interpretation

- Local score proxy; not an arena submission result.
- Means average per-problem reductions; ratios of total tokens or heartbeats differ.
- Finite candidate, round, and site budgets do not establish a global optimum.
- A primary-screened trial need not have a combined score; selected outputs are reported separately.
- Elapsed seconds sum per-problem time, including caches and overlapping workers; this is not wall time.
- Wall seconds sum recorded runner-session durations, excluding gaps between resumes; incomplete timing data remain null.
- Candidate-check and cache counters exclude discovery/compiler-probe work; older stages may not record them.
- Tactic outcomes describe discovery attempts, not complete-proof validity; unavailable or unobserved tactics are not proof failures.
- Trial and error counts count log events or diagnostics, which can include repeated discovery after an accepted edit or resume.
- Sequential gains are conditional on earlier accepted stages and are not independent ablations.

Evidence: [configuration](config.json), [runner summary](summary.json), [computed report](report.json), [selected proofs](candidates.jsonl), and the per-problem `problem_*.json` / `trials_*.jsonl` records.
