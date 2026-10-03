# Structural context and score-feedback experiments

These two stages test the next harness changes requested after the
[Astra proof analysis](../one_shot/11_astra_analysis/README.md).

| Stage | Models | Feedback and stopping | Planned cells |
| --- | --- | --- | ---: |
| [01: structural context](01_structural_context/PROTOCOL.md) | Astra/low, Luna/max | Correctness only; stop at first valid proposal | 30 |
| [02: score search](02_score_search/PROTOCOL.md) | Astra/max, Astra/low, Luna/max | Score tuple after attempts; agent decides when to stop | 45 |

Every cell starts from the original declaration. Neither stage applies
deterministic transforms or reads another model's replacement proof. Original
reference measurements, scoring and version checks are unchanged. Stage 02 has
no imposed total attempt, token or wall-time budget; individual Lean checks
retain the existing timeout. Provider/context limits still exist.

The [controller](controller.json) checks the first theorem end to end in each
stage before expanding that stage to all 15 problems. Pilot outputs are retained.
Stages run sequentially, with up to five concurrent Codex processes within a
stage. A live report is refreshed every 30 seconds and includes the best checked
score so far for active searches. Started requests without terminal evidence
are never silently resampled. A transport interruption retains all verified
discoveries and is reported as incomplete.

The [findings](FINDINGS.md) discuss completed comparisons. The
[comparison snapshot](COMPARISON.md) brings the two stages and historical
controls together. Its [per-problem table](per_problem.csv) and
[check trajectories](trajectories.csv) distinguish improvements found after the
first changed valid proposal from fallback to the original. Regenerate this
snapshot with `python src/summarize_agent_harness.py`; the per-stage reports
refresh automatically during a run. Add `--watch` to keep the combined snapshot
updated until the controller finishes or fails.

Run or resume the controller only when no copy is active:

```bash
conda activate af
python src/continue_agent_harness.py
```

For a selected stage or theorem:

```bash
python src/run_agent_harness.py --mode correctness --name CallElimCorrect.substOldPostSubset
python src/run_agent_harness.py --mode score --name CallElimCorrect.substOldPostSubset
python src/audit_agent_harness.py results/harness/01_structural_context
```

An experiment's code, prompts, input proofs, historical controls, evaluator
configuration and Codex executable are pinned before its first request. Resume
refuses drift. Model files are writable only in the cell's workspace and Codex
runtime directories; the host owns evaluation records and all source projects
remain read-only. Source tools enforce their path scope. Shell reads remain an
instruction boundary, as in the historical Codex baseline; review traces.

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
