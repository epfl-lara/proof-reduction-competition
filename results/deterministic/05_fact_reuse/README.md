# 05 fact reuse

Stage: `results/deterministic/05_fact_reuse`.

Try reusing an existing local fact instead of proving it again.

**3 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **39.851%**. Gain over the preceding stage: **+0.273 pp**; gain over the measured original control: **+6.521 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | 3.594 | 4.154 | +0.559 |
| Heartbeat reduction | 15.140 | 15.399 | +0.259 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 39.578 | 39.851 | +0.273 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 4}`.

Recorded totals: `{"accepted_edits": 11, "accepted_transitions": 11, "analysis_requests": 25, "attempts": 11, "cache_hits": 11, "elapsed_seconds": 217.33499999999998, "lean_candidate_checks": 29, "rounds": 25, "wall_seconds": 98.934}`. Null counters were not recorded by that runner.

Budget stops: **1**. Stop reasons: `{"no_new_proposals": 14, "round_limit": 1}`.

Primary-only screened trial events: 0. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"passed": 11}`. Decision outcomes: `{"fully_scored_improvement": 11}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `putnam_1995_a3` | 3462 → 3280 | +2.433 | round_limit |
| `putnam_1964_b2` | 1578 → 1543 | +0.847 | no_new_proposals |
| `Binius.BinaryBasefold.fold_advances_evaluation_poly` | 1804 → 1767 | +0.813 | no_new_proposals |

## Accepted example

`putnam_1995_a3` — trial 3 in [trials_9d2374f9d3343f1e.jsonl](trials_9d2374f9d3343f1e.jsonl). This accepted **single edit** changes the complete candidate's combined score from 47.988% to 48.563% (**+0.575 pp**).

Before (enclosing indentation removed):

```lean
have h₂₀ : 7 ∣ (∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) + 9 * digits_to_num d := h₁₂
have h₂₁ : 7 ∣ 7 * digits_to_num d := by
  use digits_to_num d

have h₂₃ : (∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) + 2 * digits_to_num d = ((∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) + 9 * digits_to_num d) - 7 * digits_to_num d := by ring
rw [h₂₃]
exact dvd_sub h₂₀ h₂₁
```

After:

```lean

have h₂₁ : 7 ∣ 7 * digits_to_num d := by
  use digits_to_num d

have h₂₃ : (∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) + 2 * digits_to_num d = ((∑ i : Fin 9, (e i - d i) * (10 : ℤ) ^ (i : ℕ)) + 9 * digits_to_num d) - 7 * digits_to_num d := by ring
rw [h₂₃]
exact dvd_sub h₁₂ h₂₁
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
