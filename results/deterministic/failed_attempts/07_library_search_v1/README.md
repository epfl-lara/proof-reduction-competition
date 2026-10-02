# 07 library search v1

Stage: `results/deterministic/failed_attempts/07_library_search_v1`.

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

Recorded totals: `{"accepted_edits": 14, "accepted_transitions": 14, "analysis_requests": 160, "attempts": 165, "cache_hits": 22, "elapsed_seconds": 3418.849, "lean_candidate_checks": 178, "rounds": 80, "wall_seconds": 751.78}`. Null counters were not recorded by that runner.

Budget stops: **8**. Stop reasons: `{"discovery_unavailable": 2, "no_improving_proposal": 3, "no_new_proposals": 2, "round_limit": 8}`.

Primary-only screened trial events: 145. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 35, "incomplete": 70, "invalid": 8, "passed": 52}`. Decision outcomes: `{"fully_scored_improvement": 20, "invalid_candidate": 8, "primary_bound_pruned": 102, "primary_failed": 33, "primary_timeout": 2}`.

Discovery statuses: `{"discovery_failed": 2, "ok": 78}`. Tactic outcomes: `{"failed": 175, "heartbeat_limit": 724, "not_observed": 36, "rejected_sorry": 131, "solved": 290, "unavailable": 116, "unsolved": 55}`. Proposal/analysis error events and diagnostics: **9** (`{"diagnostic:discovery_error": 9}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `Core.InitsUpdatesComm` | 229 → 228 | +6.082 | no_improving_proposal |
| `putnam_1964_b2` | 542 → 469 | +3.698 | round_limit |
| `CallElimCorrect.extractedOldExprInVars` | 222 → 234 | +1.594 | round_limit |
| `fundamental_theorem_of_variational_calculus'` | 834 → 832 | +0.745 | round_limit |
| `putnam_1964_a4` | 1351 → 1338 | +0.326 | round_limit |
| `Cslib.SKI.parallelReduction_diamond` | 407 → 408 | +0.188 | no_improving_proposal |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | 1311 → 1306 | +0.121 | discovery_unavailable |
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
