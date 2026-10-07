# Staged harness experiments

The maintained configurations are **Sol 6.1/max** and **Astra/max**. Both use the
revised prompt, source and goal tools, score feedback, and deterministic cleanup
at the beginning and end. Historical conditions below remain separate evidence.

| Stage | Models | Feedback and stopping | Cells |
| --- | --- | --- | ---: |
| [01: structural context](01_structural_context/PROTOCOL.md) | Astra/low, Luna/max | Correctness only; stop at first valid proposal | 30 |
| [02: score search](02_score_search/PROTOCOL.md) | Astra/max, Astra/low, Luna/max | Score tuple after attempts; agent decides when to stop | 45 |
| [03: deterministic at edges](03_deterministic_edges/PROTOCOL.md) | Astra/max, Astra/low, Luna/max | Best original/D0 seed → score search → final cleanup | 45 |
| [04: deterministic during search](04_deterministic_each/PROTOCOL.md) | Astra/max, Astra/low, Luna/max | Historical comparison; in-loop option retired | 45 |
| [05: model configuration and cost](05_model_config/PROTOCOL.md) | Sol 6.1/max, Astra/high | Beginning/end cleanup plus score search and cost reporting | 30 |
| [06: package refactor replicate](06_refactor_regression/PROTOCOL.md) | Sol 6.1/max | Same prompts, references and search settings through the maintained APIs | 15 |
| [07: native provider agents](07_native_agents/PROTOCOL.md) | DeepSeek V4.1 Flash/high via Lemex, Opus 5.5/max via Claude Code | Same V2 task, tools, score search and edge cleanup | 15 per model |
| [08: tactic profiling](08_tactic_profiles/sol61_max/README.md) | Sol 6.1/max | Source and goal tools plus tactic heartbeat diagnostics | 15 |
| [09: Qwen results and submission](09_qwen_flash_next/README.md) | Qwen3.8-Flash-Next/xhigh via Lemex | Profiling, score feedback, edge cleanup; audited original/recovery selection | 15 |
| [10: fresh budgeted attempts](10_budget_resets/sol61_max_3usd/PROTOCOL.md) | Sol 6.1/max | Fresh context from the best verified proof; cumulative $3 target and 57 minutes per problem | 15 |
| [11: Google Antigravity](11_antigravity/README.md) | Gemini 3.8 Flash/high via `agy` | $3 estimated per problem, streamed budget guard, two workers; 5 complete and 10 interrupted | 15 |
| [12: local discovery tools](12_source_discovery/README.md) | Qwen3.8-Flash-Next/xhigh via Lemex | Literal dependency search and frozen semantic discovery; 15/15 complete, 78.815525% locally | 15 |
| [13: web discovery tools](13_web_search/README.md) | Qwen3.8-Flash-Next/xhigh via Lemex | Matched web-enabled trial stopped by user at 7/15; no full-cohort mean | 15 |

The [Qwen submission](09_qwen_flash_next/submission.jsonl) reaches
**78.219958% locally**, with 100% compatibility and **36/36** passing version
checks. It combines ten original results with five improved recovery results;
the five recovery problems received additional budgets. All three saved-evidence
audits passed. The [manifest](09_qwen_flash_next/submission_manifest.json) pins
every selected proof and its source; this portfolio is separate from a single-run
model comparison.

The [fresh-attempt trial](10_budget_resets/sol61_max_3usd/COMPARISON.md) compares
the new budget tracking policy with stage 08 and records the verified gains after
each problem's first attempt. Its report and comparison update from saved
evidence; full-cohort scores require all 15 outcomes and a passed audit.

The [tactic-profiling trial](08_tactic_profiles/sol61_max/PROTOCOL.md) completed
15/15 problems and passed its saved-evidence audit. Its combined score was
**86.951351%**, with 100% compatibility. Sol profiled every problem; heartbeat
reduction was essentially unchanged from the previous replicate, and one repeat
does not isolate a causal tool benefit.

