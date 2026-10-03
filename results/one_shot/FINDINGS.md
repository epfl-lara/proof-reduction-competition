# Model experiments: findings and next decisions

These are local warm-up results, not new official arena grades. The fixed
deterministic starting point is **46.248122%** locally; the user's official
deterministic submission scored **46.34%**. Do not mix those denominators.

## Completed RCP conditions

All five conditions for DeepSeek-V4.1-Flash and Qwen3.6-35B-A3B are complete.
The Qwen3.5 continuation remains separate and unfinished at this snapshot.
The following table chooses the best completed arm per model after observing
the warm-up; it is not a held-out model ranking or a pooled proof portfolio.

| Setup | Arm | Combined score | Gain over deterministic control |
| --- | --- | ---: | ---: |
| Deterministic D0 and repeated-cleanup control D1 | — | 46.248122% | — |
| DeepSeek + validity repair + deterministic cleanup | cards | 48.656864% | +2.408742 pp |
| Qwen3.6-35B + validity repair + deterministic cleanup | plain | 46.396101% | +0.147979 pp |

The strongest DeepSeek arm gains another **0.186763 pp** from cleanup beyond its
model/repair selection. Its total gain is concentrated in two Putnam problems,
so this does not establish a broad average benefit from strategy cards. The
[full condition and per-problem report](06_parallel_continuation/04_combined_deterministic/README.md)
keeps every arm separate, including controls and failures.

DeepSeek's initial delivery problem is substantial: **60/75 initial responses
had no final proof**. Repair cannot debug an absent proposal. Across its five arms,
valid outputs increased from 3 to 11 with repair, and six final proposals were
accepted. These counts describe different outcomes: delivery, validity and
improvement. Small-Qwen validity also includes unchanged incumbent returns;
counting them as optimization successes would overstate progress.

## Codex tools produce a different result

The requested Astra/max baseline keeps tools enabled for source inspection and
Lean correctness checks. Its [live audited report](09_codex_tools_baselines/README.md)
compares original and deterministic starting proofs with the same `cards` prompt.
The pure arm has no deterministic transforms. The other arm includes cleanup.
Luna/max, high and medium follow under the same setup.

The first paired theorem, `CallElimCorrect.substOldPostSubset`, illustrates a
substantial structural rewrite:

| Stage | Tokens | Combined score |
| --- | ---: | ---: |
| Original reference | 313 | 33.333333% |
| Deterministic D0 | 303 | 37.406995% |
| Astra from original | 223 | 64.744686% |
| Astra from D0, before cleanup | 192 | 70.836929% |
| Astra from D0, after cleanup | 143 | 74.487866% |

Both model proofs factor repeated list-subset reasoning into a local `join`
lemma. Source inspection found the relevant library definitions and lemmas;
compiler feedback corrected errors. Neither needed an outer repair call, but
each used two model-side validity checks. This is not first-try compiler success.

On the next theorem, the pure result **73.224553%** beats the combined result
**62.002346%**, versus D0 **37.395598%**. Deterministic seeding is not uniformly
better. Keep the branches independent rather than combining the best of both
and calling it a single-sample baseline. The live report masks incomplete means.

These gains are evidence that the evaluator and selection path can recognize
large improvements. They do not identify whether the model, source access,
in-turn debugging, or inference budget explains the difference from RCP.
Codex does not enforce the RCP study's exact 32K output cap or temperature.

## Delivery and timing diagnosis

Qwen3.8 is **on hold at the user's request**. Its stopped high cohort has 47
saved empty capped responses and two unknown interrupted requests. The later
medium probe again returned no proof after all 32,768 output tokens were reported
as reasoning. No more Qwen3.8 work is scheduled.

The medium probe spent 7.7 minutes queued locally and 7.6 minutes admitted to HTTP.
The inherited RCP key also differed from the repo file in the current shell;
new launches explicitly use `.env`, while historical worker credentials are
unverified. See [credential and timing evidence](RCP_CREDENTIALS_AND_TIMING.md).
Do not infer hardware/model speed from summed request elapsed time.

## Next decisions, in order

1. Finish the Astra original/combined comparison and the matched Luna effort
   settings. Compare absolute score, all-version validity, changed proofs,
   tool/compiler calls and reported usage. Do not infer significance from a
   single proof or from gains over different starting baselines.
2. If the tools-enabled path remains effective, give one RCP model the same
   source-lookup and correctness tools in a separate controlled test. This is a
   more direct diagnosis than adding more generic prompt text. Keep the score
   objective, starting proofs and reference denominators fixed.
3. Test a small, specific bank addition for structural rewrites: factor repeated
   induction-branch reasoning into a local helper, or replace a long argument
   with an existing lemma found in the pinned project. Keep these post-hoc
   warm-up observations outside the bank used for the current experiment.
4. Compare repair budgets using the saved trajectories before spending more
   model calls. The existing replay separates validity recovery from score gain;
   a universal two-round limit is premature because Qwen3.5 has a round-three win.
5. Keep candidate score feedback and optimization search for the next stage.
   The present loop only supplies correctness feedback. Training should target
   the working interface after delivery and tool behavior are measured.

Tactic costs remain conditional on goal, context, elaboration and Lean version.
The `join` cleanup trades some heartbeat reduction for a larger token saving;
the competition's combined objective accepts that trade. A bank should record
the verified context and score components, not a universal price for `grind`
or `simp`.
