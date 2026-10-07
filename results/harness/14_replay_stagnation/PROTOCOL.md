# Phase 0: saved-evidence stopping-policy replay

Registered 2026-10-07 before any policy outcomes were computed. The associated
`protocol.json` is authoritative. This study reads host-owned saved evidence and
uses no model, Lean, semantic-search, or web calls during replay.

The primary cohort is stage 10, Sol 6.1/max, all 15 declared problems. Stages 06
and 08 are separate 15-problem single-attempt robustness cohorts. Stages 09, 11,
and completed stage 12 cells are descriptive only, kept separate by run and
condition. Stage 13 and all active runs are excluded. Partial descriptive
cohorts have subset statistics, never full-cohort means.

## Fixed policies and decision semantics

Identity; stagnation X in {3,4,5,6,8,10,12,15,20} minutes; stagnation with the same
X and individual-gain reset threshold delta in {0.25,0.5} percentage points;
and attempt caps in {1,2,3,4}. Only plain stagnation feeds the gate.

Decisions occur **after** each completed check and at attempt end, as in the
supplied plan. A completed accepted check updates the incumbent before the
decision. There is no invented timer observation between host events. Thus X
is an event-observed threshold, not an exact-time watchdog. Small accepted
gains still update the best proof even when they do not reset the delta clock.
The policy receives immutable prefix summaries, never future outcomes.

A cut with later accepted checks breaks recorded continuation support, including
in the last attempt. No subsequent attempt is revealed. Otherwise the next
attempt is revealed only when its saved parent proof SHA matches. Its recorded
inter-attempt gap is preserved and its recorded duration/outcomes are shifted
earlier. No gain or duration beyond recorded support is invented. This splice
assumes unchanged within-attempt behavior despite different remaining-time
prompts, so it is an offline sensitivity analysis, not a causal estimate.

Raw score means the accepted incumbent before final deterministic cleanup;
cleanup checks are excluded. Identity must equal every saved raw score and, for
stage 10, every first-attempt and per-attempt score in comparison.json, within
1e-9. Any identity mismatch aborts the report. Historical single-attempt runs
retain their recorded deadline (including no deadline), rather than imposing a
new 57-minute cap. Started attempts cut by a saved controlled deadline may use
that deadline as a censored end; the basis is recorded. Other missing terminal
evidence is excluded explicitly. Sources with malformed identities are errors.

Freed time is the reduction in recorded raw-search finish time, including
preserved admission gaps and excluding final cleanup. Unspent time is remaining
recorded deadline time, reported separately. Unknown cost stays unknown. Known
attempt cost is interpolated linearly in retained duration only as a secondary
model estimate; this has **no guaranteed direction of bias** without turn-level
usage. Cost estimates do not enter the gate.

## Pre-registered gate and selection

GO only when one plain stagnation X meets all these conditions:

1. The complete 15/15 stage-10 cohort loaded and identity validated.
2. At least 12/15 problems remain fully on recorded continuation support.
3. Mean raw-score loss is at most 0.10 percentage points.
4. Mean freed time is at least 8 minutes per problem.
5. Estimated reinvestment value is at least twice the mean lost score.
6. The same X loses at most 0.10 pp separately on complete stages 06 and 08.
7. Every leave-one-problem-out selection chooses within one grid index of X.

Reinvestment is freed minutes times the median raw gain/minute of **all**
recorded restart attempts (index >=1), including zero-yield attempts. It is a
model-based estimate, not discovered improvement. If no restarts are observed,
the estimate is unknown and cannot pass. Eligible X values are ranked by most
mean freed time, then smaller score loss, then larger X. Leave-one-out selection
removes the held-out theorem from primary and robustness cohorts and recomputes
the median yield without it; support requires ceil(0.8 * retained problems).
No eligible X or a missing fold selection fails stability. Otherwise NO-GO.

## Outputs and checks

`report.json`, `per_problem.csv`, `anytime.csv` (one-minute grid), `gaps.csv`, and
`README.md`, with byte fingerprints of every consulted input and replay source.
Hazard summaries count once per attempt/threshold at the first observed
stagnation decision event and measure subsequent accepted gains. Separate
descriptive gap and restart-yield statistics retain their condition and scope.

Required validation: synthetic support, deadline, prefix-only observation,
unknown-cost, and output-boundary contracts; actual saved identity checks;
one-problem pilot before full replay; two ledger spot checks; formatting, lint,
and full offline suite. No historic evidence or pinned runtime is modified.

This is a narrow adaptation of [Dream-RSI](https://www.dream-rsi.com/assets/dream-rsi.pdf),
sections 3.1-3.2 (pages 5-6), whose offline simulator reveals only recorded
children. Our sequential evidence does not evaluate unrecorded branching or
reproduce the paper's online recursive learning loop. Phase 1 is not authorized
or launched by this study.
