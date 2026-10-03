# Interpreting the context, repair, and combined experiments

**Partial interpretation, based on terminal artifacts read at 2026-10-03
03:10:54 UTC:** 158/225 initial cells, 122/225 repair outcomes, and 119/225
combined outcomes were recorded. No model/context condition had finished all
fifteen initial problems. These observations motivate later experiments; they
do not select a winning model, context arm, or submission. The generated stage
reports remain the authority for later counts and complete-condition scores.

The main practical questions are currently output delivery, useful validity
recovery, and the scope of the proposed edit. Making the strategy bank larger is
not yet the first intervention supported by this evidence.

## What is established, and what is still partial

The fifteen additional deterministic controls are complete: **D1 equals D0
byte-for-byte on every theorem**, with mean combined score **46.248122%** and
36/36 required version checks passing. The fixed pass performed 961 candidate
trials without an accepted change. This is evidence about this bounded pass,
not a proof that these incumbents cannot improve. See the
[completed control comparison](04_combined_deterministic/CONTROL.md).

The following are diagnostic counts from the snapshot, summed across the five
arms for each model. They do not combine proofs into a portfolio. Different
completed theorem subsets, particularly the small completed Qwen3.5 repair
subset, make these unsuitable for ranking model success rates.

| Model | Initial outcomes / 75 | Initial all-version valid | Initial length-truncated | Repair outcomes / 75 | Final all-version valid | Final unchanged incumbent | Accepted after repair |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSeek-V4.1-Flash | 54 | 2 | 47 | 54 | 6 | 2 | 3 |
| Qwen3.5-397B-A17B | 51 | 7 | 0 | 18 | 16 | 4 | 5 |
| Qwen3.6-35B-A3B | 53 | 0 | 5 | 50 | 28 | 19 | 1 |

In particular, **46 of the 54 recorded DeepSeek initial calls returned no final
declaration and ended at the length limit**. Each of those 46 calls reports
32,768 completion tokens, all classified by the provider as reasoning tokens:
1,507,328 tokens in total. One additional length-truncated response contained
some final content. All five Qwen3.6 length-truncated responses were also empty
finals, with all 32,768 tokens reported as reasoning. These are observed outcomes
under the requested high-reasoning configuration and shared token cap; they do
not establish which provider-side setting caused the behavior. Reasoning tokens
are already included in completion tokens.

**This is not evidence that the proof needs more than 32K output tokens.** The
complete incumbent declaration was supplied to every model. Its input context
is separate from the generated-token limit; the source excerpts and goal
annotations have their own documented bounds. A model can receive a large
context and return a small proof. In the empty-final cases, the observed problem
is that generation stopped before emitting that proof.

This protocol does not regenerate an empty initial response. Consequently, a
large part of the DeepSeek matrix never enters compiler debugging. Calling
these rows simply “Lean failures” would hide the delivery problem. Conversely,
the 19 unchanged-incumbent returns among Qwen3.6's 28 valid final outputs are
correctness recovery, not optimization successes. Across all completed repair
cells, 50 finals were valid, 25 copied the incumbent, and nine were accepted;
these are three different measurements. Qwen3.5 also had two recorded initial
transport errors, whose raw scores remain unknown.

The [initial report](01_context_ablation/README.md),
[repair report](03_repaired_context_ablation/README.md), and their per-problem
CSVs retain the model/arm breakdown. Completed-result arrival is selective:
repair queues differ by model, and some initial calls are still running.
Neither partial means nor sums of overlapping request durations identify a
best model or a hardware-speed ranking.

## Concrete cases that guide the next step

| Observation | What the saved evidence supports | What it does not establish |
| --- | --- | --- |
| DeepSeek `cards_goals_costs`, `Cslib.CCS.bisimilarity_congr_choice`: immediate all-version-valid output; 251 → 260 competition tokens; combined score 33.333083 → 61.474032. | A slightly longer proof can be much better under the competition objective. The rewrite combines explicit constructor terms and delayed destructuring. | That cost context caused the gain, or that either structural change alone explains it. |
| Qwen3.5 `cards_goals`, `CallElimCorrect.substOldPostSubset`: one repair; L 41.775669 → H 41.883736 while D1 remains 37.406995. | Deterministic cleanup can exploit a model rewrite. One local `simp_all` → `contradiction` change improves heartbeats without changing tokens. | That another cleanup pass helps every model rewrite. |
| Qwen3.5 `cards`, `CallElimCorrect.extractedOldExprInVars`: one repair; L 39.165517 → H 39.467249, D1 37.395598. | The fixed menu found a useful `simp_all` → `grind` substitution at this state. | A universal cost ordering in which `grind` is cheaper than `simp_all`. |
| Qwen3.6 `plain`, ArkLib's `fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius`: two repairs; D0 38.043633 → L = H 40.263320; 1,335 → 1,301 tokens. | The smaller model can produce a useful changed proof after debugging, including on a long project theorem. Its gain is not just deletion of comments or whitespace. | That whole-proof rewriting is generally reliable, or that all displayed textual shortening earns competition-token credit. |
| Qwen3.6 `plain`, `CallElimCorrect.extractedOldExprInVars`: F 37.094125 → cleaned F 37.395598, exactly equal to D1. | Cleanup improves a valid but inferior proposal back to the control. | A rescued submission improvement: H remains D1. |
| Qwen3.5 `cards_goals`, the same theorem: F 32.648203 → cleaned F 36.281491 after four accepted cleanup transitions, still below D1 37.395598. | Several locally accepted deterministic steps can remain irrelevant to the final selected proof. | Four competition wins, or any gain over the control. |

