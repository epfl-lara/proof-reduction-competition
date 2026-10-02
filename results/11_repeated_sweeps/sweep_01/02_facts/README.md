# 02 facts

Stage: `results/11_repeated_sweeps/sweep_01/02_facts`.

Try deleting local facts, then recheck the complete declaration.

**6 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **45.314%**. Gain over the preceding stage: **+0.602 pp**; gain over the measured original control: **+11.984 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 10.243 | 11.314 | +1.071 |
| Heartbeat reduction | 23.892 | 24.626 | +0.735 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 44.712 | 45.314 | +0.602 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 16, "accepted_transitions": 16, "analysis_requests": 30, "attempts": 309, "cache_hits": 18, "elapsed_seconds": 2333.179, "lean_candidate_checks": 334, "rounds": 30, "wall_seconds": 604.607}`. Null counters were not recorded by that runner.

Budget stops: **1**. Stop reasons: `{"no_improving_proposal": 10, "no_new_proposals": 4, "round_limit": 1}`.

Primary-only screened trial events: 293. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 293, "passed": 16}`. Decision outcomes: `{"fully_scored_improvement": 16, "primary_failed": 288, "primary_timeout": 5}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `putnam_1964_b2` | 469 → 376 | +2.987 | round_limit |
| `putnam_1964_a4` | 1291 → 1223 | +2.295 | no_improving_proposal |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | 1734 → 1662 | +1.636 | no_improving_proposal |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | 1366 → 1347 | +1.017 | no_improving_proposal |
| `interleaved_affine_gaps_imply_tensor_gaps` | 1162 → 1141 | +0.983 | no_improving_proposal |
| `putnam_1995_a3` | 3099 → 3087 | +0.112 | no_improving_proposal |

## Accepted example

`putnam_1964_b2` — trial 15 in [trials_0820057344b656d8.jsonl](trials_0820057344b656d8.jsonl). This accepted **single edit** changes the complete candidate's combined score from 80.043% to 81.159% (**+1.116 pp**).

Before (enclosing indentation removed):

```lean
have h₃ : P.card * 2 = 2 ^ Fintype.card S := by

  have h₅ : P.card = Q.card := h₁
  linarith
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
