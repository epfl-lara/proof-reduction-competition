# Sol 6.1/max with tactic heartbeat profiling

This trial completed all 15 warm-up problems and all 36 required version checks.
The [final audit](finalization_audit.json) passed over saved evidence: 15 model
requests, 388 host checks, 1,401 saved version outcomes and 15 final cleanup jobs.
Auditing made no new Lean or model calls.

## Conditions

- Native Codex, `gpt-6.1-sol/max`, CLI 0.160.0.
- The canonical revised mathematical prompt and five strategy cards, unchanged
  from the previous [Sol replicate](../../06_refactor_regression/PROTOCOL.md).
- Score feedback, source/goal tools, and the new explicit `profile` operation.
  Tool instructions explain automatic hotspots and optional
  `profile_tactic "label" in tac` annotations in a diagnostic copy.
- The better validated original or saved deterministic seed, with the same
  ten-method deterministic portfolio at the beginning and end. No in-loop
  deterministic tool.
- A proof must pass every required version and improve the combined score by
  more than 0.05 percentage points to replace the incumbent. A better raw proof
  survives regressive final cleanup.
- Fixed dataset token denominators and all 36 previously prepared reference
  measurements. Search never remeasured an original proof.
- Five host workers. Model tokens, attempts and generation time were uncapped;
  this trial predates the later 57-minute whole-problem deadline policy.

[config.json](config.json) preserves the exact inputs, prompts, model settings,
CLI identity, cost assumptions and 63 source pins. Profiling is diagnostic:
inclusive raw counters are divided by 1,000, nested entries overlap, and
instrumentation adds overhead. Only fresh pinned, synchronous, unannotated
`check` measurements enter scores and proof selection.

## Results and observed tool use

| Local full-cohort mean | Previous Sol replicate | Profiling trial | Change, percentage points |
| --- | ---: | ---: | ---: |
| Proof-token reduction | 74.751025% | 75.885907% | +1.134881 |
| Heartbeat reduction | 84.976477% | 84.968147% | -0.008331 |
| Compatibility | 100% | 100% | 0 |
| Combined score | 86.575834% | 86.951351% | +0.375517 |

See [comparison_final.json](comparison_final.json), [report.json](report.json)
and the complete [selected declarations](conditions/gpt-6.1-sol__max/selected_candidates.jsonl).
These are local measurements, separate from organizer scores. This is one
stochastic repeat with profiler access; the score difference does not isolate
a causal profiler effect. The mean heartbeat reduction was essentially unchanged.

The agent used profiling on every problem, producing 43 host-owned profiles:
40 successful and three failed diagnostic candidates. It used explicit labels
in three profiles across two problems. The
[usage inventory](profile_usage_after_restart.json) identifies every saved profile.

Two saved sequences show actionable feedback:

- In `CallElimCorrect.substOldPostSubset`, the first profile exposed expensive
  `simp_all` work. The immediately following candidate replaced broad
  simplification with `simp only`; ordinary scoring measured 6,717.860 then
  2,587.601 heartbeats for those intermediate candidates. The final selected
  proof used 1,274.984 heartbeats. These scored measurements are separate from
  instrumented profile costs.
- In `Binius.BinaryBasefold.fold_advances_evaluation_poly`, the agent labeled
  `fin`, `module` and `basis` steps. Inclusive diagnostic costs were 104.396,
  1,067.814 and 77.186 heartbeats respectively. Subsequent accepted revisions
  improved the combined score from 88.614685% to 90.029375% over checks 8–11.
  The sequence supports using the tool to direct edits; it does not identify
  how much improvement the profiler caused.

Exact supplied declarations, full structured traces and timestamps remain under
each cell's `evidence/profiles/`; native commands remain in `attempt_00/events.jsonl`.
The host retains all-version measurements in `evidence/checks.jsonl`.

## Resume and finalization

Nine cells completed before the installed CLI changed from 0.160.0 to 0.160.1.
The six remaining cells resumed with the original CLI and all 63 original source
pins in an isolated runtime reconstructed from actual Git sources and the
original profiling changes. Audit snapshots were never executed. See
[restart_runtime.json](restart_runtime.json) and
[restart_preflight.json](restart_preflight.json).

The last native request completed, but host finalization reported an unavailable
cached reference. The existing v4.28.0 reference was subsequently revalidated and
reused unchanged; the underlying transient failure was not recorded. Finalization
reused the saved native response, performed the remaining host checks and cleanup,
and made no new model request or original-reference measurement. Historical
completed cells, configuration and request/response bytes were preserved.

[run.json](run.json), [report.json](report.json),
[finalization_progress.json](finalization_progress.json) and
[finalization_audit.json](finalization_audit.json) describe the completed run.
Earlier progress, audit and comparison files preserve intermediate states.

## Implementation validation

The profiling changes passed `make format`, `make check`, 72 focused tests and
the full offline suite (342 tests and 102 subtests) in an isolated checkout.
The measurement backend and canonical mathematical prompts stayed unchanged.
The copied evidence matched the original bytes, and the completed 15-cell audit
passed again. See [commit_validation.json](commit_validation.json).
