# 09 arithmetic minimization

Stage: `results/deterministic/09_arithmetic_minimization`.

Remove chunks and individual arithmetic hints while preserving tactic controls.

**1 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **44.616%**. Gain over the preceding stage: **+0.465 pp**; gain over the measured original control: **+11.286 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 10.069 | 10.171 | +0.102 |
| Heartbeat reduction | 22.382 | 23.676 | +1.294 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 44.150 | 44.616 | +0.465 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 1, "accepted_transitions": 1, "analysis_requests": 16, "attempts": 1, "cache_hits": 1, "elapsed_seconds": 22.198999999999998, "lean_candidate_checks": 1, "rounds": 16, "wall_seconds": 9.904}`. Null counters were not recorded by that runner.

Budget stops: **0**. Stop reasons: `{"no_new_proposals": 15}`.

Primary-only screened trial events: 0. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"passed": 1}`. Decision outcomes: `{"fully_scored_improvement": 1}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `fundamental_theorem_of_variational_calculus'` | 830 → 817 | +6.981 | no_new_proposals |

## Accepted example

`fundamental_theorem_of_variational_calculus'` — trial 1 in [trials_26b11637cbbc0cf7.jsonl](trials_26b11637cbbc0cf7.jsonl). This accepted **single edit** changes the complete candidate's combined score from 35.564% to 42.545% (**+6.981 pp**).

Before (enclosing indentation removed):

```lean
        [inner_eq_self_add_diff, hcs, hself, hclose, hxp,
mul_lt_mul_of_pos_right hclose hxp]
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
