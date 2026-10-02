# 08 rw min

Stage: `results/deterministic/11_repeated_sweeps/sweep_01/08_rw_min`.

Remove rewrite-list entries while preserving the order of retained rewrites.

**1 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **46.025%**. Gain over the preceding stage: **+0.009 pp**; gain over the measured original control: **+12.695 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 11.941 | 11.966 | +0.024 |
| Heartbeat reduction | 26.106 | 26.110 | +0.003 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 46.016 | 46.025 | +0.009 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 1, "accepted_transitions": 1, "analysis_requests": 16, "attempts": 174, "cache_hits": 25, "elapsed_seconds": 1043.417, "lean_candidate_checks": 150, "rounds": 16, "wall_seconds": 402.412}`. Null counters were not recorded by that runner.

Budget stops: **0**. Stop reasons: `{"no_improving_proposal": 11, "no_new_proposals": 4}`.

Primary-only screened trial events: 173. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 169, "incomplete": 2, "invalid": 2, "passed": 1}`. Decision outcomes: `{"fully_scored_improvement": 1, "invalid_candidate": 2, "primary_bound_pruned": 2, "primary_failed": 167, "primary_timeout": 2}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | 1658 → 1651 | +0.138 | no_improving_proposal |

## Accepted example

`Binius.BinaryBasefold.fold_advances_evaluation_poly` — trial 24 in [trials_9f7e14053ba6838d.jsonl](trials_9f7e14053ba6838d.jsonl). This accepted **single edit** changes the complete candidate's combined score from 39.694% to 39.832% (**+0.138 pp**).

Before (enclosing indentation removed):

```lean
[←Nat.add_zero (j.val * 2)]
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
