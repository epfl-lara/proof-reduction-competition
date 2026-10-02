# 05 search

Stage: `results/11_repeated_sweeps/sweep_02/05_search`.

Ask deterministic Lean search tactics for explicit proof suggestions.

**1 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **46.238%**. Gain over the preceding stage: **+0.008 pp**; gain over the measured original control: **+12.909 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 12.171 | 12.167 | -0.004 |
| Heartbeat reduction | 26.518 | 26.547 | +0.029 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 46.230 | 46.238 | +0.008 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 1, "accepted_transitions": 1, "analysis_requests": 146, "attempts": 186, "cache_hits": 28, "elapsed_seconds": 3162.484, "lean_candidate_checks": 155, "rounds": 73, "wall_seconds": 569.91}`. Null counters were not recorded by that runner.

Budget stops: **7**. Stop reasons: `{"no_improving_proposal": 6, "no_new_proposals": 2, "round_limit": 7}`.

Primary-only screened trial events: 183. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 26, "incomplete": 88, "invalid": 12, "passed": 60}`. Decision outcomes: `{"fully_scored_improvement": 3, "invalid_candidate": 12, "primary_bound_pruned": 145, "primary_failed": 25, "primary_timeout": 1}`.

Discovery statuses: `{"ok": 73}`. Tactic outcomes: `{"failed": 136, "heartbeat_limit": 692, "not_observed": 6, "rejected_sorry": 101, "solved": 298, "unavailable": 91, "unsolved": 53}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `putnam_1964_a4` | 1192 → 1193 | +0.127 | round_limit |

## Accepted example

`putnam_1964_a4` — trial 14 in [trials_9db3d07c62677e1b.jsonl](trials_9db3d07c62677e1b.jsonl). This accepted **single edit** changes the complete candidate's combined score from 73.192% to 73.319% (**+0.127 pp**).

Before (enclosing indentation removed):

```lean
                                               by
omega
```

After:

```lean
by exact rfl
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
