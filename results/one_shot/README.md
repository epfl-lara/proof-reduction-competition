# One-shot model experiments

Start with the [current findings](FINDINGS.md), including completed RCP conditions,
the tools-enabled Codex comparison, and the credential/queue diagnosis. Historical
interpretation snapshots below retain the counts and limitations known at their dates.
The [running checkpoint](RUNNING.md) records which jobs continue in the background
and where their automatically refreshed reports are written.

[01_context_ablation](01_context_ablation/) compares a small strategy bank, goal
annotations and original-tactic cost observations on the same 15 deterministic
incumbents. Each model/condition/problem receives one independent request.
The [completed initial findings](01_context_ablation/FINDINGS.md) report all
225 initial attempts, including validity, score gains, token use and unavailable
responses. Repair and combined results are separate stages below.
An [observed direct-output case](01_context_ablation/OBSERVED_CASES.md) illustrates
a large heartbeat gain despite a slightly longer proof.
Five [verified before/after examples](OBSERVED_TRANSFORMATIONS.md) show concrete
model rewrites and deterministic cleanup steps that could inform future bank
experiments. They are post-hoc warm-up observations; the tested bank stays fixed.
The [interpretation and follow-up plan](INTERPRETATION.md) separates these
observed cases from full-condition conclusions and defines the next controlled
experiments. The [independent review snapshot](PRECOMMIT_REVIEW.md) records the
feedback-contract and artifact checks while the runs were in progress.
The [next experiment specifications](NEXT_EXPERIMENTS.md) give concrete pilots,
request ceilings, comparisons, and stop conditions. The separately authorized
[Qwen3.8 medium probe](07_qwen38_reasoning/README.md) is a completed single effort
comparison. It delivered no proof; Qwen3.8 is now on hold at the user's request.

The later [Codex agent comparison](09_codex_tools_baselines/PROTOCOL.md) tests
Astra/max and Luna/max, high and medium with tools enabled, both with and without
deterministic transforms. It uses separate inference accounting and does not
claim the RCP output-token or temperature limits.
The [Astra/low extension](10_astra_low/PROTOCOL.md) adds the requested reasoning
comparison on the same two seeds and 15 problems, with exact initial-request
parity except effort and separate per-problem low/max differences.
The completed [Astra analysis](11_astra_analysis/README.md) compares all 120
Astra/max, Astra/low, Luna/max and Luna/high cells. It separates deterministic
cleanup from model gains, examines proof structure and source/debugging tool
use, and saves proof diffs, case studies, figures and an offline evidence audit.

[02_validity_repair](02_validity_repair/) adds the requested correctness-only
debugging stage to saved proposals: up to three repair calls, stopping at the
first all-version-valid declaration, with no candidate performance feedback.
See the [repair guide](../../docs/VALIDITY_REPAIR.md). This preserves the original
direct-output baseline and reports the added calls separately.

[03_repaired_context_ablation](03_repaired_context_ablation/) applies that fixed
debugger to the full predeclared context matrix, reusing the pilot outcomes. The
[protocol](03_repaired_context_ablation/PROTOCOL.md) separates initial validity,
post-debugging validity, selected competition scores and additional model costs.

[04_combined_deterministic](04_combined_deterministic/README.md) tests an
additional deterministic cleanup of valid model proposals, including proposals
that initially scored worse. The same cleanup runs on every deterministic
incumbent as a control. This separates the model branch's contribution from
gains obtainable through additional deterministic work alone.
Its [fifteen-control comparison](04_combined_deterministic/CONTROL.md) and
[first live combined case](04_combined_deterministic/PILOT.md) are complete.

The [parallel continuation](06_parallel_continuation/PROTOCOL.md) finishes the
same original 225-cell repair/cleanup experiment after safely draining the
serial repair scheduler. It reuses completed cells and cleanup jobs exactly;
only scheduling changes. Final full-matrix repair and combined comparisons
belong in that continuation, while stages 03 and 04 retain the original partial
run's evidence. Copied historical work must not be counted again as new calls
or compute.

The requested models are DeepSeek-V4.1-Flash, Qwen3.5-397B-A17B and
Qwen3.6-35B-A3B through the user's RCP client. All use temperature **0.3**, high
reasoning requested through that client, and **32,768 generated tokens maximum**,
including reasoning. Provider enforcement of reasoning settings is not inferred
from the request alone.

The separate [reasoning-budget investigation](REASONING_BUDGET.md) records
upstream support, a read-only RCP schema check, and two small arithmetic probes
outside the matrix. Their reported reasoning counts matched budgets of 32 and
128, but both exhausted their 512-token total allowance without a completed
integer answer. These two calls used 1,024 completion tokens; they establish
neither useful Lean-proof delivery nor the backend's forced-termination mechanism.

| Condition | Additional information |
| --- | --- |
| `plain` | Common statement, incumbent proof, score objective, versions and bounded preceding source context |
| `cards` | Common context plus up to four lexically selected strategy cards |
| `goals` | Common context plus bounded incumbent goal annotations |
| `cards_goals` | Both cards and goals |
| `cards_goals_costs` | The same cards/goals plus measured original-tactic allocations at those states |

The complete planned matrix is **3 × 5 × 15 = 225 cells**. The first three plain
requests (one per model on the first problem) are retained as normal cells after
the pilot. Stage 01 has no repair turns, transport retries, alternate samples or
deterministic cleanup of generated proofs. A malformed/truncated output remains
a failed attempt there; stages 02 and 03 record subsequent correctness repairs
separately. A transport failure remains unavailable, with no invented score.
An interrupted request without a saved response is never resampled.

The later-requested [Qwen3.8-27B extension](05_qwen38_extension/PROTOCOL.md)
declared a separate **75-cell** cohort using byte-identical theorem/arm prompts.
It was [stopped](05_qwen38_extension/STOPPED.md) after 47 saved responses.
The existing client maps its requested high effort to provider `xhigh`.
Its generation and repair requests share an admission gate that accounts for
unfinished original repair workers and enforces the clarified **five requests
total across the key** once the original initial-generation pool has drained.

The common incumbent score is **46.248122%** against the original cached local
references. Every syntactically valid output receives the existing full-version
evaluation. Per-condition selected proofs retain the incumbent unless the model's
candidate improves the combined score by more than 0.05 percentage points.
Reports separate raw candidate scores/pass rates from this fallback policy.
Any best-of-all-conditions portfolio is a separate 225-request result.

The first `--prepare-only` run produced a preparation configuration; final prompt
retrieval and resume checks were fixed before any model calls. The final
`config.json`, `input_hashes.json`, `cell_index.json` and exact per-cell requests
identify the actual experiment. Prepared inputs stay immutable across resume.

See the [runner guide](../../docs/ONE_SHOT.md),
[strategy research](../../related_work/STRATEGY_CONTEXT.md),
[context implementation](../../docs/PROOF_CONTEXT.md),
[the saved context coverage audit](01_context_ablation/CONTEXT_COVERAGE.md), and
[original deterministic results](../deterministic/README.md).
