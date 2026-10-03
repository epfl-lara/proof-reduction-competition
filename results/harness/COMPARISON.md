# Harness comparison snapshot

Updated 2026-10-03T21:07:16.001320+00:00. Full means are shown only for complete conditions.

| Stage | Model / effort | Terminal | Historical score | New score |
| --- | --- | ---: | ---: | ---: |
| correctness | gpt-6-astra / low | 15/15 | 57.222638% | 59.407773% |
| correctness | gpt-6-luna / max | 14/15 | 53.045428% | pending |
| score | gpt-6-astra / max | 0/15 | 78.093430% | pending |
| score | gpt-6-astra / low | 0/15 | 57.222638% | pending |
| score | gpt-6-luna / max | 0/15 | 53.045428% | pending |

The two stages use independent generations. Stage 02 adds performance feedback and additional inference; this is not a budget-matched comparison.

The per-problem CSV includes stage-01 comparisons and within-trajectory gains after the first changed valid proposal. This last calculation uses the best score already available at that point, so fallback to the original is not counted as a subsequent search gain.

Completion-token counts use provider-reported usage, including reasoning, across completed CLI calls. Tool checks count agent requests, including duplicate code; trajectories mark duplicates. Neither number is a dollar cost.

This is a snapshot. The per-stage README/report files refresh automatically while runs continue. Regenerate with `python src/summarize_agent_harness.py`, or add `--watch` to refresh until the controller finishes.
