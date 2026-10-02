# 06 simp min

Stage: `results/deterministic/11_repeated_sweeps/sweep_01/06_simp_min`.

Remove chunks and individual arguments from explicit simplifier lists.

**2 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **46.016%**. Gain over the preceding stage: **+0.054 pp**; gain over the measured original control: **+12.686 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 11.888 | 11.941 | +0.053 |
| Heartbeat reduction | 25.997 | 26.106 | +0.110 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 45.962 | 46.016 | +0.054 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 3, "accepted_transitions": 3, "analysis_requests": 18, "attempts": 310, "cache_hits": 4, "elapsed_seconds": 1967.5140000000001, "lean_candidate_checks": 312, "rounds": 18, "wall_seconds": 497.763}`. Null counters were not recorded by that runner.

Budget stops: **3**. Stop reasons: `{"no_improving_proposal": 8, "no_new_proposals": 4, "trial_limit": 3}`.

Primary-only screened trial events: 307. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 295, "incomplete": 11, "passed": 4}`. Decision outcomes: `{"fully_scored_improvement": 3, "primary_bound_pruned": 12, "primary_failed": 295}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | 1280 → 1272 | +0.750 | trial_limit |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | 1347 → 1345 | +0.063 | trial_limit |

## Accepted example

`FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` — trial 52 in [trials_846f4b847d270ab1.jsonl](trials_846f4b847d270ab1.jsonl). This accepted **single edit** changes the complete candidate's combined score from 39.866% to 40.471% (**+0.605 pp**).

Before (enclosing indentation removed):

```lean
[ofListBasis_eq_ofList, map_mul, pb]
```

After:

```lean
[ofListBasis_eq_ofList]
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
