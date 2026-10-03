# Astra low-reasoning baseline

**partial**: 3/30 cells at 2026-10-03T17:00:52.025313+00:00.

Tools are enabled. One optimization proposal, correctness-only debugging, and paired original/deterministic seeds. See [protocol](PROTOCOL.md).

All scores use fixed local original references. Original identity: 33.333333%; deterministic D0: 46.248122%. Partial conditions have no full-benchmark mean.

| Model | Effort | Seed | Finished | Initial valid | Final valid | Selected mean | Gain over D0 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| gpt-6-astra | low | deterministic | 1/15 | 1 | 1 | pending | pending |
| gpt-6-astra | low | original | 2/15 | 1 | 2 | pending | pending |

| Problem | Model / effort | Seed | Selected score | Gain over D0 | Tool checks |
| --- | --- | --- | ---: | ---: | ---: |
| `CallElimCorrect.substOldPostSubset` | gpt-6-astra / low | deterministic | 61.0877% | +23.6807 pp | 5 |
| `CallElimCorrect.substOldPostSubset` | gpt-6-astra / low | original | 40.0862% | +2.6792 pp | 3 |
| `CallElimCorrect.extractedOldExprInVars` | gpt-6-astra / low | original | 34.5070% | -2.8886 pp | 1 |

New calls after the [Luna recovery](../09_codex_tools_baselines/recovery/README.md) keep source projects read-only and route validity checks through the host. Prompts and scoring stay fixed; `isolated_calls` records the execution-policy change.

Usage and tool counts in [per_problem.csv](per_problem.csv) cover terminal cells only. Pending work and excluded pilot usage are additional; unknown usage is never zero. The full report is [report.json](report.json).

[Paired low/max differences](comparison.json) are reported per case. Full-benchmark differences remain null until all 15 cases in an arm finish. Initial requests match Astra/max exactly except reasoning effort. Low calls use source-write isolation; historical max calls preceded that fix.
