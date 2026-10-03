# Observed direct-output success

This is a concrete case from the matrix, selected after observing its result.
It does not establish the best model or context condition across the full
benchmark; that comparison is reported separately in [README.md](README.md).

## Explicit constructor terms and delayed destructuring

DeepSeek-V4.1-Flash, with `cards_goals_costs`, produced an immediately valid
replacement for `Cslib.CCS.bisimilarity_congr_choice`. It required **zero repair
calls** and passes **v4.33.0-rc2, v4.32.0 and v4.31.0** unchanged.

| Measure | Deterministic incumbent | Direct model proposal |
| --- | ---: | ---: |
| Competition tokens | 251 | 260 |
| Length reduction | 0% | -3.585657% |
| Heartbeat reduction | -0.000751% | 88.007752% |
| Compatibility | 100% | 100% |
| Combined score | 33.333083% | 61.474032% |

The local per-problem gain is **28.140949 percentage points**, against unchanged
cached references. The longer proof improves the combined competition objective
through a large heartbeat reduction.

The rewrite replaces repeated `exists` / `constructor` / `apply` sequences with
explicit constructor terms such as
`⟨s2', Tr.choiceL htr2, ChoiceBisim.bisim (hb.le_bisimilarity _ _ hr2)⟩`.
It also moves destructuring of `hbisim` inside the branch that needs it, after
splitting the transition cases. These changes occur together; the experiment
does not attribute the heartbeat saving to either change alone.

The [original result](cells/9e76d02f19edb27267fcce50a300130438ef2f47e09a1168d0b6bf34d0a83f7b/result.json)
contains the exact generated declaration, provider metadata, all-version checks
and metrics. The [evidence audit](validation/evidence_audit.json) passed with
this accepted candidate included and all 36 cached references unchanged.
The combined experiment applies its fixed deterministic cleanup separately;
the values above describe the original, unprocessed model response.
