# Phase 0 result: NO-GO for the proposed stagnation policy

The offline replay completed without new model or Lean calls. No plain
stagnation threshold passed the [pre-registered gate](PROTOCOL.md). Keep the
stage-10 policy; Phase 1 was not launched. This result concerns event-observed
stopping on these saved chains, not the value of Dream-RSI's unrecorded branching
or online policy-learning loop.

The [Sol report](sol61/report.json) covers all 15 problems independently in each
of stages 10, 08, and 06 (45 cells). Identity replay reproduced the saved raw
incumbents in all three runs, including every first-attempt, all-attempt, and
per-attempt score in stage 10's comparison (57 attempts, tolerance 1e-9).

| Stage-10 threshold | Mean score loss (pp) | Mean freed minutes/problem | Fully on support | Estimated reinvestment (pp) |
| --- | ---: | ---: | ---: | ---: |
| 8 minutes | 0.446075 | 8.579 | 9/15 | 0.328816 |
| 10 minutes | 0.184613 | 5.928 | 11/15 | 0.227188 |
| 12, 15, or 20 minutes | 0 | 0 | 15/15 | 0 |

The gate requires at least 12/15 on support, at most 0.10 pp mean loss, at least
8 minutes freed per problem, and estimated reinvestment at least twice the lost
score, plus robustness and leave-one-out stability. Smaller thresholds lost
still more score. Stages 06 and 08 both lost zero at 8 minutes and above, but
stage 10 failed. There was no eligible threshold to select for leave-one-out.
The reinvestment column is a model estimate, not improvement discovered by replay.

Stage 10's identity raw mean is 89.357422%. Stage 08's raw mean is 86.913307%
and stage 06's is 86.557428%; these exclude final cleanup and differ from the
previously reported final-cleanup scores. About 22.22% of stage-10 attempt time
followed the last accepted improvement. That does not mean this time is safely
recoverable: deciding from the prefix can discard a later gain. Decisions here
occur after checks and at attempt end, so 12-minute thresholds do not invent an
earlier timer wakeup during a quiet terminal tail. Costs are secondary; only
4/15 stage-10 problem costs are known, and unknown usage remains unknown.

[Per-problem rows](sol61/per_problem.csv), [anytime curves](sol61/anytime.csv),
and [improvement gaps](sol61/gaps.csv) retain the fixed cohorts. The
[one-problem pilot](pilot/report.json) preceded the final full replay.
The [descriptive report](descriptive/report.json) keeps original Qwen,
retry, recovery, Gemini, and stage-12 semantic-tool evidence separate. Partial
runs are labelled `loaded_subset_only` and never supply a final cohort score
or feed the gate. See [study exclusions](study_exclusions.json): stage 13 and
early Gemini transport/calibration probes were not used.

Both final reports passed `proof-harness audit` ([Sol](sol61/audit.json),
[descriptive](descriptive/audit.json)): input/source/artifact hashes, CSV counts,
score/time arithmetic, and support counts. [Ledger spot checks](validation/ledger_spot_checks.json)
show SKI attempt 2's 11.936-minute tail; the
[support-break check](validation/support_break_spot_check.json) shows that an
8-minute cutoff in Core attempt 2 hides accepted check 46 and all later attempts,
losing 0.428392 pp.

The [validation record](validation/validation.json) preserves formatting,
lint, focused tests (12 passed), and the entire current-checkout offline suite
(457 passed, 32 Lean integration tests skipped, 102 subtests passed). That suite
used archived environment fingerprints for existing saved-certificate fixtures
and an isolated cache; normal source/reference contracts were not changed.
Earlier setup failures and the exact fixture are retained in `validation/`.
This suite is offline validation, not a new Lean proof validation.

Qwen's stage-13 runtime and prompts were unchanged. The
[preservation record](validation/preservation.json) verifies 96 protected files
and that subtracting only the replay integration patch restores the original
working-tree bytes. No stage-13 evidence was consumed or modified.

Pre-registration commit: `2cdaa496` on `phase0-offline-replay`; implementation:
`2009ed12`. The isolated worktree is `/localhome/milikic/proof-replay-phase0`.
The replay additions were initially copied to the main checkout without
absorbing its existing unrelated modifications. They are retained separately
from the source-discovery and web-tool changes.

To reproduce, use a fresh output directory:

```bash
proof-harness replay \
  --run results/harness/10_budget_resets/sol61_max_3usd \
  --run results/harness/08_tactic_profiles/sol61_max \
  --run results/harness/06_refactor_regression \
  --protocol results/harness/14_replay_stagnation/protocol.json \
  --output /tmp/sol61-replay-new
proof-harness audit --output /tmp/sol61-replay-new
```
