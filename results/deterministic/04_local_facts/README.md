# 04 local facts

Stage: `results/deterministic/04_local_facts`.

Try deleting local facts, then recheck the complete declaration.

**7 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **39.578%**. Gain over the preceding stage: **+1.731 pp**; gain over the measured original control: **+6.248 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 0.148 | 3.594 | +3.446 |
| Heartbeat reduction | 13.395 | 15.140 | +1.745 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 37.847 | 39.578 | +1.731 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 4}`.

Recorded totals: `{"accepted_edits": 29, "accepted_transitions": 29, "analysis_requests": 40, "attempts": 195, "cache_hits": 29, "elapsed_seconds": 1803.458, "lean_candidate_checks": 247, "rounds": 40, "wall_seconds": 605.93}`. Null counters were not recorded by that runner.

Budget stops: **4**. Stop reasons: `{"no_improving_proposal": 7, "no_new_proposals": 4, "round_limit": 4}`.

Primary-only screened trial events: 166. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 166, "passed": 29}`. Decision outcomes: `{"fully_scored_improvement": 29, "primary_failed": 166}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `interleaved_affine_gaps_imply_tensor_gaps` | 1349 → 1180 | +7.911 | round_limit |
| `putnam_1964_a4` | 1626 → 1419 | +4.665 | round_limit |
| `putnam_1964_b2` | 1726 → 1578 | +4.494 | round_limit |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | 1906 → 1804 | +2.798 | no_improving_proposal |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | 1453 → 1378 | +2.362 | no_improving_proposal |
| `CallElimCorrect.substOldPostSubset` | 318 → 303 | +2.001 | no_new_proposals |
| `putnam_1995_a3` | 3617 → 3462 | +1.727 | round_limit |

## Accepted example

`CallElimCorrect.substOldPostSubset` — trial 1 in [trials_786cc503728e58a4.jsonl](trials_786cc503728e58a4.jsonl). This accepted **single edit** changes the complete candidate's combined score from 34.818% to 36.819% (**+2.001 pp**).

Before (enclosing indentation removed):

```lean
have assoc := List.append_assoc (Lambda.LExpr.LExpr.getVars trigger1) (Lambda.LExpr.LExpr.getVars e1) [h1]
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