Evidence: [direct CCS case](01_context_ablation/OBSERVED_CASES.md),
[combined engineering pilot](04_combined_deterministic/PILOT.md),
[Qwen3.5 cards cleanup](04_combined_deterministic/cells/08349fa06e3f1902200ebcdfe70e6e720bde06007eac21c44eb859ebe2448da1/result.json),
[Qwen3.6 ArkLib rewrite](04_combined_deterministic/cells/065283d1cff52e87889f6d247a45981c0be261c4b1d522cb453d52a542d43f0e/result.json),
[cleanup returning to control](04_combined_deterministic/cells/2a4b07335de248e05c9d36d9c579e3b28d8dd28db4621417ad3e99889e272483/result.json), and
[four-step inferior cleanup](04_combined_deterministic/cells/82291d9383913fa72c19a0848c3e9af5a30155accd65e1d23551ed9496c975da/result.json).
These cases were chosen after observing outcomes and are illustrations, not an
unbiased estimate of a strategy's effectiveness.

At the snapshot, seven completed combined cells beat D1, and three beat L;
none rescued a score-rejected proposal above D1. Ten accepted deterministic
transitions occurred across seven unique proposal cleanup jobs, but only three
cells gained over their previous selection. Meanwhile, two newly accepted
DeepSeek ArkLib finals were still awaiting combined cleanup. These counts will
change; the distinction between an improved F and an improved H will not.

## How to make the final comparison

Keep each of the fifteen model/arm conditions separate, with fifteen problems
per condition. Report initial validity, final validity, valid changed proofs,
unchanged-incumbent returns, and accepted improvements beside their denominators.
Use all-version validity; an incumbent fallback must not inflate the candidate
pass rate. Preserve failed/invalid raw scores as recorded zeros and unavailable
raw scores as unknown. Pending calls remain pending, not failures.

For each complete condition, display **D0, D1, L, H** and the per-axis scores.
Retain raw valid F and cleaned F in the per-problem evidence. **H − D1** measures
the model branch's contribution beyond the added deterministic control;
**H − L** measures the gain from cleanup and control fallback. H takes the exact
best eligible branch and preserves both L and D1. New candidates must exceed
D0 by more than 0.05 points; exact ties prefer the control. Report rescues only
when a distinct, previously rejected valid F cleans up past that eligibility
threshold, and distinguish beating D0 from beating D1.

Use paired contrasts on the same theorem and model: cards minus plain, goals
minus plain, the 2×2 main effects and interaction, and
`cards_goals_costs − cards_goals` for costs. A gain in the cost arm versus plain
alone cannot identify a cost-context effect. Show per-problem gains and the
largest contribution alongside the mean: the single CCS gain would contribute
about 1.876 percentage points to a fifteen-problem condition if its other
fourteen rows stayed at the incumbent. One draw per cell gives descriptive
development evidence, not statistical significance or an independent holdout.

Count original model requests and additional debugging requests separately,
including truncations, missing usage, and pending calls. Count each unique
deterministic `(theorem, proof bytes)` job once, then show its logical reuses.
At this snapshot, fifteen control references plus 47 recorded proposal
references used 35 terminal physical jobs, sharing 27 references. The registry
also contained three unfinished jobs; their work is not estimated from terminal
counters. Optimizer candidate-check counts exclude the job's separate
initial/final validation calls. Equal per-job limits do not equalize total
compute between D1 and a control-plus-model-proposal branch.

Do not pool the best proof across arms or models to report a condition's score.
Full means and independent condition exports wait for all fifteen problems and
all controls. Stage 04 was added after observing partial earlier results, so its
control is useful without making the extension an independently preregistered
confirmation.

Every model arm starts from D0, so the model experiments already combine
deterministic preprocessing with generation. There is no model-only arm starting
from the original unoptimized declaration. This matrix measures what models add
after D0 and what cleanup adds afterward; it cannot estimate how deterministic
preprocessing changes model performance relative to starting from the original.

## Next experiments, in order

These are proposed separate experiments. None changes the running prompts,
calls, repair policy, or inputs.

1. **Finish and audit this matrix before selecting a context arm.** Preserve
   every first response, correctness repair, and deterministic job. Inspect the
   final paired effects and whether gains concentrate in one theorem. Use the
   same warm-up rows for development comparisons, with a separate disjoint
   theorem/source split before making generalization or training claims.