Stages 01–06 are complete and audited. The [refactor replicate](06_refactor_regression/COMPARISON.md)
reached **86.575834% combined**, with 100% compatibility and 36/36 passing version
checks, versus 87.342215% in stage 05. Its mean/max API-equivalent cost was
$1.060463/$2.536752 per problem, with 0/15 above $3. The earlier stronger submission
remains available; the two runs are separate.

Stage 07 is incomplete and stopped. The corrected Opus run completed 1/15
problems before the account quota interrupted subsequent requests; it remains
paused. DeepSeek's first pilot ended with a transport error after preserving an
improved proof. See the [native provider findings](07_native_agents/README.md).

## Completed comparisons

| Model | Score search (02) | Beginning/end cleanup (03) | In-loop cleanup (04) |
| --- | ---: | ---: | ---: |
| Astra/max | 88.384406% | 88.043179% | 86.977844% |
| Astra/low | 78.130010% | 79.118309% | 75.301134% |
| Luna/max | 65.135096% | 68.264239% | 61.320048% |

These conditions all selected proofs with 100% compatibility. In-loop cleanup
lost on all three models and is removed from the runtime and agent tools.
Beginning/end cleanup remains the default, following the better placement for
the cheaper configurations. These are exploratory warm-up results, rather than
held-out validation.

Stage 05 reached **87.342215%** for Sol 6.1/max and **84.319957%** for Astra/high,
both with 100% compatibility. Sol's API-equivalent estimate was $0.987643 mean
and $1.672598 maximum per problem, with 0/15 above $3. Astra/high had 3/15 above
the cap. See the [findings](FINDINGS.md), [historical comparison](COMPARISON.md),
and [Sol submission](05_model_config/conditions/gpt-6.1-sol__max/README.md).

## Run, resume and audit

```bash
conda activate af
proof-harness estimate --condition gpt-6.1-sol:max \
  --output results/harness/my_sol_run
proof-harness run --condition gpt-6.1-sol:max --pilot --workers 10 \
  --output results/harness/my_sol_run
proof-harness report --output results/harness/my_sol_run
proof-harness audit --output results/harness/my_sol_run
```

Use `gpt-6-astra:max` for the SOTA condition; omitting `--condition` selects both.
The pilot is audited before the rest of the batch and reused in the full cohort.
A report refreshes every 30 seconds. Repeating a command reuses completed cells;
started requests without terminal evidence are never silently resampled.
Source or configuration changes require a new output directory.

Stages 01–02 start from the original declaration. Stages 03–06 start from the
better all-version-valid original or saved D0 declaration. D0 comes from the
completed deterministic experiments; references are never remeasured. The same
bounded ten-method pass runs at the end. Every replacement must pass all required
versions and improve the combined score by more than 0.05 percentage points.
Historical searches had no imposed wall-time budget. New runs default to a
57-minute whole-problem deadline, retaining the best fully verified proof when
time expires. A native final normally ends the search; bounded transport recovery
shares the same deadline. Optional budget tracking admits fresh optimization
attempts under an explicit restart limit. Costs are reported per problem under
explicit API-equivalent assumptions, rather than as invoices.

Each run pins code, prompts, source projects, inputs, denominators, CLI identity
and cost assumptions. The host owns the best-proof ledger and evaluation evidence;
model-process writes are restricted to the workspace and runtime directories.
Shared cleanup jobs in `deterministic_jobs/` are keyed by proof and provenance.
Reports keep conditions separate and export one submission JSONL per complete
condition, without pooling the best outputs across models.

## Implementation and archived evidence

See [the architecture and APIs](../../docs/ARCHITECTURE.md),
[batch runner](../../src/proof_eval/harness/runner.py),
[host score ledger](../../src/proof_eval/harness/session.py),
[provider transport](../../src/proof_eval/providers/codex.py),
[revised prompt](../../prompts/refactor_system.md), and
[structural bank](../../prompts/strategy_bank.json).

Historical controller records, per-problem tables and trajectories remain saved.
The per-study scripts were retired; their source is preserved in checkpoint
`bfb2ade6` and content-addressed audit snapshots. The current auditor validates
saved evidence without importing or executing historical code.
