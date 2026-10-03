# Correctness-only debugging after one optimization proposal

This stage follows the user's revised definition of one-shot optimization:
one optimization proposal, then up to three Lean debugging rounds with **no
candidate performance feedback**. The original direct-output matrix in
[01_context_ablation](../01_context_ablation/) remains intact.

See the [protocol and API guide](../../../docs/VALIDITY_REPAIR.md). Generation
settings remain temperature 0.3, high reasoning requested, and 32,768 tokens
including reasoning per request. The debugger sees the fixed statement,
current proposal, known-valid incumbent, bounded source excerpt and compiler
errors. It stops at the first proof passing every required version. The harness
then makes the separate score-based selection, with no further model call.

## Engineering pilot

[01_engineering_pilot](01_engineering_pilot/) selects four existing cells to
exercise the implemented paths, before scaling correction calls:

| Model | Initial condition and problem | Selected reason |
| --- | --- | --- |
| Qwen3.5-397B-A17B | `plain`, `CallElimCorrect.substOldPostSubset` | Nonempty proposal with real Lean errors |
| Qwen3.6-35B-A3B | `goals`, `CallElimCorrect.substOldPostSubset` | Nonempty proposal with real Lean errors |
| DeepSeek-V4.1-Flash | `cards`, `CallElimCorrect.extractedOldExprInVars` | Already-valid proposal; must stop even though its score is worse |
| DeepSeek-V4.1-Flash | `plain`, `CallElimCorrect.substOldPostSubset` | Empty truncated response; no proof to debug and no regeneration |

The pilot can make **at most six additional model requests**, three for each
compiler-failing Qwen proposal. The two DeepSeek control cases need no new
requests. At selection time there was no completed DeepSeek proposal with both
nonempty final content and a compiler failure, so a live DeepSeek compiler-repair
comparison is not inferred from these controls. This is an engineering cohort,
not a paired model/context ranking or full-benchmark score.

[02_deepseek_pilot](02_deepseek_pilot/) adds the first completed DeepSeek cell
with nonempty final code and an actual compiler failure: `plain`,
`fundamental_theorem_of_variational_calculus'`, request
`3e57795cab07517c7b270983d3cb83b81df02b553a736557c50a27453d704034`.
It was selected by eligibility and completion order, without comparing scores.
This separate pilot permits at most three repair requests, for a combined pilot
maximum of **nine additional requests** across the three models.

The pilot overlaps the ongoing direct-output run. Request durations therefore
reflect shared service load and are not a controlled latency comparison.
Initial prompts, proposals and measurements are unchanged; no repaired output
is fed into another initial cell or another condition.

The [saved validation](validation/) includes 42 passing focused tests for the
feedback filter and bounded, resumable repair loop. No live model calls are made
by those tests.
