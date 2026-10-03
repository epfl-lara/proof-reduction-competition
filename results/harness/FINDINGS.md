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

## Structural prompt and tools: Luna/max

All 15 declarations are complete. The revised harness scores **52.740977%**,
versus **53.045428%** previously: **−0.304451 points**. Mean token reduction is
**11.625908%**, heartbeat reduction **46.597023%**, and compatibility **100%**.
There are 4 wins, 9 losses and 2 ties against historical outputs using the same
0.05-point margin. Thirteen selected proofs improve the original; two fall back
to it after valid but regressive proposals. There were 57 agent checker calls,
15 completed Codex calls, and 215,580 reported completion tokens.

Luna's heartbeat reduction improves on the historical 42.02%, but its token
reduction falls from 17.11%. Thus the new structural instructions sometimes
trade additional source for less elaboration without improving the combined
objective. A valid rewrite alone does not tell the model whether that trade
paid off. The first old-substitution pilot illustrates the issue: its valid
528-token rewrite scored −51.94%, and selection correctly retained the original
at 33.33%.

These results do not support adopting the prompt/bank/tool bundle as a broad
improvement yet. The score-feedback experiment tests the next hypothesis:
whether models can use measured tradeoffs to revise a valid but weak proposal.
The full structural-stage evidence audit passed for 30 completed cells,
104 saved checker records and 269 saved version outcomes. No references were
remeasured for that audit.

## Score feedback

The next stage exposes the measured tuple after each attempt and lets the
agent continue beyond its first valid proof. Results remain pending here until
the corresponding conditions complete. All three requested model settings
have started the score-search pilot. Its trajectory analysis excludes gains
from merely falling back to the original after a worse valid proposal.

The [21:14 UTC pilot snapshot](02_score_search/pilot_snapshots/2026-10-03T21-14-33Z.json)
already demonstrates post-valid optimization on `substOldPostSubset`:
Astra/max improved from a first-valid **51.175129%** to **78.248859%**, and
Astra/low from **71.774992%** to **75.519306%**. The low-effort cell completed;
the other searches were still running at the snapshot. This is one theorem,
not a full-condition score or an isolated causal estimate of feedback. Rejected
regressions and the accepted sequence are preserved in that snapshot.

Evidence: [structural-stage results](01_structural_context/README.md),
[structural protocol](01_structural_context/PROTOCOL.md),
[per-problem comparison](per_problem.csv),
[score-search protocol](02_score_search/PROTOCOL.md).
