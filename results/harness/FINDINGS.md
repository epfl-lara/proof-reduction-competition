# Findings from the staged harness experiments

This file records completed comparisons. The [live comparison](COMPARISON.md)
and per-stage reports show current progress. These are local warm-up scores;
the protocol changes were informed by earlier results on the same problems.

## Structural prompt and tools: Astra/low

All 15 declarations are complete. The revised harness scores **59.407773%**,
versus **57.222638%** with the previous original-proof harness: **+2.185135
percentage points**. Mean token reduction is **37.253605%**, heartbeat reduction
**40.969714%**, and compatibility **100%**. All 15 selected proofs improve on
their original; none require fallback to the original.

This is a modest mean improvement with large case-level swings. Using 0.05
points as the tie margin, it wins 9 cases, loses 5, and ties 1 against the
historical outputs. Old substitution gains 27.64 points, affine/tensor gaps
20.44, and old-variable extraction 17.50. Variational calculus loses 22.15,
SKI diamond 11.08, and polynomial folding 9.06. This is one generation per
case, so the comparison does not establish a reliable average causal effect.

Every case used the new named source tools. There were 56 search commands,
20 source reads, 26 agent checker calls, 15 completed Codex calls, and 34,216
reported completion tokens. Astra/low did not use the optional goal tool.
The source tools were exercised, but access and instructions alone did not
close the gap to the historical Astra/max score of 78.093430%.

## Score feedback

The next stage exposes the measured tuple after each attempt and lets the
agent continue beyond its first valid proof. Results remain pending here until
the corresponding conditions complete. Its trajectory analysis excludes gains
from merely falling back to the original after a worse valid proposal.

Evidence: [structural-stage results](01_structural_context/README.md),
[structural protocol](01_structural_context/PROTOCOL.md),
[per-problem comparison](per_problem.csv),
[score-search protocol](02_score_search/PROTOCOL.md).
