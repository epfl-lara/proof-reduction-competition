# Archived correctness-repair findings

**This directory is an archived partial execution: 180 of 225 repair cells completed.** All 225 initial proposals are fixed. The remaining 45 cells continue in [06 parallel continuation](../06_parallel_continuation/03_repaired_context_ablation/README.md), reusing these 180 terminal cells without another sample. Full three-model conclusions belong to that continuation.

The original scheduler received one PID-only SIGINT at 2026-10-03T05:50:48.193630+00:00. Its active repair cell finished before process exit; the controller verified the drain at 2026-10-03T06:09:13.381764+00:00. All 180 started cell directories have a terminal result, and all 181 repair-start markers have saved generation records. No in-flight sample was cancelled or replayed. The immutable runtime bookkeeping remains one result behind: `run.json` records 179 cells and one formerly active key; the old summary records 178 completed-cell repair requests. Terminal evidence and the rebuilt report correctly contain **180 cells and 181 repair requests**. See the [handoff protocol](../06_parallel_continuation/PROTOCOL.md) and [drain manifest](../06_parallel_continuation/launch.json).

The [saved-evidence audit](validation/repair_evidence_audit.json) passed for all 180 recorded cells and 181 rounds, with all 36 cached version references unchanged. Its `complete_required=false` and 45 missing cells are intentional. Reporting and auditing made no model calls, Lean calls, or reference measurements.

## Complete conditions and candidate validity

The shared deterministic incumbent D0 averages **46.248122%** local combined competition score over fifteen warm-up proofs. L is the final incumbent-selected score after one optimization proposal and at most three correctness-only repairs. Debugging stops at the first all-version-valid proof and receives no score or heartbeat feedback. Empty initial outputs are not regenerated. Every score mean below requires all fifteen outcomes; no model or arm is pooled into a proof portfolio.

| Model | Arm | Completed / 15 | Selected L | Gain vs D0 pp | Valid before → after, completed rows | Model returned incumbent | Improvements |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | plain | 15/15 | 46.248122 | +0.000000 | 0 → 0 | 0 | 0 |
| DeepSeek-V4.1-Flash | cards | 15/15 | 48.470100 | +2.221978 | 1 → 4 | 1 | 2 |
| DeepSeek-V4.1-Flash | goals | 15/15 | 47.266594 | +1.018472 | 1 → 2 | 0 | 2 |
| DeepSeek-V4.1-Flash | cards_goals | 15/15 | 46.433972 | +0.185850 | 0 → 1 | 0 | 1 |
| DeepSeek-V4.1-Flash | cards_goals_costs | 15/15 | 48.124185 | +1.876063 | 1 → 4 | 2 | 1 |
| Qwen3.5-397B-A17B | plain | 6/15 | — | — | 0 → 6 | 1 | 2 |
| Qwen3.5-397B-A17B | cards | 6/15 | — | — | 0 → 6 | 2 | 2 |
| Qwen3.5-397B-A17B | goals | 6/15 | — | — | 0 → 3 | 1 | 0 |
| Qwen3.5-397B-A17B | cards_goals | 6/15 | — | — | 0 → 5 | 1 | 1 |
| Qwen3.5-397B-A17B | cards_goals_costs | 6/15 | — | — | 0 → 4 | 2 | 0 |
| Qwen3.6-35B-A3B | plain | 15/15 | 46.396101 | +0.147979 | 0 → 5 | 2 | 1 |
| Qwen3.6-35B-A3B | cards | 15/15 | 46.248122 | +0.000000 | 0 → 6 | 5 | 0 |
| Qwen3.6-35B-A3B | goals | 15/15 | 46.348342 | +0.100220 | 0 → 10 | 7 | 1 |
| Qwen3.6-35B-A3B | cards_goals | 15/15 | 46.248122 | +0.000000 | 1 → 7 | 4 | 0 |
| Qwen3.6-35B-A3B | cards_goals_costs | 15/15 | 46.248122 | +0.000000 | 0 → 6 | 1 | 0 |

Across the 180 completed cells, matched all-version validity rose from **4 to 69**; 65 invalid proposals became valid. However, **29** final generations returned the supplied incumbent. Of the **40** valid changed proposals, **13** improved the selected score. Returning an incumbent is a model-output event, distinct from the harness retaining it after failure. These are diagnostic counts over completed requests, not an aggregate competition score.

Qwen35 goals recovered validity in 10/15 cases, but seven returned the incumbent and only one improved the score. Its higher validity count therefore does not establish a better optimizer. DeepSeek cards improved two proofs; its entire +2.221978-point mean gain comes from those two cases. Qwen397 still lacks nine outcomes per arm in this archive, so its full-condition score and context effects remain blank.

## Where the score moved

