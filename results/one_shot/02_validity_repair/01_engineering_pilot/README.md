# Correctness-only repair experiment

**complete**: 4/4 selected cells; 2 repair requests. At most 3 rounds per proposal.

This cohort is explicitly selected from saved one-shot cells. Its counts are not a full-benchmark score. Stop at the first proof passing all required versions; never return scores, length changes or heartbeat measurements to the debugger. An empty initial response is not regenerated. Final incumbent selection uses the combined score only after the loop ends.

| Model | Arm | Proof | Initial category | Rounds | Outcome | Returned incumbent | Accepted |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| deepseek-ai/DeepSeek-V4.1-Flash | cards | `CallElimCorrect.extractedOldExprInVars` | already_valid | 0 | already_valid | False | False |
| Qwen/Qwen3.5-397B-A17B | plain | `CallElimCorrect.substOldPostSubset` | compiler_repair | 1 | repaired_valid | False | False |
| Qwen/Qwen3.6-35B-A3B | goals | `CallElimCorrect.substOldPostSubset` | compiler_repair | 1 | repaired_valid | True | False |
| deepseek-ai/DeepSeek-V4.1-Flash | plain | `CallElimCorrect.substOldPostSubset` | no_candidate | 0 | no_candidate | False | False |

Each cell preserves the initial result, per-round compiler feedback, exact messages, request-start markers, raw final output, and all-version evaluations. Reasoning text is not saved. Malformed nonempty outputs are labeled output recovery separately from compiler repair.
