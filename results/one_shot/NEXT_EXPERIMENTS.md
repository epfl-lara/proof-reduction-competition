# Next experiments: change one part at a time

**Current priority (2026-10-03):** finish the tools-enabled
[Astra/max and Luna/max, high, medium baselines](09_codex_tools_baselines/PROTOCOL.md).
Keep the Qwen3.5 continuation running. **Qwen3.8 is on hold at the user's request**:
its high cohort was stopped, and the one medium probe also exhausted 32,768
tokens without delivering a proof. No further Qwen3.8 calls are scheduled.

The delivery comparison below was proposed before those updates. Its Qwen3.8
pilot is now [recorded](07_qwen38_reasoning/README.md); its proposed expansion is
withdrawn while that model is on hold. The remaining sections describe possible
follow-ups, not additional launched experiments. Finish the current cohorts and
keep their inputs and generation policies unchanged. The sequence gives each
test a concrete entry condition, comparison, budget, and decision.
It complements the [observed transformations](OBSERVED_TRANSFORMATIONS.md) and
the existing [interpretation](INTERPRETATION.md).

## 1. Deliver a complete declaration within 32K generated tokens

The first intervention should preserve the complete incumbent and all current
input context. Change only requested reasoning effort:

| Model | Current request / client mapping | Proposed comparison |
| --- | --- | --- |
| DeepSeek-V4.1-Flash | `high` / `high` | `low` / `low` |
| Qwen3.8-27B | `high` / `xhigh` | One `medium` / `medium` probe completed; expansion on hold |

These mappings come from the existing RCP client. They identify the payload;
they do not establish the provider's internal reasoning budget. DeepSeek
`medium` maps to `high`, so it would not implement the intended contrast.
Do not simultaneously add a thinking-token budget, change prompts, remove
context, or increase the 32,768-token cap.

Start with the saved `plain` input for
`CallElimCorrect.substOldPostSubset`, one request per model, temperature 0.3.
This is an engineering smoke test selected after observing the current study,
not an independent effectiveness test. Save the exact messages, requested and
mapped effort, finish reason, token usage, final content, parsed declaration,
and all-version evaluation. A final-channel reasoning continuation is not a
delivered Lean declaration. A copied incumbent is valid delivery, but not an
optimization success.

If the smoke output contains a complete declaration, inspect its compiler result
before scaling. A nonempty but malformed answer fails the output contract; a
well-formed invalid declaration exposes a separate correctness issue. If there
is still no complete declaration, stop that model's expansion and investigate
serving/parsing or an explicitly separate thinking-budget test. The earlier
[two arithmetic probes](REASONING_BUDGET.md) did not establish useful answer
delivery, so do not treat their matching token counts as a solved mechanism.

For a working contract in a future authorized comparison, retain the identical pilot as one of the fifteen
`plain` warm-up cases and run the remaining fourteen once. Maximum initial
generation budget originally proposed across both models: **30 requests and 983,040 completion
tokens**, including reasoning; the two pilots are included. Keep correctness
repairs out of this delivery comparison. Record nonempty-final rate, complete
declaration rate, truncation, all-version validity, changed valid proofs,
accepted score gain, and known/missing token usage separately.

Use the existing high-effort `plain` cases as an explicitly historical development
comparison, not a contemporaneous randomized control. Provider changes between
cohorts are a possible explanation for differences. A later confirmation needs
interleaved conditions on disjoint declarations. Do not resample the current
matrix to replace its empty outputs.

Implementation prerequisite: the current one-shot runner intentionally fixes
`high` in its configuration, requests, and API calls. After the active runs
finish, expose a reasoning-effort option consistently in those three places,
include its client mapping in the immutable experiment identity, and test that
resume rejects a changed effort. Update the auditor to verify the declared
policy. There is no working `--reasoning-effort` switch in the current runner;
do not claim one or alter a running experiment's files.

## 2. Test a local-edit output contract against whole-proof rewriting

