# Deterministic seed and final cleanup

Question: does deterministic preprocessing and final cleanup improve the revised
score-feedback harness? Compare each complete 15-problem condition against the
same model/effort's completed [stage 02](../02_score_search/README.md).

Models: `gpt-6-astra/max`, `gpt-6-astra/low`, `gpt-6-luna/max`; **45 cells**.
The revised system prompt, five generic strategy cards, source/goal tools and
score-feedback loop remain the same. Models choose when to stop; there is no
imposed total attempt, output-token or wall-time cap. Provider limits and the
existing per-Lean-check timeout still apply.

1. Select the better all-version-valid original or saved deterministic D0 proof.
   D0 comes from the completed deterministic study stored in the stage-01 input
   packs. Reusing it is the initial deterministic step; neither references nor
   D0 are recomputed. No previous model solution is supplied.
2. Run score search. The agent receives compiler diagnostics, component scores,
   combined score and its saved best after each proposed change. No deterministic
   tool is available during this mode's search.
3. Apply one fixed cleanup pass to the saved best after the agent stops. Retain
   the better eligible proof; a regressive cleanup cannot displace the input.

The runtime cleanup reuses `run_combined_matrix.cleanup_proof`: ordered methods
`lint, simp, wrappers, facts, reuse, menu, search, simp_min, arith_min, rw_min`;
each method has at most 3 rounds, 32 trials and 6 sites. This is one bounded
portfolio pass, whereas the historical D0 was built by the earlier deterministic
experiments. They are distinct stages, not equal-compute applications.

All length/heartbeat denominators stay tied to the original reference. Cached
local synchronous heartbeats and pinned Lean versions are unchanged. Accept
only proofs passing every required version and improving the combined score by
more than 0.05 percentage points. Selection never regresses the current best.

Both new placements share the exact initial seed, cleanup implementation/budget,
and proof/provenance-keyed job cache. The controller completes the first theorem
for all three models in both modes before expanding to the full cohort. Started
model calls are not resampled on resume. Incomplete compiler, provider or cleanup
outcomes remain marked incomplete; full means require all 15 cells complete.

Save inputs, requests, raw tool checks, cleanup jobs, selected proof and score
trajectory. Report gain over stage 02, model-proposal gains, final-cleanup gains,
completion tokens and cleanup work. Keep independent-generation comparisons
separate from within-trajectory improvements; neither comparison is budget
matched or held-out evidence. Export submission JSONL for each completed model.

```bash
python src/continue_agent_harness.py --suite deterministic --workers 5
python src/summarize_agent_harness.py --watch --suite deterministic
python src/audit_agent_harness.py results/harness/03_deterministic_edges
```
