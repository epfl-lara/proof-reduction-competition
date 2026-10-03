# Correctness-only debugger: engineering pilot findings

The bounded debugger repaired both tested Qwen compiler failures in one call.
Qwen3.5 returned a changed valid proof with a lower competition score; Qwen3.6
returned the incumbent unchanged. DeepSeek's correction exhausted the output
budget without final code. **No pilot candidate was accepted as an optimization
improvement.** These selected cases check harness behavior, not model rankings.

## Actual repair calls

| Model | Initial problem / arm | Correction calls | Final proposal | Incumbent score | Corrected score | Selected |
| --- | --- | ---: | --- | ---: | ---: | --- |
| Qwen3.5-397B-A17B | `CallElimCorrect.substOldPostSubset` / plain | 1 | Changed; all required versions pass | 37.407 | 36.154 | Incumbent |
| Qwen3.6-35B-A3B | `CallElimCorrect.substOldPostSubset` / goals | 1 | Incumbent returned; all versions pass | 37.407 | 37.407 | Incumbent |
| DeepSeek-V4.1-Flash | `fundamental_theorem_of_variational_calculus'` / plain | 1 | Empty final response after output-budget exhaustion | 43.462 | 0, invalid output | Incumbent |

Scores are local per-problem combined percentages. They are reported here after
the experiment; **none was sent to a debugger**. Qwen3.5 is the concrete check
that a valid but lower-scoring correction stops the loop immediately. The harness
then rejects it for submission without requesting another optimization attempt.

Qwen3.5 used 1,206 completion tokens (528 reasoning); Qwen3.6 used 4,413 (3,647
reasoning). DeepSeek used all 32,768 completion tokens as reasoning, with zero
final-content characters. Total additional usage across the three calls was
**11,697 prompt tokens and 38,387 completion tokens**, as reported by the provider.
The requests overlap other service traffic, so their durations are not a
controlled speed comparison.

Two additional saved DeepSeek cases exercised zero-call paths: an already-valid
but non-improving proposal stopped immediately, and an empty initial response was
recorded as no candidate. Neither was counted as a compiler repair. The two pilot
folders therefore contain five initial cells but only three additional requests.

## What this establishes

- Compiler feedback can repair a concrete failed proposal while preserving the
  rule that the model receives no candidate performance feedback.
- Passing Lean, returning an unchanged incumbent, and improving the competition
  score are separate outcomes. The artifact schema and reports retain all three.
- The larger token cap does not guarantee final code. An empty initial response
  has no proposal to debug; an empty repair response ends this protocol rather
  than silently starting a new optimization proposal.
- Up to three corrections is a budget, not a guarantee of a valid new proof.
  Failed repairs retain the already-verified incumbent for submission.

The [engineering pilot](01_engineering_pilot/README.md) and
[DeepSeek pilot](02_deepseek_pilot/README.md) retain full initial/round evidence.
Their [first audit](01_engineering_pilot/validation/repair_evidence_audit.json) and
[second audit](02_deepseek_pilot/validation/repair_evidence_audit.json) passed without
Lean execution or model requests. The audits reconstruct the exact feedback and
messages from the previous candidate, verify first-valid stopping, and check
post-loop acceptance and unchanged reference records.

The next comparison applies this fixed policy to every initial cell in the
context matrix, reusing these exact pilot outcomes. That paired result is needed
before deciding whether cards, goals or measured incumbent costs help after
correctness debugging. No score-guided replanning is added at this stage.
