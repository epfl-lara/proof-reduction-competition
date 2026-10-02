# 06 simp min

Stage: `results/deterministic/11_repeated_sweeps/sweep_02/06_simp_min`.

Remove chunks and individual arguments from explicit simplifier lists.

**2 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **46.248%**. Gain over the preceding stage: **+0.010 pp**; gain over the measured original control: **+12.919 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 12.167 | 12.187 | +0.020 |
| Heartbeat reduction | 26.547 | 26.557 | +0.010 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 46.238 | 46.248 | +0.010 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 2, "accepted_transitions": 2, "analysis_requests": 17, "attempts": 326, "cache_hits": 16, "elapsed_seconds": 2008.175, "lean_candidate_checks": 315, "rounds": 17, "wall_seconds": 512.705}`. Null counters were not recorded by that runner.

Budget stops: **3**. Stop reasons: `{"no_improving_proposal": 8, "no_new_proposals": 4, "trial_limit": 3}`.

Primary-only screened trial events: 324. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"failed": 312, "incomplete": 10, "passed": 4}`. Decision outcomes: `{"fully_scored_improvement": 2, "primary_bound_pruned": 12, "primary_failed": 312}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | 1272 → 1270 | +0.092 | trial_limit |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | 1337 → 1335 | +0.057 | trial_limit |

## Accepted example

`FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` — trial 45 in [trials_846f4b847d270ab1.jsonl](trials_846f4b847d270ab1.jsonl). This accepted **single edit** changes the complete candidate's combined score from 40.471% to 40.563% (**+0.092 pp**).

Before (enclosing indentation removed):

```lean
                  [ Bool.decide_and,
Algebra.smul_mul_assoc, mul_sub, Algebra.mul_smul_comm, sub_mul]
```

After:

```lean
                  [
Algebra.smul_mul_assoc, mul_sub, Algebra.mul_smul_comm, sub_mul]
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
