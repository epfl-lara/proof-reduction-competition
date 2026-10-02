# 08 simp minimization

Stage: `results/08_simp_minimization`.

Remove chunks and individual arguments from explicit simplifier lists.

**10 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **44.150%**. Gain over the preceding stage: **+0.396 pp**; gain over the measured original control: **+10.821 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 9.402 | 10.069 | +0.666 |
| Heartbeat reduction | 21.860 | 22.382 | +0.522 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 43.754 | 44.150 | +0.396 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 26, "accepted_transitions": 26, "analysis_requests": 39, "attempts": 462, "cache_hits": 26, "elapsed_seconds": 3467.569, "lean_candidate_checks": 495, "rounds": 39, "wall_seconds": 845.963}`. Null counters were not recorded by that runner.

Budget stops: **6**. Stop reasons: `{"no_improving_proposal": 4, "no_new_proposals": 5, "round_limit": 1, "trial_limit": 5}`.

Primary-only screened trial events: 436. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 415, "incomplete": 19, "passed": 28}`. Decision outcomes: `{"fully_scored_improvement": 26, "primary_bound_pruned": 21, "primary_failed": 415}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `Core.InitsUpdatesComm` | 228 → 222 | +2.114 | no_new_proposals |
| `putnam_1964_a4` | 1338 → 1293 | +1.362 | round_limit |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | 1389 → 1370 | +0.846 | no_improving_proposal |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | 1306 → 1288 | +0.596 | trial_limit |
| `interleaved_affine_gaps_imply_tensor_gaps` | 1170 → 1162 | +0.258 | trial_limit |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | 1370 → 1368 | +0.203 | trial_limit |
| `putnam_1995_a3` | 3103 → 3099 | +0.187 | trial_limit |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | 1749 → 1745 | +0.172 | trial_limit |
| `CallElimCorrect.substOldPostSubset` | 305 → 303 | +0.105 | no_improving_proposal |
| `fundamental_theorem_of_variational_calculus'` | 832 → 830 | +0.098 | no_improving_proposal |

## Accepted example

`Core.InitsUpdatesComm` — trial 5 in [trials_b1f6d85dc1f90d1f.jsonl](trials_b1f6d85dc1f90d1f.jsonl). This accepted **single edit** changes the complete candidate's combined score from 48.988% to 50.443% (**+1.456 pp**).

Before (enclosing indentation removed):

```lean
[isDefined, List.mem_cons]
```

After:

```lean
[isDefined]
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
