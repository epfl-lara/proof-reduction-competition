# Score-feedback optimization

Updated 2026-10-06T18:55:20.637488+00:00. **partial**: 5/15 terminal cells.

See [protocol](PROTOCOL.md). Scores are local warm-up results against fixed original references. Incomplete conditions have no full-benchmark mean.

| Model | Effort | Terminal | Score | Historical original-arm score | Structural control score |
| --- | --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next | xhigh | 5/15 | pending | — | — |

Deterministic placement: `score_edges`. Fixed reference denominators and saved original/D0 seeds.

| Model / effort | Score-only control | Final-cleanup gain | In-loop cleanup calls | Valid-proposal cleanup coverage |
| --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next / xhigh | — | pending | 0 | 0.00% |

## Estimated API-equivalent cost

Standard rates, short context per underlying request, no regional premium. Reasoning is included in output. These are estimates from reported usage, not Codex invoices or certified competition accounting. Every problem must fit $3; an affordable average is insufficient. Running cells are excluded until terminal usage is available. Unknown usage stays unknown.

| Model / effort | Priced terminal problems | Mean / problem | Maximum / problem | Problems over $3 |
| --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3.8-Flash-Next / xhigh | 0/5 | — | — | 0 |

## Completed cells

| Theorem | Model / effort | Score | Change from historical | Tool checks |
| --- | --- | ---: | ---: | ---: |
| Binius.BinaryBasefold.fold_advances_evaluation_poly | Qwen/Qwen3.8-Flash-Next / xhigh | 88.518387% | — | 12 |
| interleaved_affine_gaps_imply_tensor_gaps | Qwen/Qwen3.8-Flash-Next / xhigh | 78.367489% | — | 9 |
| putnam_1964_a4 | Qwen/Qwen3.8-Flash-Next / xhigh | 90.696095% | — | 20 |
| putnam_1964_b2 | Qwen/Qwen3.8-Flash-Next / xhigh | 98.520377% | — | 58 |
| putnam_1995_a3 | Qwen/Qwen3.8-Flash-Next / xhigh | 94.231956% | — | 5 |

## Running cells

| Theorem | Model / effort | Checks | Best score so far |
| --- | --- | ---: | ---: |
