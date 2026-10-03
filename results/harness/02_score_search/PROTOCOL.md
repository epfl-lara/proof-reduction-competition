# Iterative search with competition-score feedback

Predeclared matrix: **15 warm-up declarations × Astra/max, Astra/low and
Luna/max = 45 cells**, all starting from original proofs. The system/user task
messages and structural bank match stage 01 exactly. The tool-mode instructions
change: performance becomes visible, and a valid proof is no longer a stopping
condition. Neither stage applies deterministic optimization.

## Agent tools

Each `python tools.py check candidate.lean` call uses the existing pinned Lean
evaluator and returns:

```json
{
  "score_tuple_order": ["length_reduction_pct", "heartbeat_reduction_pct", "compatibility_pct"],
  "score_tuple": [40.0, 80.0, 100.0],
  "total_score": 73.33333333333333,
  "passing_rate_pct": 100.0,
  "all_versions_passed": true,
  "accepted_as_best": true,
  "delta_from_previous_best_pp": 5.0,
  "best_scores": {"combined_pct": 73.33333333333333},
  "best_proof": "..."
}
```

This is an illustrative schema fragment, not an experimental result. Actual
responses also provide version-specific correctness feedback, candidate token
count and primary heartbeats. A primary failure gates competition components
and total to zero, while `passing_rate_pct` still shows the actual fraction of
versions that passed. Unavailable measurements remain null, not fabricated zero.
The local heartbeat measure uses `Elab.async=false`; time is not the reward.

The host preserves the best proof passing **every** required version. A candidate
must improve the total by more than the existing 0.05-point margin to replace
it. Regressions, invalid outputs, partial compatibility and duplicates are
recorded but cannot overwrite a better verified proof. This retains the earlier
selection policy even when a partially compatible proof has a numerical score.

`python tools.py status` retrieves the best proof and tuple. The agent can
inspect source or goals, propose another proof, debug it and compare again.
`finish --reason '...'` records the agent's short factual stopping reason.
Final source text is checked by the harness too; the selected output is always
the host's best checked proof, even if the final text regresses or a call fails.

## Budget and stopping

There is **no imposed total number of attempts, output tokens, or wall-time
budget**. The agent continues while it has promising changes and stops when it
judges further progress unlikely. There is no fixed “two failures then stop”
rule and no automated early stop after the first valid or worse result.
The provider still has its own limits, and the existing per-candidate Lean
timeout remains unchanged so reference/environment identity is preserved.

A completed Codex final ends the search even if the agent omitted `finish`;
that omission is recorded. In-turn tools retain the conversation, so repeated
fresh model calls are not needed merely to supply scores. Provider errors or
process interruptions are incomplete outcomes, not claims of convergence.
The ledger preserves already verified improvements; started requests are never
silently resampled.

## Comparisons and reporting

For Astra/low and Luna/max, compare full means against stage 01 and against
historical original-arm controls. This measures the combined benefit of score
feedback and additional inference, not a budget-matched causal effect of seeing
a number. Astra/max compares against its historical **78.093430%** original
arm; without an additional new-prompt correctness-only Astra/max cohort, that
difference also mixes prompt/tool changes with iterative search.

Each cell records its first valid proposal, final selected proof, every attempted
score tuple, accepted improvements, tool checks, model usage and stopping reason.
The saved `score_gain_after_first_valid_pp` is the raw difference between final
selection and the first valid proposal; it can include fallback to the already
valid original if that proposal is worse. To measure gains from continued
search, compare the final best score to the ledger's best score immediately
after the first changed valid proposal, excluding checks of the original. The
[comparison script](../../../src/summarize_agent_harness.py) performs this
calculation. Score feedback may also influence how that first
result is reached. Pilot results remain part of the full cohort. Reports mask incomplete
condition means and never pool across models. No submission is sent automatically.

This is warm-up exploration. The generic bank is informed by previous warm-up
results, so generalization requires a later held-out check. Local score feedback
is an optimization signal, not a guarantee of the official arena score.
