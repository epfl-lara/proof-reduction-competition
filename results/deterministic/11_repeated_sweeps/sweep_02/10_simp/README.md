# 10 simp

Stage: `results/deterministic/11_repeated_sweeps/sweep_02/10_simp`.

Replace existing simplifier calls with compiler-suggested explicit lemma sets.

**0 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **46.248%**. Gain over the preceding stage: **+0.000 pp**; gain over the measured original control: **+12.919 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 12.187 | 12.187 | +0.000 |
| Heartbeat reduction | 26.557 | 26.557 | +0.000 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 46.248 | 46.248 | +0.000 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 0, "accepted_transitions": 0, "analysis_requests": 28, "attempts": 68, "cache_hits": 26, "elapsed_seconds": 272.646, "lean_candidate_checks": 42, "rounds": 15, "wall_seconds": 120.752}`. Null counters were not recorded by that runner.

Budget stops: **0**. Stop reasons: `{"no_improving_proposal": 9, "no_new_proposals": 6}`.

Primary-only screened trial events: 68. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"incomplete": 18, "passed": 50}`. Decision outcomes: `{"primary_bound_pruned": 68}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

No improvement was selected under this stage's recorded search and acceptance budgets.

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
