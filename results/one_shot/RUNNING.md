# Running experiment checkpoint

**Superseded checkpoint:** all stage-09 and Astra/low cohorts have now finished.
The active work is the [structural-context and score-search study](../harness/README.md).
The historical checkpoint below retains its original date and counts.

Saved at **2026-10-03T19:00:42+02:00 (Europe/Zurich)**. The controllers continue to update live reports.

Qwen3.8 remains on hold at the user's request.

## Completed work

- RCP continuation: **225/225 repaired and 225/225 combined cells**, all five arms for DeepSeek, Qwen3.5 and Qwen3.6 complete and fully audited.
- Astra/max: **30/30 cells**, all final proposals valid. Original arm **78.093430%**; deterministic plus model **78.970302%**.
- Luna/max: **30/30 cells**, all final proposals valid. Original arm **53.045428%**; deterministic plus model **59.744910%**.
- The shared local deterministic baseline is **46.248122%**; full comparisons use fixed original reference measurements.

## Active work

- Luna/high is running; medium follows under the existing controller.
- [Astra/low](10_astra_low/README.md) runs alongside Luna. Both pilot proposals passed Lean and the full cohort is now running, retaining those outputs.
- Each cohort has two workers: up to four concurrent Codex requests. RCP is finished; its five-request limit is unchanged.
- Source projects are read-only to new Codex tools. The host provides correctness checks. Tools remain enabled, with no optimization-score feedback during debugging.

| Model | Effort | Seed | Finished | Final valid |
| --- | --- | --- | ---: | ---: |
| gpt-6-astra | max | deterministic | 15/15 | 15 |
| gpt-6-astra | max | original | 15/15 | 15 |
| gpt-6-luna | max | deterministic | 15/15 | 15 |
| gpt-6-luna | max | original | 15/15 | 15 |
| gpt-6-luna | high | deterministic | 3/15 | 3 |
| gpt-6-luna | high | original | 4/15 | 4 |
| gpt-6-luna | medium | deterministic | 1/15 | 1 |
| gpt-6-luna | medium | original | 1/15 | 1 |
| gpt-6-astra | low | deterministic | 1/15 | 1 |
| gpt-6-astra | low | original | 1/15 | 1 |

## Durable outputs

- [Original Codex report](09_codex_tools_baselines/README.md) and [Luna controller](09_codex_tools_baselines/controller.json).
- [Astra/low report](10_astra_low/README.md), [paired low/max differences](10_astra_low/comparison.json), and [controller](10_astra_low/controller.json).
- [RCP combined report](06_parallel_continuation/04_combined_deterministic/README.md) and [repair report](06_parallel_continuation/03_repaired_context_ablation/README.md).
- [Findings](FINDINGS.md) compare completed conditions. Partial arms have no full-benchmark mean. Completed conditions receive their own organizer-format submission; none is submitted automatically.

Do not start duplicate controllers. Saved source, input and reference hashes constrain resume. Later background outputs remain local until the next commit; no controller commits or pushes Git changes.

## Verification

The [offline suite](10_astra_low/validation/offline_tests.json) passed **475 tests and 102 subtests**, with three live-RCP tests deselected. It includes an actual CLI request to localhost proving low effort, exact prompts and enabled tools. Stage-09 now audits the first completed source-protected model call as well as preserved historical evidence. All 36 benchmark reference identities remain fixed; references were not remeasured.
