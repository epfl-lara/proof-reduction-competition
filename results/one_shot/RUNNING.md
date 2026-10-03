# Running experiment checkpoint

Saved at **2026-10-03T18:31:16+02:00 (Europe/Zurich)**. Luna continues in the background; this is not a completed effort comparison.

Qwen3.8 remains on hold at the user's request. No further calls are scheduled.

## Completed work

- RCP continuation: **225/225 repaired cells and 225/225 combined cells**, with full saved-evidence audits passed. All five arms for DeepSeek, Qwen3.5 and Qwen3.6 are complete.
- Astra/max: **30/30 cells**, all final proofs valid across required versions. The original-proof arm scores **78.093430%**; the deterministic-plus-model arm scores **78.970302%**. The local deterministic baseline is **46.248122%**.

## Luna recovery and active work

Luna stopped because an untracked `candidate.lean` in the shared PhysLib checkout invalidated the source-identity guard during deterministic cleanup. The [recovery](09_codex_tools_baselines/recovery/README.md) keeps sources read-only to new Codex tool processes and routes correctness checks through a host service. Tools remain enabled. Saved model responses are reused and cached references are unchanged.

The interrupted cleanup now passes its independent audit across all ten methods. The remaining Luna/max case is running; high and medium full cohorts follow automatically. No duplicate controller is needed.

| Model | Effort | Seed | Finished | Final valid |
| --- | --- | --- | ---: | ---: |
| gpt-6-astra | max | deterministic | 15/15 | 15 |
| gpt-6-astra | max | original | 15/15 | 15 |
| gpt-6-luna | max | deterministic | 14/15 | 14 |
| gpt-6-luna | max | original | 15/15 | 15 |
| gpt-6-luna | high | deterministic | 1/15 | 1 |
| gpt-6-luna | high | original | 1/15 | 1 |
| gpt-6-luna | medium | deterministic | 1/15 | 1 |
| gpt-6-luna | medium | original | 1/15 | 1 |

## Durable outputs

- [Codex report](09_codex_tools_baselines/README.md) and [controller status](09_codex_tools_baselines/controller.json). The detached watcher audits and reports each completed cell.
- [RCP combined report](06_parallel_continuation/04_combined_deterministic/README.md), [repair report](06_parallel_continuation/03_repaired_context_ablation/README.md), and [finished reporter status](06_parallel_continuation/reporter_status.json).
- [Findings](FINDINGS.md) compare completed conditions. Incomplete conditions have no full-benchmark mean. Each complete condition has its own organizer-format submission; none is submitted automatically.

Saved source, input and reference hashes constrain resume; changing a running implementation will fail those guards. Reports written after this checkpoint are additional local artifacts and require a later commit. No background process commits or pushes Git changes.

## Verification at this checkpoint

The [offline suite](09_codex_tools_baselines/recovery/validation/offline_tests.json) passed **471 tests and 102 subtests**, with three live-RCP tests deselected. The [recovery audit](09_codex_tools_baselines/recovery/validation/recovered_cleanup.json) verifies all 62 earlier terminal cells, all 67 earlier model responses and all 53 reference-cache files are byte-unchanged. The recovered cleanup completed ten stages with six accepted transitions. All 36 benchmark reference identities remain valid; no reference was remeasured.