After delivery works, use one model and one fixed context arm. A useful first
candidate is Qwen3.5-397B-A17B, whose initial cohort delivered many nontruncated
answers. Freeze the arm before making new calls; do not choose different arms
for different theorems from the current winners.

For each of the fifteen incumbents, the harness selects one tactic syntax span
using a declared rule before generation. Supply the same full incumbent,
environment information, selected goal, and relevant context in both conditions.
The whole-proof condition returns the declaration; the local condition returns
the replacement for that exact span. Reconstruction must verify the original
span bytes and leave the rest of the declaration unchanged. Nested, ambiguous,
or unavailable spans must have a declared fallback before the cohort starts.
Do not silently drop difficult rows.

Run one end-to-end engineering case before freezing and expanding the comparison.
If its final contract matches the cohort exactly, retain its request rather
than silently drawing it again. If the contract changes, record the excluded
development calls and their costs separately from the cohort ceiling below.
Then use **30 initial requests**: fifteen rows times two output contracts.
Interleave paired conditions and counterbalance their order across theorems
so request order does not systematically track the output contract.
Both conditions get the same maximum of three
correctness-only repairs and stop at the first all-version-valid proof. That is
at most **120 total requests / 3,932,160 completion tokens** at the existing cap,
including initial attempts and reasoning. These are ceilings, not cost estimates.
Keep actual request and token counts beside scores. This is a historical ceiling,
not a scheduled budget; the Qwen3.8 expansion is on hold.

Compare initial and final validity, changed valid proofs, incumbent copies,
accepted score, and combined cleanup gain. Apply the same fixed deterministic
cleanup to both branches and use matching incumbent controls. A smaller edit
may preserve validity yet prevent useful structural rewrites; the CCS example
shows why both score gain and delivery matter. Do not add score feedback or
multiple optimization proposals in this test.

## 3. Ground one edit in the actual project API

Only after the output contract is fixed, compare the current preceding-source
excerpt with selected dependency signatures retrieved from the pinned project.
Keep the model, edit span, goals, card budget, generation policy, and total input
token budget fixed. Record which declaration each signature came from and verify
its availability in every required environment. This tests context relevance;
increasing all context fields together would not identify the useful addition.

Use a compact, version-checked API packet before growing the abstract strategy
bank. The current goal extractor has documented coverage and truncation limits;
an external extractor integration should emit the same context schema before
being compared. A new bank example must exclude the target declaration and
overlapping source proofs. The warm-up transformations are debugging examples,
not clean training or retrieval holdouts.

## Decision for a later harness

Keep compilation, scoring, context retrieval, and candidate selection in the
harness for both tracks until these tests justify a different boundary. The
model contract can be the same for prompting a closed model and training an open
model. The current results do not require teaching either model a general tool
protocol.

Choose repair depth from the saved [repair-budget replay](../../docs/VALIDITY_REPAIR.md),
not validity alone: a final incumbent copy does not earn an optimization gain.
Depth three has already produced an accepted Qwen3.5 improvement, so evidence
of zero third-round gain for another model does not justify a universal cap of
two. Likewise, compare the measured benefit of cleaning rejected valid proposals
with its unique-job cost before dropping that branch.

For open-model SFT, collect disjoint, version-checked changed-proof/edit pairs
only after fixing the useful contract. Retain invalid and score-rejected siblings
with their actual labels for later selector or reward work. Treat incumbent
copies as recovery examples, not positive optimization targets. Evaluate SFT
before adding GRPO or test-time score feedback; those are separate interventions.
No training or new inference-search loop is part of the current experiment.

All later runners must share the key's **five total in-flight request limit**.
Generation, correctness repair, metadata calls, and concurrent experiments must
not each assume an independent allowance of five. The current gate enforces the
bound but does not provide FIFO admission; a queued repair waited approximately
39 minutes while newer requests obtained slots. Before another long concurrent
study, add and test fair admission, including dead-waiter recovery and global
limit preservation. Keep queue duration separate from time admitted to HTTP.
Do not change the gate inside the current frozen runs.
