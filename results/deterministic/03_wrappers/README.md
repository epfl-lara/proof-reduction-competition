# 03 wrappers

Stage: `results/deterministic/03_wrappers`.

Contract local return wrappers using parsed syntax spans.

**5 of 15 proofs changed. The selected outputs pass 36/36 required version checks.**

Fully scored problems: 15/15. Full-benchmark combined score: **37.847%**. Gain over the preceding stage: **+0.748 pp**; gain over the measured original control: **+4.518 pp**.

| Full warm-up mean | Initial | Selected | Change (pp) |
| --- | ---: | ---: | ---: |
| Token reduction | -1.716 | 0.148 | +1.863 |
| Heartbeat reduction | 13.015 | 13.395 | +0.380 |
| Compatibility | 100.000 | 100.000 | +0.000 |
| Combined | 37.100 | 37.847 | +0.748 |

## Search and limits

Configuration: `{"budget": {"min_gain": 0.05, "rounds": 6, "sites": 6, "trials": 64}, "workers": 4}`.

Recorded totals: `{"accepted_edits": 31, "accepted_transitions": 14, "analysis_requests": 29, "attempts": 14, "cache_hits": 17, "elapsed_seconds": 406.48, "lean_candidate_checks": 36, "rounds": 29, "wall_seconds": 170.309}`. Null counters were not recorded by that runner.

Budget stops: **0**. Stop reasons: `{"no_new_proposals": 15}`.

Primary-only screened trial events: 0. Version-check outcomes: `{"passed": 36}`.

Candidate evaluation statuses: `{"passed": 14}`. Decision outcomes: `{"fully_scored_improvement": 14}`.

Discovery statuses: `{}`. Tactic outcomes: `{}`. Proposal/analysis error events and diagnostics: **0** (`{}`). The report JSON breaks tactic availability and outcomes down by tactic and benchmark source.

## Changed proofs

| Problem | Tokens before → after | Combined gain (pp) | Stop |
| --- | ---: | ---: | --- |
| `putnam_1995_a3` | 4105 → 3617 | +5.784 | no_new_proposals |
| `putnam_1964_a4` | 1776 → 1626 | +2.875 | no_new_proposals |
| `putnam_1964_b2` | 1848 → 1726 | +2.385 | no_new_proposals |
| `interleaved_affine_gaps_imply_tensor_gaps` | 1353 → 1349 | +0.090 | no_new_proposals |
| `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | 1457 → 1453 | +0.084 | no_new_proposals |

## Accepted example

`putnam_1964_a4` — trial 3 in [trials_9db3d07c62677e1b.jsonl](trials_9db3d07c62677e1b.jsonl). This accepted **single edit** changes the complete candidate's combined score from 59.095% to 59.478% (**+0.383 pp**).

Before (enclosing indentation removed):

```lean
have h₄ : u (n + (j - i)) = u n := by
  have h₅ : u (i + (n - i)) = u (j + (n - i)) := by
    have h₆ := h₁ (n - i)
    simp only at h₆ ⊢
    <;> omega
  have h₆ : i + (n - i) = n := by
    omega
  have h₇ : j + (n - i) = n + (j - i) := by
    omega
  rw [h₆] at h₅
  rw [h₇] at h₅
  linarith
exact h₄
```

After:

```lean
have h₅ : u (i + (n - i)) = u (j + (n - i)) := by
  have h₆ := h₁ (n - i)
  simp only at h₆ ⊢
  <;> omega
have h₆ : i + (n - i) = n := by
  omega
have h₇ : j + (n - i) = n + (j - i) := by
  omega
rw [h₆] at h₅
rw [h₇] at h₅
linarith
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
