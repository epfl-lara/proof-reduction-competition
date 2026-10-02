# 10 simp

Stage: `results/11_repeated_sweeps/sweep_01/10_simp`.

Replace existing simplifier calls with compiler-suggested explicit lemma sets.

**3 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **46.112%**. Gain over the preceding stage: **+0.042 pp**; gain over the measured original control: **+12.782 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 12.082 | 12.079 | -0.003 |
| Heartbeat reduction | 26.129 | 26.257 | +0.128 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 46.070 | 46.112 | +0.042 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 21, "accepted_transitions": 3, "analysis_requests": 34, "attempts": 72, "cache_hits": 3, "elapsed_seconds": 564.322, "lean_candidate_checks": 76, "rounds": 18, "wall_seconds": 135.264}`. Null counters were not recorded by that runner.

Budget stops: **0**. Stop reasons: `{"no_improving_proposal": 9, "no_new_proposals": 6}`.

Primary-only screened trial events: 69. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"incomplete": 18, "passed": 54}`. Decision outcomes: `{"fully_scored_improvement": 3, "primary_bound_pruned": 69}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `putnam_1995_a3` | 2867 → 2893 | +0.422 | no_new_proposals |
| `putnam_1964_a4` | 1208 → 1200 | +0.151 | no_new_proposals |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | 1368 → 1366 | +0.053 | no_improving_proposal |

## Accepted example

`Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` — trial 2 in [trials_d2fbe54ae756d1f4.jsonl](trials_d2fbe54ae756d1f4.jsonl). This accepted **single edit** changes the complete candidate's combined score from 47.090% to 47.143% (**+0.053 pp**).

Before (enclosing indentation removed):

```lean
simp only []
```

After:

```lean
simp only
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
