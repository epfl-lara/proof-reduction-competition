# 03 reuse

Stage: `results/deterministic/11_repeated_sweeps/sweep_01/03_reuse`.

Try reusing an existing local fact instead of proving it again.

**1 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **45.346%**. Gain over the preceding stage: **+0.032 pp**; gain over the measured original control: **+12.016 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 11.314 | 11.386 | +0.072 |
| Heartbeat reduction | 24.626 | 24.651 | +0.024 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 45.314 | 45.346 | +0.032 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 8}`.

Recorded totals: `{"accepted_edits": 2, "accepted_transitions": 2, "analysis_requests": 17, "attempts": 2, "cache_hits": 2, "elapsed_seconds": 40.605000000000004, "lean_candidate_checks": 6, "rounds": 17, "wall_seconds": 32.115}`. Null counters were not recorded by that runner.

Budget stops: **0**. Stop reasons: `{"no_new_proposals": 15}`.

Primary-only screened trial events: 0. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"passed": 2}`. Decision outcomes: `{"fully_scored_improvement": 2}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `putnam_1995_a3` | 3087 → 3043 | +0.481 | no_new_proposals |

## Accepted example

`putnam_1995_a3` — trial 1 in [trials_9d2374f9d3343f1e.jsonl](trials_9d2374f9d3343f1e.jsonl). This accepted **single edit** changes the complete candidate's combined score from 51.727% to 52.055% (**+0.328 pp**).

Before (enclosing indentation removed):

```lean
have h₂₂ : (7 : ℤ) ∣ (f i - d i) * (10 : ℤ) ^ (i : ℕ) := h₁₀
apply (Int.prime_iff_natAbs_prime.mpr (by decide)).dvd_mul.mp
exact h₂₂
```

After:

```lean

apply (Int.prime_iff_natAbs_prime.mpr (by decide)).dvd_mul.mp
exact h₁₀
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
