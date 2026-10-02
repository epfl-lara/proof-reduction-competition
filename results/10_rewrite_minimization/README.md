# 10 rewrite minimization

Stage: `results/10_rewrite_minimization`.

Remove rewrite-list entries while preserving the order of retained rewrites.

**5 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **44.712%**. Gain over the preceding stage: **+0.096 pp**; gain over the measured original control: **+11.382 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 10.171 | 10.243 | +0.073 |
| Heartbeat reduction | 23.676 | 23.892 | +0.216 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 44.616 | 44.712 | +0.096 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 8, "accepted_transitions": 8, "analysis_requests": 23, "attempts": 212, "cache_hits": 8, "elapsed_seconds": 1548.389, "lean_candidate_checks": 222, "rounds": 23, "wall_seconds": 512.257}`. Null counters were not recorded by that runner.

Budget stops: **1**. Stop reasons: `{"no_improving_proposal": 10, "no_new_proposals": 4, "trial_limit": 1}`.

Primary-only screened trial events: 204. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 198, "incomplete": 2, "invalid": 4, "passed": 8}`. Decision outcomes: `{"fully_scored_improvement": 8, "invalid_candidate": 4, "primary_bound_pruned": 2, "primary_failed": 196, "primary_timeout": 2}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | 1745 → 1734 | +0.537 | trial_limit |
| `fundamental_theorem_of_variational_calculus'` | 817 → 816 | +0.470 | no_improving_proposal |
| `putnam_1964_a4` | 1293 → 1291 | +0.196 | no_improving_proposal |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | 1368 → 1366 | +0.122 | no_improving_proposal |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | 1370 → 1368 | +0.117 | no_improving_proposal |

## Accepted example

`fundamental_theorem_of_variational_calculus'` — trial 4 in [trials_26b11637cbbc0cf7.jsonl](trials_26b11637cbbc0cf7.jsonl). This accepted **single edit** changes the complete candidate's combined score from 42.545% to 43.015% (**+0.470 pp**).

Before (enclosing indentation removed):

```lean
[Metric.mem_closedBall]
```

After:

```lean
[]
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
