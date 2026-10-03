# Running experiment checkpoint

Saved at **2026-10-03T10:49:28.246486+00:00**. This is a checkpoint, not a completed model comparison.

Qwen3.8 is on hold at the user's request. The high cohort is stopped and the single medium probe finished without a proof. No further Qwen3.8 calls are scheduled.

## Active work

- RCP continuation: 209/225 repaired cells, 208/225 combined cells. DeepSeek and Qwen3.6 conditions are complete; Qwen3.5 continues.
- Codex: 17/120 terminal cells. Astra/max runs first; Luna/max, high and medium are queued in the same fixed manifest. Tools remain enabled. No extra samples replace interrupted or failed requests.

| Model | Effort | Seed | Finished | Final valid |
| --- | --- | --- | ---: | ---: |
| gpt-6-astra | max | deterministic | 9/15 | 9 |
| gpt-6-astra | max | original | 8/15 | 8 |
| gpt-6-luna | max | deterministic | 0/15 | 0 |
| gpt-6-luna | max | original | 0/15 | 0 |
| gpt-6-luna | high | deterministic | 0/15 | 0 |
| gpt-6-luna | high | original | 0/15 | 0 |
| gpt-6-luna | medium | deterministic | 0/15 | 0 |
| gpt-6-luna | medium | original | 0/15 | 0 |

## Durable outputs

- [Codex report](09_codex_tools_baselines/README.md) and [controller status](09_codex_tools_baselines/controller.json). The controller resumes pending cells within the fixed manifest; the reporter audits completed cells and refreshes the report.
- [RCP combined report](06_parallel_continuation/04_combined_deterministic/README.md), [repair report](06_parallel_continuation/03_repaired_context_ablation/README.md), and [reporter status](06_parallel_continuation/reporter_status.json). The watcher refreshes reports and runs full audits and offline analyses when both matrices complete.
- [Findings](FINDINGS.md) explain the completed conditions and observed Astra rewrites. Incomplete conditions have no full-benchmark mean. Each complete condition gets its own organizer-format submission; none is submitted automatically.

Both workers and report watchers are detached. Do not launch duplicate controllers. Saved source, input and reference hashes constrain resume; changing a running implementation will fail those guards. Reports written after this checkpoint are additional local artifacts and require a later commit. No background process commits or pushes Git changes.

## Verification at this checkpoint

The saved offline suite passed 466 tests with 3 live-RCP tests deselected. The initial 225-cell saved-evidence audit passed; the continuation audits passed on their explicitly partial snapshots. The Codex report audits completed-cell prompt identity, correctness evidence, score arithmetic and selection against all 36 unchanged cached references. Qualitative tool-trace inspection is separate from these audits. No reference was remeasured for this checkpoint.
