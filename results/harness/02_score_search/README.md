# Score-feedback optimization

Updated 2026-10-03T21:15:49.326875+00:00. **partial**: 1/45 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-6-astra | max | 0/15 | pending | 78.093430% | — |
| gpt-6-astra | low | 1/15 | pending | 57.222638% | 59.407773% |
| gpt-6-luna | max | 0/15 | pending | 53.045428% | 52.740977% |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6-astra / low | 75.519306% | +35.433065 pp | 7 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gpt-6-luna / max | 6 | 33.333333% |
| CallElimCorrect.substOldPostSubset | gpt-6-astra / max | 9 | 78.248859% |
