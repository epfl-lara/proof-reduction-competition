# 09 lint

Stage: `results/11_repeated_sweeps/sweep_01/09_lint`.

Delete tactics nominated by Lean's unused/unreachable-tactic linters.

**4 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **46.070%**. Gain over the preceding stage: **+0.045 pp**; gain over the measured original control: **+12.741 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 11.966 | 12.082 | +0.116 |
| Heartbeat reduction | 26.110 | 26.129 | +0.020 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 46.025 | 46.070 | +0.045 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 8, "accepted_transitions": 4, "analysis_requests": 19, "attempts": 7, "cache_hits": 4, "elapsed_seconds": 117.855, "lean_candidate_checks": 14, "rounds": 19, "wall_seconds": 44.284}`. Null counters were not recorded by that runner.

Budget stops: **0**. Stop reasons: `{"no_improving_proposal": 1, "no_new_proposals": 14}`.

Primary-only screened trial events: 3. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 3, "passed": 4}`. Decision outcomes: `{"fully_scored_improvement": 4, "primary_failed": 3}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | 1345 → 1337 | +0.244 | no_new_proposals |
| `fundamental_theorem_of_variational_calculus'` | 814 → 809 | +0.217 | no_new_proposals |
| `putnam_1964_a4` | 1216 → 1208 | +0.151 | no_new_proposals |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | 1651 → 1648 | +0.067 | no_improving_proposal |

## Accepted example

`fundamental_theorem_of_variational_calculus'` — trial 1 in [trials_26b11637cbbc0cf7.jsonl](trials_26b11637cbbc0cf7.jsonl). This accepted **single edit** changes the complete candidate's combined score from 43.245% to 43.462% (**+0.217 pp**).

Before (enclosing indentation removed):

```lean
rw [] at hx
```

After: this fragment is deleted.

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
