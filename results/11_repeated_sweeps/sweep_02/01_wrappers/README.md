# 01 wrappers

Stage: `results/11_repeated_sweeps/sweep_02/01_wrappers`.

Contract local return wrappers using parsed syntax spans.

**1 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **46.117%**. Gain over the preceding stage: **+0.005 pp**; gain over the measured original control: **+12.788 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 12.079 | 12.094 | +0.015 |
| Heartbeat reduction | 26.257 | 26.257 | +0.000 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 46.112 | 46.117 | +0.005 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 1, "accepted_transitions": 1, "analysis_requests": 16, "attempts": 1, "cache_hits": 1, "elapsed_seconds": 20.992, "lean_candidate_checks": 3, "rounds": 16, "wall_seconds": 16.545}`. Null counters were not recorded by that runner.

Budget stops: **0**. Stop reasons: `{"no_new_proposals": 15}`.

Primary-only screened trial events: 0. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"passed": 1}`. Decision outcomes: `{"fully_scored_improvement": 1}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `putnam_1964_a4` | 1200 → 1196 | +0.076 | no_new_proposals |

## Accepted example

`putnam_1964_a4` — trial 1 in [trials_9db3d07c62677e1b.jsonl](trials_9db3d07c62677e1b.jsonl). This accepted **single edit** changes the complete candidate's combined score from 72.917% to 72.993% (**+0.076 pp**).

Before (enclosing indentation removed):

```lean
have h₃ := h_eq.1
exact h₃
```

After:

```lean
exact h_eq.1
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
