# 04 menu

Stage: `results/11_repeated_sweeps/sweep_01/04_menu`.

Try the fixed goal-closing tactic menu at selected parsed sites.

**9 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **45.781%**. Gain over the preceding stage: **+0.436 pp**; gain over the measured original control: **+12.452 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 11.386 | 11.915 | +0.528 |
| Heartbeat reduction | 24.651 | 25.430 | +0.779 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 45.346 | 45.781 | +0.436 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 16, "accepted_transitions": 16, "analysis_requests": 150, "attempts": 528, "cache_hits": 94, "elapsed_seconds": 4515.442, "lean_candidate_checks": 558, "rounds": 75, "wall_seconds": 725.421}`. Null counters were not recorded by that runner.

Budget stops: **11**. Stop reasons: `{"no_improving_proposal": 3, "no_new_proposals": 1, "round_limit": 8, "trial_limit": 3}`.

Primary-only screened trial events: 473. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 120, "incomplete": 199, "invalid": 7, "passed": 202}`. Decision outcomes: `{"fully_scored_improvement": 55, "invalid_candidate": 7, "primary_bound_pruned": 346, "primary_failed": 120}`.

Discovery statuses: `{"ok": 75}`. Tactic outcomes: `{"failed": 5159, "heartbeat_limit": 759, "not_observed": 38, "solved": 797, "unavailable": 902, "unsolved": 1769}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `putnam_1964_b2` | 376 → 353 | +3.286 | trial_limit |
| `putnam_1995_a3` | 3043 → 2867 | +1.995 | round_limit |
| `putnam_1964_a4` | 1223 → 1211 | +0.237 | round_limit |
| `interleaved_affine_gaps_imply_tensor_gaps` | 1141 → 1140 | +0.235 | round_limit |
| `fundamental_theorem_of_variational_calculus'` | 816 → 814 | +0.230 | round_limit |
| `CallElimCorrect.extractedOldExprInVars` | 234 → 233 | +0.174 | trial_limit |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | 1288 → 1280 | +0.173 | round_limit |
| `CallElimCorrect.substOldPostSubset` | 303 → 303 | +0.141 | trial_limit |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | 1662 → 1658 | +0.065 | round_limit |

## Accepted example

`putnam_1964_b2` — trial 29 in [trials_0820057344b656d8.jsonl](trials_0820057344b656d8.jsonl). This accepted **single edit** changes the complete candidate's combined score from 82.998% to 85.324% (**+2.326 pp**).

Before (enclosing indentation removed):

```lean
simp_all [Set.ext_iff]
```

After:

```lean
simp_all
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
