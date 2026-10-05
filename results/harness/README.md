# Staged harness experiments

These stages test the harness changes requested after the
[Astra proof analysis](../one_shot/11_astra_analysis/README.md).

| Stage | Models | Feedback and stopping | Planned cells |
| --- | --- | --- | ---: |
| [01: structural context](01_structural_context/PROTOCOL.md) | Astra/low, Luna/max | Correctness only; stop at first valid proposal | 30 |
| [02: score search](02_score_search/PROTOCOL.md) | Astra/max, Astra/low, Luna/max | Score tuple after attempts; agent decides when to stop | 45 |
| [03: deterministic at edges](03_deterministic_edges/PROTOCOL.md) | Astra/max, Astra/low, Luna/max | Best original/D0 seed → score search → final deterministic cleanup | 45 |
| [04: deterministic during search](04_deterministic_each/PROTOCOL.md) | Astra/max, Astra/low, Luna/max | Completed historical comparison; in-loop option retired | 45 |
| [05: model configuration and cost](05_model_config/PROTOCOL.md) | Sol 6.1/max, Astra/high | Beginning/end cleanup plus score search; estimate and measure cost | 30 |

Beginning/end cleanup is now the default. In-loop cleanup is removed from the
runnable modes and agent tools. Stage 04 remains saved evidence. Refactoring is
paused while choosing the model configuration. See the stage-05 protocol for
the cost API and its pricing assumptions.

Stage 05 is complete and audited: **Sol 6.1/max 87.342215%**, **Astra/high
84.319957%**, both with 100% compatibility. Sol's estimated API-equivalent cost
is $0.987643 mean / $1.672598 maximum per problem, with 0/15 above $3. Astra/high
has 3/15 above the cap. See the [findings](FINDINGS.md) and the ready
[Sol submission JSONL](05_model_config/conditions/gpt-6.1-sol__max/selected_candidates.jsonl),
with [upload notes and validation](05_model_config/conditions/gpt-6.1-sol__max/README.md).

Stages 01–02 start from the original declaration. Stages 03–04 start from the
better all-version-valid original or saved D0 declaration. D0 is reused from
the completed deterministic experiments; no new initial search is performed.
Each later cleanup uses the same fixed ten-method pass described in the protocols.
No stage reads another model's replacement proof. Original reference measurements,
scoring and version checks are unchanged. All score-search stages have
no imposed total attempt, token or wall-time budget; individual Lean checks
retain the existing timeout. Provider/context limits still exist.

Stages 01–04 are complete and audited. Their controller records are retained.
The new study uses `model_config_controller.json`: it checks the first theorem
for both new models, audits the evidence, then expands to all 15 problems with
up to ten concurrent Codex processes. Pilot outputs are retained. A live report
is refreshed every 30 seconds and includes the best checked
score so far for active searches. Started requests without terminal evidence
are never silently resampled. A transport interruption retains all verified
discoveries and is reported as incomplete.

The [findings](FINDINGS.md) discuss completed comparisons. The
[comparison snapshot](COMPARISON.md) brings the stages and historical
controls together. Its [per-problem table](per_problem.csv) and
[check trajectories](trajectories.csv) distinguish improvements found after the
first changed valid proposal from fallback to the original. Regenerate this
snapshot with `python src/summarize_agent_harness.py`; the per-stage reports
refresh automatically during a run. Add `--watch` to keep the combined snapshot
updated until the new model-configuration controller finishes or fails.

Run or resume the controller only when no copy is active:

```bash
conda activate af
python src/run_agent_harness.py --estimate-only
python src/continue_agent_harness.py --suite models --workers 10
```

For a selected stage or theorem:

```bash
python src/run_agent_harness.py --name CallElimCorrect.substOldPostSubset
python src/audit_agent_harness.py results/harness/05_model_config
```

For an inspected controller handoff with an existing runner still active, add
`--adopt-running`. The replacement verifies the saved PID/command and monitors
that runner; it does not launch its model requests again. Only one controller
may hold the controller lock at a time.

An experiment's code, prompts, input proofs, historical controls, evaluator
configuration and Codex executable are pinned before its first request. Resume
refuses drift. Model files are writable only in the cell's workspace and Codex
runtime directories; the host owns evaluation records and all source projects
remain read-only. Source tools enforce their path scope. Shell reads remain an
instruction boundary, as in the historical Codex baseline; review traces.

Stage 02's completed outputs are fixed controls: Astra/max **88.384406%**,
Astra/low **78.130010%**, Luna/max **65.135096%**, with 100% compatibility in
each. Stages 03–04 compare against those controls, not just the older one-shot
outputs. Reports partition accepted improvements into model proposals, in-loop
cleanup and final cleanup. Shared jobs in `deterministic_jobs/` are keyed by
normalized proof and frozen provenance; their work is counted once in the
combined report. A 0.05-point selection margin and full-version pass gate apply
to every replacement. Rejected proposals and cleanup attempts remain in the
host-owned ledger.

Stage 03 (beginning/end) finished at **88.043179% / 79.118309% / 68.264239%**
for Astra/max, Astra/low and Luna/max. Stage 04 finished at
**86.977844% / 75.301134% / 61.320048%**, respectively. All six conditions selected
proofs with 100% compatibility. The in-loop placement lost on all three models;
the default follows the better placement for the cheaper configurations.

Validation before the combined runs: 502 offline tests and 102 subtests passed
(three live RCP tests excluded); saved-evidence audits passed for all 75 control
cells. The [real cleanup-tool check](validation/deterministic_tool_smoke/result.json)
completed all ten methods on the first theorem's saved D0, retained the same
37.406995% score, and reused the repeated job without evaluator calls. This is
an integration check, not a new model result or an improvement claim.

This is exploratory tuning on the supplied warm-up, not held-out validation.
The new bank contains only generic structural heuristics, with no target-specific
solutions. Reports keep each model/effort condition separate and do not pool
the best proofs across models into a single-sample result. Submission-format
JSONL is exported once all 15 cells of a condition complete.

Implementation: [runner](../../src/run_agent_harness.py),
[host tools and score ledger](../../src/proof_agent_tools.py),
[workspace client](../../src/proof_agent_client.py),
[Codex transport](../../src/proof_agent_proposal.py),
[new prompt](../../prompts/agent_refactor_system_v2.md),
[structural bank](../../prompts/structural_strategy_bank_v2.json).

Official OpenAI guidance supports explicit tool instructions and measuring prompt
changes on the actual workload; it does not establish that these particular
Lean changes will help. We verified model, effort and message routing with the
installed CLI against a localhost test server before live calls.
[Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering),
[GPT-6 prompting guidance](https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices),
[Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).