- [DeepSeek / cards / `putnam_1995_a3`](cells/4096d43f3fc0c91ae033c88f84c0629b92fdd0d78d968b5baab632d90dd8c6c2/result.json): two repairs; score **55.160632 → 79.798845**. Length reduction rose from 29.179927% to 72.288862% and heartbeat reduction from 36.301968% to 67.107672%, with every required version passing.
- [DeepSeek / cards / `putnam_1964_a4`](cells/684df68125a4c59a7137b4bb9aa39f12e987862100dcd9c400252d7b2ccdecd4/result.json): one repair; score **73.319454 → 82.010916**. The proof fell from 1,193 to 772 arena tokens while heartbeat reduction also improved.
- [DeepSeek / costs / CCS bisimilarity](cells/9e76d02f19edb27267fcce50a300130438ef2f47e09a1168d0b6bf34d0a83f7b/result.json): initially valid; score **33.333083 → 61.474032**. The proof grew from 251 to 260 tokens, while heartbeat reduction rose to 88.007752%. This illustrates why selection must use the combined competition score, rather than shortening alone.
- [Qwen35 / plain / ArkLib fiberwise proof](cells/065283d1cff52e87889f6d247a45981c0be261c4b1d522cb453d52a542d43f0e/result.json): two repairs; score **38.043633 → 40.263320**, from reductions in both length and heartbeats.

These are jointly changed proofs, not isolated causal tests of a particular tactic. The [per-proof CSV](per_problem.csv) provides all gains and failures; the [source table](source_results.csv) retains project-level denominators.

## Paired context differences

All differences use the same fifteen proofs and final selected L. These complete-cohort descriptive effects have no confidence intervals or significance claim: there is one stochastic proposal per cell, and arms spend different numbers of repair calls.

| Model | Cards − plain | Goals − plain | Cards+goals − plain | Costs − cards+goals | Card main effect | Goal main effect | Interaction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | +2.221978 | +1.018472 | +0.185850 | +1.690214 | +0.694678 | -0.508828 | -3.054601 |
| Qwen3.5-397B-A17B | — | — | — | — | — | — | — |
| Qwen3.6-35B-A3B | -0.147979 | -0.047759 | -0.147979 | +0.000000 | -0.124099 | -0.023880 | +0.047759 |

Card main effect averages `cards−plain` and `cards_goals−goals`; goal main effect averages `goals−plain` and `cards_goals−cards`; interaction is `cards_goals−cards−goals+plain`. Cost context is compared only with `cards_goals`. For DeepSeek, costs versus cards+goals has one positive and one negative proof difference, with thirteen ties. Its positive mean is not evidence that cost context helped consistently.

## Physical calls and reported token usage

| Scope represented once | Calls | Prompt tokens | Completion tokens | Reasoning tokens, subset | Missing usage records |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fixed original initial matrix | 225 | 1,773,985 | 3,745,883 | 3,548,772 | 3 |
| Additional repairs in this archive | 181 | 1,184,338 | 1,860,342 | 1,599,904 | 1 |

The five reused engineering-pilot cells contain **three repair calls**, totaling 11,697 prompt and 38,387 completion tokens. They are included once in the 181 repair calls above; adding the stage02 totals again would double-count them. These same 180 cells and their 181 recorded calls will be copied into stage06, where they must again be counted only once. The two separate arithmetic budget probes (1,024 completion tokens) and all Qwen3.8 extension calls are outside these counts. Missing transport usage is not estimated, so totals describe observed provider usage rather than complete billing.

The original initial matrix had 73 length-truncated responses, including 70 empty final outputs with reported reasoning. This archive adds 14 such empty, truncated repair outputs. Reasoning tokens are already part of completion tokens. An exhausted reasoning channel is not evidence that a Lean proof needs more than 32,768 output tokens; see the [separate budget investigation](../REASONING_BUDGET.md).

## What this establishes and what follows

Correctness-only repair can recover usable optimizations, but its success rate must distinguish incumbent copies, valid inferior proposals, and score improvements. The complete DeepSeek and Qwen35 conditions above are usable benchmark results and have independent fifteen-proof submission exports. This archive does not establish a full Qwen397 comparison.

Finish the [unchanged-request continuation](../06_parallel_continuation/PROTOCOL.md), then compare L with the matched deterministic control and post-model cleanup in its stage04 results. Keep the Qwen3.8 follow-up separate: it was added after viewing partial results and requests a model-specific `xhigh` provider effort through the frozen client. Scheduling changed for the continuation, and request duration includes overlapping service/admission waits; no latency ranking is justified.

The warm-up data are development examples, not a held-out evaluation. Source excerpts and goal annotations are bounded, all first-pass prompts contain the complete incumbent, and no original-unoptimized model-only arm was tested. Next context or reasoning-budget variants should be new paired experiments rather than edits to these saved requests.

Reproduction: `python src/report_repair_matrix.py --input results/one_shot/03_repaired_context_ablation` and `python src/audit_validity_repair.py --input results/one_shot/03_repaired_context_ablation`. Do not add `--complete` for this partial archive.