2. **Test output delivery before enlarging the bank.** For DeepSeek, compare the
   current requested `high` reasoning effort against `low`, while holding the
   full input context, prompt, arm, temperature, and 32,768-token cap fixed. The
   [local RCP client](../../src/proof_eval/rcp.py) maps DeepSeek `medium` to
   `high`, so requesting `medium` would not implement this contrast. First check
   one saved problematic case as an engineering test, then freeze a fifteen-row
   paired cohort. Measure nonempty final declarations, truncation, initial
   all-version validity, accepted score gain, and prompt/completion tokens.
   Keep the 32K cap for this test: simply raising it is not yet justified by
   evidence that a useful proof requires more output. Subsequent
   [upstream research and two small RCP probes](REASONING_BUDGET.md) investigated
   the separate `thinking_token_budget` field: requested budgets 32 and 128
   matched reported reasoning tokens, but both 512-token outputs continued
   calculation in the final channel and delivered no completed integer answer.
   These two extra calls used 1,024 completion tokens outside the matrix. They
   support an observed reasoning-channel boundary, not a verified forced-end
   mechanism or semantic reasoning stop. A useful final-answer reserve and
   behavior on actual Lean inputs remain untested. Disabling thinking could be a separate later
   contrast. Log provider behavior rather than assuming an effort setting is a
   hard token limit. This is a budget test, not a request to continue an empty
   response in the current matrix.

   A separate prompt contrast can make the stopping rule explicit while keeping
   all input context: append “Make one best-effort proposal after a brief review.
   Once you identify a credible edit, stop exploring alternatives and return the
   complete declaration. If no edit is clear, return the incumbent immediately.
   The harness will check every required version and measure the score after
   your response.” Hold the reasoning setting fixed for that comparison; this
   wording is a behavioral nudge, not an enforced token reserve. The existing
   prompt already requests one declaration and permits incumbent fallback, so
   this tests stopping behavior rather than repairing a proven contradiction.
   Saved reasoning-token counts cannot distinguish useful reasoning, repetition,
   or serving/parser behavior. Empty length-capped outputs also occur in the
   plain arm, without bank cards or goal annotations.

3. **Compare whole-proof rewriting with a bounded local edit.** Use the same
   known-valid incumbent, one optimization proposal and the same correctness
   repair allowance. In the local condition, let the harness identify one exact
   syntax span before model generation and reconstruct the complete declaration
   from the returned replacement. Keep equivalent goal/dependency information
   in both conditions and count malformed or nonmatching edits as failures.
   First test this output contract end-to-end on one case. Then compare initial
   validity, valid changed outputs, accepted L, H − D1, and total tokens on the
   fixed cohort. The hypothesis is that smaller edits reduce delivery and
   reconstruction failures; the CCS structural gain warns that overly narrow
   edits may also lose useful transformations.

4. **Improve relevance of context before increasing its volume.** The current
   [coverage audit](01_context_ablation/CONTEXT_COVERAGE.md) records 87 observed
   goal sites out of 709 eligible syntax sites, 33 truncated goal displays,
   only 54 measured original-tactic costs, and no complete dependency-signature
   index. ArkLib has 17 truncated displays among its 18 selected sites. Compare
   a compact selected goal plus exact referenced declaration signatures against
   the bounded preceding-source excerpt, at a matched input-token budget and
   fixed edit scope. Retrieve from the pinned project environment. For example,
   a saved Physlib proposal used unavailable `norm_sq_eq_inner` and misapplied
   `Continuous.inner'` and `Metric.continuousAt_iff`; this motivates testing
   API grounding, not claiming that omitted context caused the errors.
   [Saved failed proposal](01_context_ablation/cells/7b69390eef6b1f372ee3ade955f0affd7eec2489ed3e83779fb897cbdf228411/result.json).

5. **Only then test strategy selection or additional search.** The current
   lexical selector used eleven of eighteen cards; the seven unused cards have
   not been tested by this matrix. Compare a fixed small card budget with
   goal-aware selection, retaining version conditions and failed attempts in
   any evidence bank. Never attach a universal heartbeat price to a tactic.
   After a reliable proposal contract exists, a separate search-allocation test
   can compare two proposals with at most one repair each against one proposal
   with at most three repairs. Declare both the total generation-token budget
   and maximum requests: four permitted requests do not imply equal realized
   cost. Keep correctness-only debugging separate from any later score-guided
   optimization loop.

Both tracks can initially use the same harness-owned retrieval, patch
application, validation, and selection contract. This experiment does not yet
justify teaching a model a broad tool protocol. For open-model training, first
freeze the useful editing contract, then collect version-checked changed proofs
and local edit pairs from disjoint training material, including rejected
siblings. Incumbent copies can be labeled as valid recovery, but should not be
positive optimization targets. Evaluate SFT before adding GRPO; preserve
all-version gates and the actual combined-score objective so a shorter but
more expensive proof is not automatically rewarded. Closed-model prompting can
use the same examples and contract under a separately declared inference
budget. Training, example retrieval, and test-time score feedback remain future
interventions, rather than explanations of the current outcomes.
