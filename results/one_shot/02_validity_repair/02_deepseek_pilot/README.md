# Correctness-only repair experiment

**complete**: 1/1 selected cells; 1 repair requests. At most 3 rounds per proposal.

This cohort is explicitly selected from saved one-shot cells. Its counts are not a full-benchmark score. Stop at the first proof passing all required versions; never return scores, length changes or heartbeat measurements to the debugger. An empty initial response is not regenerated. Final incumbent selection uses the combined score only after the loop ends.

| Model | Arm | Proof | Initial category | Rounds | Outcome | Returned incumbent | Accepted |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| deepseek-ai/DeepSeek-V4.1-Flash | plain | `fundamental_theorem_of_variational_calculus'` | compiler_repair | 1 | repair_returned_no_candidate | False | False |

Each cell preserves the initial result, per-round compiler feedback, exact messages, request-start markers, raw final output, and all-version evaluations. Reasoning text is not saved. Malformed nonempty outputs are labeled output recovery separately from compiler repair.
