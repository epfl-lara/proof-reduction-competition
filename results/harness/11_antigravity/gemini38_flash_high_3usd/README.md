# Score-feedback optimization

Updated 2026-10-06T17:00:59.257804+00:00. **partial**: 0/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| gemini-3.8-flash | high | 0/15 | pending | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| gemini-3.8-flash / high | — | pending | 0 | — |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.

| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| gemini-3.8-flash / high | 0/0 | — | — | 0 |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
| CallElimCorrect.substOldPostSubset | gemini-3.8-flash / high | 1 | 37.406995% |
