# Deterministic optimization combined with model proposals

Declared on 2026-10-03 after the user requested an explicit combined test. The
initial context experiment already starts from the archived deterministic
incumbents: all fifteen saved input proofs match
[selected_candidates.jsonl](../../deterministic/selected_candidates.jsonl)
byte-for-byte. This extension tests whether another deterministic pass can
improve the model's first valid proposal. It introduces no model requests.

The cohort remains the same 225 model × context × theorem cells from
[stage 03](../03_repaired_context_ablation/PROTOCOL.md). Each cell retains its
original optimization request and at most three correctness-only repair calls.
Neither deterministic outcomes nor competition scores go back to the model.
The stage was chosen after observing partial earlier results, so it is an
exploratory extension, not a preregistered independent confirmation.

## Comparisons

For each theorem, retain the original deterministic incumbent **D0** and run an
additional bounded deterministic cleanup to obtain **D1**. This control gives
every theorem the extra cleanup opportunity, regardless of model outcomes.

For each cell, retain stage 03's selected proof **L** and its first
all-version-valid final proposal **F**, when one exists. Run the same cleanup on
F even if stage 03 rejected its score. This allows deterministic simplification
to rescue a valid but initially inferior rewrite. Empty, invalid, or unavailable
final proposals receive no deterministic optimization; their combined selection
falls back to the completed D1 control.

The combined output **H** selects the highest-scoring eligible all-version-valid
proof from D1, L, and cleaned F. New improvements must exceed D0 by the existing
0.05 percentage-point margin. D0 itself remains an eligible fallback. Prefer the
control on an exact score tie. Selection must preserve the earlier valid L;
small differences between eligible alternatives must not cause a regression.

Report D0, D1, L, H separately. **H − D1** measures the added value of the model
branch beyond the extra deterministic control pass. **H − L** measures the gain
from adding deterministic cleanup and its control fallback. Also report the
number of initially inferior valid proposals rescued by cleanup.

## Fixed cleanup

Use the existing deterministic methods in this order: `lint`, `simp`, `wrappers`,
`facts`, `reuse`, `menu`, `search`, `simp_min`, `arith_min`, `rw_min`. Run one pass,
with no portfolio repeat sweep. Each method has at most three rounds, 32 candidate
trials, and six discovery sites per site batch, with the existing 0.05-point
improvement margin. These are bounded searches, not a fixed point or a total
wall-time cap.

Require every accepted transition to pass the theorem's exact listed version
set. The earlier general deterministic engine permits compatibility tradeoffs;
this experiment adds an explicit all-version eligibility gate while preserving
the raw compiler evidence and numerical scores. Gate rejection must not be
reported as a compiler failure. Unavailable discovery is an incomplete cleanup,
not evidence that no improvement exists.

References are read from the unchanged local cache. There is no reference
measurement, environment update, new tactic family, model training, additional
model sampling, or score-guided model loop.

## Accounting and evidence

Deduplicate identical `(theorem, proof bytes)` cleanup jobs across controls and
model cells. Store every cell's link to its physical cleanup job and distinguish
logical uses from actual trials, Lean checks, cache hits and elapsed work.
Control plus proposal cleanup can use more total compute than the control alone;
this is not an equal-total-compute comparison. Reusing an identical proof's
cleanup is not an additional model sample.

Preserve method checkpoints, candidate edits, evaluations and rejection reasons,
input/result hashes, implementation hashes, budgets and unchanged-reference
checks. Keep the first three experiment directories immutable apart from their
ordinary reports. Stage 04 results belong here.

Full means and submission exports require every theorem in the corresponding
fifteen-problem condition and its control to finish. Partial snapshots expose
their denominators. Do not pool the best proposals across models or context
conditions. Retain the original one-draw, small-warm-up limitations.
