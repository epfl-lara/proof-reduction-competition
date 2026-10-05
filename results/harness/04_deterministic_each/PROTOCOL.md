# Deterministic cleanup during score search

Question: does exposing deterministic cleanup during the agent's search improve
over using it only at the edges? Use the exact seeds, models, methods, cleanup
budget, reference denominators, acceptance rule and stopping policy from
[stage 03](../03_deterministic_edges/PROTOCOL.md): **45 new cells**, covering
`gpt-6-astra/max`, `gpt-6-astra/low`, and `gpt-6-luna/max` on all 15 problems.

The only placement change is an additional host tool:

```bash
python tools.py deterministic candidate.lean
```

After each changed proposal passes every required version, the agent is told to
call this tool before its next rewrite. It returns raw and cleaned scores, the
cleaned declaration, gain over the input, and the best proof seen so far. Invalid
input receives correctness feedback and skips cleanup. The host retains a
valid raw improvement even when its cleanup does not improve it. The agent can
continue from whichever proof scores best; final output is also protected by
host selection and final cleanup.

The tool runs the same fixed portfolio as final cleanup. It does not run another
model. Repeated normalized proofs share cached jobs across placements/models;
only identical input proofs with matching frozen provenance can share a result.
All proofs accepted inside a job must pass the complete required version set.
Every raw attempt and cleanup output is preserved separately.

This is agent-requested cleanup, not forced interception of every check. Report
actual tool calls and the fraction of unique changed valid proposals sent for
cleanup, including zero or partial compliance. The three-model pilot must
exercise the tool before expanding; no completed pilot request is resampled.
Keep selected proofs on incomplete runs, but do not report their means as
completed benchmark results.

Compare with both stage 02 (score loop without deterministic work) and stage 03
(same deterministic seed/final cleanup). Partition the monotone best-score
trajectory into model-proposal, in-loop cleanup and final-cleanup gains. This
accounting is descriptive: earlier deterministic changes can affect later
model proposals. Report tokens, tool usage and unique cleanup work as well as
score; independent generations are not equal-compute causal comparisons.

```bash
python src/run_agent_harness.py --mode score_each --workers 5
python src/audit_agent_harness.py results/harness/04_deterministic_each
```
