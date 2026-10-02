# 05 search

Stage: `results/deterministic/11_repeated_sweeps/sweep_01/05_search`.

Ask deterministic Lean search tactics for explicit proof suggestions.

**2 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **45.962%**. Gain over the preceding stage: **+0.180 pp**; gain over the measured original control: **+12.632 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 11.915 | 11.888 | -0.026 |
| Heartbeat reduction | 25.430 | 25.997 | +0.567 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 45.781 | 45.962 | +0.180 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 3, "accepted_transitions": 3, "analysis_requests": 146, "attempts": 192, "cache_hits": 21, "elapsed_seconds": 3290.61, "lean_candidate_checks": 169, "rounds": 73, "wall_seconds": 736.092}`. Null counters were not recorded by that runner.

Budget stops: **8**. Stop reasons: `{"no_improving_proposal": 5, "no_new_proposals": 2, "round_limit": 8}`.

Primary-only screened trial events: 188. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 32, "incomplete": 88, "invalid": 12, "passed": 60}`. Decision outcomes: `{"fully_scored_improvement": 4, "invalid_candidate": 12, "primary_bound_pruned": 144, "primary_failed": 29, "primary_timeout": 3}`.

Discovery statuses: `{"ok": 73}`. Tactic outcomes: `{"failed": 145, "heartbeat_limit": 711, "not_observed": 9, "rejected_sorry": 101, "solved": 300, "unavailable": 91, "unsolved": 53}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `putnam_1964_a4` | 1211 → 1216 | +2.302 | round_limit |
| `putnam_1964_b2` | 353 → 355 | +0.402 | round_limit |

## Accepted example

`putnam_1964_a4` — trial 8 in [trials_9db3d07c62677e1b.jsonl](trials_9db3d07c62677e1b.jsonl). This accepted **single edit** changes the complete candidate's combined score from 70.313% to 72.615% (**+2.302 pp**).

Before (enclosing indentation removed):

```lean
linarith
```

After:

```lean
exact id (Eq.symm h₅)
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
