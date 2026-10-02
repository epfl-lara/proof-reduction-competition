# 06 tactic menu

Stage: `results/deterministic/06_tactic_menu`.

Try the fixed goal-closing tactic menu at selected parsed sites.

**13 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **42.893%**. Gain over the preceding stage: **+3.042 pp**; gain over the measured original control: **+9.563 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 4.154 | 9.421 | +5.267 |
| Heartbeat reduction | 15.399 | 19.258 | +3.859 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 39.851 | 42.893 | +3.042 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 4}`.

Recorded totals: `{"accepted_edits": 32, "accepted_transitions": 32, "analysis_requests": 160, "attempts": 539, "cache_hits": 167, "elapsed_seconds": 4867.153, "lean_candidate_checks": 731, "rounds": 80, "wall_seconds": 1521.792}`. Null counters were not recorded by that runner.

Budget stops: **12**. Stop reasons: `{"no_improving_proposal": 2, "no_new_proposals": 1, "round_limit": 10, "trial_limit": 2}`.

Primary-only screened trial events: 373. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 109, "incomplete": 184, "passed": 246}`. Decision outcomes: `{"fully_scored_improvement": 166, "primary_bound_pruned": 264, "primary_failed": 109}`.

Discovery statuses: `{"ok": 80}`. Tactic outcomes: `{"failed": 5191, "heartbeat_limit": 721, "not_observed": 76, "solved": 661, "unavailable": 1134, "unsolved": 1660}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `putnam_1964_b2` | 1543 → 542 | +25.851 | trial_limit |
| `Core.InitsUpdatesComm` | 230 → 229 | +8.482 | round_limit |
| `CallElimCorrect.extractedOldExprInVars` | 222 → 222 | +2.143 | round_limit |
| `putnam_1995_a3` | 3280 → 3104 | +1.992 | round_limit |
| `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | 1424 → 1389 | +1.831 | round_limit |
| `putnam_1964_a4` | 1419 → 1351 | +1.754 | round_limit |
| `fundamental_theorem_of_variational_calculus'` | 851 → 834 | +1.387 | round_limit |
| `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | 408 → 398 | +0.702 | no_new_proposals |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | 1361 → 1311 | +0.674 | round_limit |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | 1767 → 1749 | +0.341 | round_limit |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | 1378 → 1370 | +0.292 | round_limit |
| `CallElimCorrect.substOldPostSubset` | 303 → 303 | +0.111 | trial_limit |
| `interleaved_affine_gaps_imply_tensor_gaps` | 1180 → 1170 | +0.068 | round_limit |

## Accepted example

`Core.InitsUpdatesComm` — trial 9 in [trials_b1f6d85dc1f90d1f.jsonl](trials_b1f6d85dc1f90d1f.jsonl). This accepted **single edit** changes the complete candidate's combined score from 33.765% to 37.792% (**+4.027 pp**).

Before (enclosing indentation removed):

```lean
simp_all
```

After:

```lean
norm_cast
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
