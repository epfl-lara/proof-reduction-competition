# 04 menu

Stage: `results/11_repeated_sweeps/sweep_02/04_menu`.

Try the fixed goal-closing tactic menu at selected parsed sites.

**6 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **46.230%**. Gain over the preceding stage: **+0.113 pp**; gain over the measured original control: **+12.900 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 12.094 | 12.171 | +0.077 |
| Heartbeat reduction | 26.257 | 26.518 | +0.261 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 46.117 | 46.230 | +0.113 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 8, "accepted_transitions": 8, "analysis_requests": 146, "attempts": 589, "cache_hits": 127, "elapsed_seconds": 3952.604, "lean_candidate_checks": 466, "rounds": 73, "wall_seconds": 656.147}`. Null counters were not recorded by that runner.

Budget stops: **10**. Stop reasons: `{"no_improving_proposal": 4, "no_new_proposals": 1, "round_limit": 7, "trial_limit": 3}`.

Primary-only screened trial events: 569. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 125, "incomplete": 246, "invalid": 44, "passed": 174}`. Decision outcomes: `{"fully_scored_improvement": 20, "invalid_candidate": 44, "primary_bound_pruned": 400, "primary_failed": 125}`.

Discovery statuses: `{"ok": 73}`. Tactic outcomes: `{"failed": 4821, "heartbeat_limit": 705, "not_observed": 38, "solved": 864, "unavailable": 902, "unsolved": 1657}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `putnam_1964_b2` | 355 → 348 | +0.599 | trial_limit |
| `putnam_1995_a3` | 2893 → 2893 | +0.535 | round_limit |
| `putnam_1964_a4` | 1196 → 1192 | +0.199 | round_limit |
| `CallElimCorrect.extractedOldExprInVars` | 233 → 232 | +0.151 | trial_limit |
| `CallElimCorrect.substOldPostSubset` | 303 → 303 | +0.135 | trial_limit |
| `interleaved_affine_gaps_imply_tensor_gaps` | 1140 → 1139 | +0.071 | round_limit |

## Accepted example

`putnam_1995_a3` — trial 25 in [trials_9d2374f9d3343f1e.jsonl](trials_9d2374f9d3343f1e.jsonl). This accepted **single edit** changes the complete candidate's combined score from 54.625% to 55.161% (**+0.535 pp**).

Before (enclosing indentation removed):

```lean
linarith
```

After:

```lean
omega
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
