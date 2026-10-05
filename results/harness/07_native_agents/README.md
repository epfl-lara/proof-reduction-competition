# Native provider pilots: partial results

These runs use the canonical revised V2 prompt, five strategy cards, source and
goal tools, score feedback, and deterministic cleanup at the beginning and end.
The declared warm-up cohort has 15 problems and 36 required version checks.
All scores below are local measurements against fixed original token counts and
cached references. Neither native provider completed its full cohort.

| Run | Successfully completed problems | Outcome |
| --- | ---: | --- |
| [DeepSeek V4.1 Flash/high](deepseek_flash/) | 0/15 | First pilot ended with a response-stream transport error |
| [Opus 5.5/max, corrected native tools](opus55_max_native_tools/) | 1/15 | Later calls hit the account session quota; run is paused |
| [Opus, initial restrictive pilot](opus55_max/) | 0/15 | Historical parser rejected recovered tool denials |

The earlier restrictive pilot and corrected pilot target the same theorem; they
are separate runs, not two completed problems. Per-run reports retain their last
saved bytes and may describe activity before interruption. This summary records
the final observed state. No full-cohort average is available for these providers.

## First theorem

`CallElimCorrect.substOldPostSubset` requires Lean v4.26.0. Both providers retained
proofs passing that version. DeepSeek's result remains incomplete because the
model did not emit a successful terminal response.

| Run | Length reduction | Heartbeat reduction | Compatibility | Combined score |
| --- | ---: | ---: | ---: | ---: |
| Saved deterministic seed | — | — | 100% | 37.406995% |
| DeepSeek, saved best proof | 67.092652% | 81.032854% | 100% | 82.708502% |
| Opus, completed corrected pilot | 80.830671% | 85.101874% | 100% | 88.644182% |

DeepSeek performed 113 host checks and accepted 16 improvements. Its native
session lasted approximately 8h35m. The last accepted improvement occurred after
about three hours; later work did not improve the score. The interrupted host
was reconnected to the existing native process, without resampling the request.
The final native error was `stream disconnected before completion: Transport
error: network error: error decoding response body`. The remaining 14 problems
were never launched. Its terminal usage and exact gateway price are unknown.

The corrected Opus pilot performed 53 host checks, including 50 agent checks,
and accepted 15 improvements. Its saved pilot audit passed. Fourteen subsequent
native calls ended with session-limit errors. Five other problems retain improved
verified proofs, but those runs are incomplete; five cells also lack completed
host postprocessing. The user's pause request remains in `pause.json` and has no
automatic resume.

## Pilot cost verification

The corrected Opus pilot reported **$13.2922668 API-equivalent**. Its raw terminal
record reports 323,521 output tokens, including 266,442 thinking tokens, 17,524,354
cache-read input tokens, 414,534 one-hour cache-write tokens and 176 ordinary input
tokens. At the [Anthropic rates](https://platform.claude.com/docs/en/about-claude/pricing)
verified on 2026-10-05, the independent calculation is:

| Component | Estimated USD |
| --- | ---: |
| All output, including reasoning once | 6.4704200 |
| Cache reads | 3.5048708 |
| One-hour cache writes | 3.3162720 |
| Ordinary input | 0.0007040 |
| Total | **13.2922668** |

This exactly matches the CLI estimate and exceeds the $3 per-problem cap. It is
not a subscription invoice. The [saved normalization](opus55_max_native_tools/usage_verification.json)
preserves the original terminal records. Historical generation records retain
their original normalization; the current API records cache duration and reported
thinking subsets and preserves usage even for failed terminal requests.

On this same theorem, Astra/max with cleanup used 19,487 output tokens and an
estimated $3.944580; its score was 87.127696%. Astra/max without cleanup used
33,191 output tokens and an estimated $8.690906; its score was 90.063364%.
These are separate runs with different search trajectories and unrestricted
budgets, not a comparison at a fixed cost.

## Preserved evidence and cleanup

Requests, raw events, host check ledgers, selected proofs, measurements and cleanup
jobs remain in their original directories. Source hashes resolve to archived
implementation snapshots; the auditor never executes those snapshots. Native
scratch work is archived locally under `.proof-eval/native-workspaces/` and ignored
by Git; successful terminal declarations remain tracked for auditing. Original
references and the measurement backend are unchanged.

The temporary `proof-reduction-native-dev` worktree was removed. Its four exact
unmerged changes are recoverable from local checkpoint `15bafa79`; the maintained
provider fixes are integrated in the main package. Cleanup launched no model
requests and did not resume either cohort. Budget and plateau stopping are future
experiments; the recorded runs retain their uncapped configuration.

The [cleanup validation](CLEANUP_VALIDATION.json) records the offline tests and
saved-evidence audits, with successful model completions counted separately from
examined terminal records.
