# Findings from the staged harness experiments

This file records completed comparisons. The [live comparison](COMPARISON.md)
and per-stage reports show current progress. These are local warm-up scores;
the protocol changes were informed by earlier results on the same problems.

## Current decision and model-configuration study

Stage 05 is now **complete: 30/30 cells**, audited on 5 October 2026. Sol 6.1/max
is the strongest completed score-search configuration with all 15 recorded
API-equivalent problem costs below $3. Its ready-to-upload
[proof JSONL](05_model_config/conditions/gpt-6.1-sol__max/selected_candidates.jsonl)
and [submission manifest](05_model_config/conditions/gpt-6.1-sol__max/submission_manifest.json)
preserve the selected proofs and their provenance.

| Model / effort | Local combined score | Length reduction | Heartbeat reduction | Compatibility | Mean USD / problem | Maximum USD / problem | Over $3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Sol 6.1/max | 87.342215% | 76.399921% | 85.626723% | 100% | 0.987643 | 1.672598 | 0/15 |
| Astra/high | 84.319957% | 71.577926% | 81.381946% | 100% | 1.926246 | 3.543124 | 3/15 |

With the same beginning/end setup, Sol is 0.700964 percentage points below
Astra/max (88.043179%) and 8.223906 points above Astra/low (79.118309%). It scores
3.022258 points above Astra/high while costing about half as much at the recorded
rates. Astra/high exceeds the $3 cap on the unique-decoding-radius, polynomial
folding and affine/tensor-gaps problems. This remains a single warm-up run per
condition, not a repeated or held-out comparison.

Sol made 343 agent checker calls and used 439,344 output tokens, including
reasoning. Final cleanup added 0.038737 points on average. Astra/high made 171
agent checker calls, used 108,264 output tokens, and gained 0.129709 points from
final cleanup. The study audit checked 604 saved checks, 2,615 version outcomes,
30 model requests and 30 cleanup jobs.

The exact Sol JSONL contains 15 distinct benchmark IDs and matches the selected
proofs for all 36 required problem/version checks. The current arena revision
and dataset match the saved snapshot. File size, full statements, JSONL schema
and every public intake forbidden pattern were checked; no new reference
measurements or model calls were needed. The file is prepared for organizer
grading and has not been uploaded by this preparation. Dollar values below and
above are Standard, short-context API-equivalent estimates, not Codex invoices
or certified future replay costs.

Stages 03 and 04 are complete and audited: 90/90 cells. Beginning/end cleanup
is now the default, and in-loop cleanup is removed from the runnable harness
and agent tools. Its historical artifacts and content-addressed implementation
snapshots remain auditable. Refactoring is paused until selecting a model.

The [stage-05 protocol](05_model_config/PROTOCOL.md) tests Sol 6.1/max and Astra/high
with the same beginning/end setup, fixed cached references and revised score
feedback. It estimates costs before measurements and records API-equivalent
costs from each completed run's token counters. No additional budget stopping
rule is imposed in this comparison. A pilot for both models precedes expansion
to 30 cells; pilot outputs are reused.

The final completed placement costs below supersede the partial snapshot later
in this file. Assumptions: Standard API list rates, short context per underlying
request, reported cache counters, no regional premium. These are not Codex
invoices or certified future API replay costs. The $3 cap applies per problem.

| Placement | Model / effort | Score | Mean USD / problem | Maximum USD / problem | Problems over $3 |
| --- | --- | ---: | ---: | ---: | ---: |
| Beginning/end | Astra/max | 88.043179% | 5.151091 | 7.935048 | 15/15 |
| Beginning/end | Astra/low | 79.118309% | 0.929707 | 2.156566 | 0/15 |
| Beginning/end | Luna/max | 68.264239% | 0.090727 | 0.244687 | 0/15 |
| In-loop, retired | Astra/max | 86.977844% | 7.431051 | 11.397110 | 15/15 |
| In-loop, retired | Astra/low | 75.301134% | 1.969864 | 4.037396 | 3/15 |
| In-loop, retired | Luna/max | 61.320048% | 0.124064 | 0.366331 | 0/15 |

The complete in-loop cohort costs more and scores lower for every model in this
single warm-up comparison. Beginning/end differs from score-only Astra/max by
−0.341227 percentage points; repeated trials would be needed to measure noise.
All selected proofs have 100% compatibility.

Pre-run Sol 6.1 scenarios: repricing Astra/max's stage-03 usage gives a $0.729594
mean and $1.069493 maximum. Repricing Luna/max's longer traces gives $1.316902
mean and $3.384100 maximum, with one over-cap problem. These do not predict Sol's
usage or score; actual new-condition results must decide. Astra/high is likewise
unmeasured at launch. The [cost snapshot](05_model_config/cost_estimate.json)
contains all scenarios and pinned source hashes.

Validation before stage 05: 516 offline tests and 102 subtests passed (three
live RCP tests excluded), followed by nine targeted runner/resume checks for
the new model conditions and missing historical controls. The installed Codex
CLI sends the exact requested models and reasoning efforts in localhost tests.
Evidence audits passed all 165 completed cells across stages 01–04 without new
Lean measurements or model calls.

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

These results do not establish a broad improvement from the prompt/bank/tool
bundle alone. We retain the revised setup as requested and use the completed
score-feedback experiment to test measured revision of valid proposals.
The full structural-stage evidence audit passed for 30 completed cells,
104 saved checker records and 269 saved version outcomes. No references were
remeasured for that audit.

## Score feedback

All **45 cells** completed, with 100% compatibility for every selected proof.

| Model / effort | Score | Change from historical original arm | Change from revised correctness-only | Mean gain after first changed valid proposal |
| --- | ---: | ---: | ---: | ---: |
| Astra / max | 88.384406% | +10.290976 pp | No matched stage-01 control | +12.267598 pp |
| Astra / low | 78.130010% | +20.907372 pp | +18.722237 pp | +11.649248 pp |
| Luna / max | 65.135096% | +12.089668 pp | +12.394120 pp | +14.835491 pp |

Every selected proof improved its original and its corresponding historical
output; every cell found improvement after its first changed valid proposal.
The within-trajectory calculation uses the best available score at that point,
so returning to the original after a regression does not count as search gain.

Agent checker calls were 286 / 116 / 466 for Astra/max, Astra/low and Luna/max;
reported completion tokens were 339,648 / 61,335 / 630,496, including reasoning.
This study adds both feedback and inference, so it does not isolate the causal
effect of score feedback at equal compute. It does show that the harness can
find substantial additional improvements beyond the first valid proposal.

The saved-evidence audit passed: 45 cells, 913 checks, 1,578 saved version
outcomes and 45 CLI requests. No references were remeasured by the audit.

## Deterministic placement experiments

Stages [03](03_deterministic_edges/PROTOCOL.md) and
[04](04_deterministic_each/PROTOCOL.md) add deterministic work to this same
revised score loop, testing all three model settings again. Both begin from the
better original/D0 proof and finish with fixed deterministic cleanup. Stage 04
also exposes that cleanup as an in-loop tool. The existing score-only runs stay
fixed as controls. Results will appear in [COMPARISON.md](COMPARISON.md); no
combined-mode improvement is claimed before those runs complete.

The historical [pilot snapshot](02_score_search/pilot_snapshots/2026-10-03T21-14-33Z.json)
shows post-valid optimization on `substOldPostSubset`:
Astra/max improved from a first-valid **51.175129%** to **78.248859%**, and
Astra/low from **71.774992%** to **75.519306%**. The low-effort cell completed;
the other searches were still running at the snapshot. This is one theorem,
not a full-condition score or an isolated causal estimate of feedback. Rejected
regressions and the accepted sequence are preserved in that snapshot.

Evidence: [structural-stage results](01_structural_context/README.md),
[structural protocol](01_structural_context/PROTOCOL.md),
[per-problem comparison](per_problem.csv),
[score-search protocol](02_score_search/PROTOCOL.md).

## Cleanup timing and parallel scheduling

The first theorem completed in both modes before full expansion. Its three
in-loop pilots give the following timing breakdown; these are single-problem
measurements, not full-benchmark averages.

| Model / effort | Total wall time | In-loop cleanup | Final cleanup | Cleanup share | Fresh candidate/version checks in unique cleanup jobs |
| --- | ---: | ---: | ---: | ---: | ---: |
| gpt-6-astra / max | 32.5 min | 26.2 min | 0.0 min | 80.6% | 268 |
| gpt-6-astra / low | 10.6 min | 6.2 min | 2.5 min | 82.2% | 86 |
| gpt-6-luna / max | 31.3 min | 15.1 min | 4.0 min | 61.0% | 195 |

Cleanup time is measured from the host tool ledger: input-check start through
cleanup completion. It includes Lean analysis, candidate verification,
measurements and host overhead. The repeated final cached job contributes
only its actual lookup time; historical job elapsed time is not charged twice.
Total wall time spans the first saved request start to cell completion.

Most costly methods were `menu`, `search` and `simp_min` (plus `simp` for
Luna). Their many candidate checks require fresh Lean elaboration and heartbeat
measurement. This identifies verification-heavy search as the main cleanup
cost; the current logs do not isolate Python text rewriting from every other
kind of overhead. Cached reference proofs are never remeasured.

At 17:08 CEST on 4 October, the controller was handed over without stopping
its existing runner or model requests. Both full cohorts now run concurrently
with five workers each, for ten active cells at most. Both pilot audits had
already passed. This changes scheduling only: frozen prompts, cleanup budgets,
scoring, reference records and proof selection remain identical. The handoff
is recorded in `deterministic_controller.json`. Two targeted controller tests
cover process-identity checks, terminal-state handling, parallel cohort launch
after both pilots, and resume without relaunching completed stages.

## Token-price estimate

Snapshot: 2026-10-04 19:51 CEST. USD token-value estimates from completed cells only.
These are not invoices: every request used `existing_codex_login`. The
calculation applies Standard API short-context rates to recorded Codex usage.
Included subscription usage, purchased credits and negotiated billing can differ.

Official rates per million tokens:

| Model | Ordinary input | Cached input | Cache write | Output, including reasoning |
| --- | ---: | ---: | ---: | ---: |
| GPT-6 Astra | $10 | $1 | $12.50 | $50 |
| GPT-6 Luna | $0.10 | $0.01 | $0.125 | $0.50 |

Sources: [Astra](https://developers.openai.com/api/docs/models/gpt-6-astra),
[Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[cache accounting](https://developers.openai.com/api/docs/guides/prompt-caching),
[Codex billing](https://learn.chatgpt.com/docs/pricing). Checked on 4 October 2026.

`ordinary_input = input_tokens - cached_input_tokens - cache_write_input_tokens`.
Multiply the four disjoint token classes by their rates and divide by one
million. Reasoning tokens are already in output tokens and are not added again.
All raw usage objects in this snapshot report zero cache-write tokens; Codex
credit billing has no separate cache-write charge. An API replay may create
billable writes, so the recorded zero is not an API replay guarantee.

| Stage | Model / effort | Completed | Input M | Cached M | Output M | Standard token value | Per completed problem |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 02_score_search | gpt-6-astra / max | 15/15 | 46.654208 | 45.135360 | 0.339648 | $77.3062 | $5.1537 |
| 02_score_search | gpt-6-astra / low | 15/15 | 10.524832 | 9.965184 | 0.061335 | $18.6284 | $1.2419 |
| 02_score_search | gpt-6-luna / max | 15/15 | 81.156763 | 78.624768 | 0.630496 | $1.3547 | $0.0903 |
| 03_deterministic_edges | gpt-6-astra / max | 15/15 | 46.615166 | 45.093632 | 0.339148 | $77.2664 | $5.1511 |
| 03_deterministic_edges | gpt-6-astra / low | 15/15 | 6.273838 | 5.681920 | 0.046890 | $13.9456 | $0.9297 |
| 03_deterministic_edges | gpt-6-luna / max | 15/15 | 77.677724 | 74.645248 | 0.622405 | $1.3609 | $0.0907 |
| 04_deterministic_each | gpt-6-astra / max | 9/15 | 46.697877 | 45.499136 | 0.239413 | $69.4572 | $7.7175 |
| 04_deterministic_each | gpt-6-astra / low | 9/15 | 9.145316 | 8.634752 | 0.039190 | $15.6999 | $1.7444 |
| 04_deterministic_each | gpt-6-luna / max | 7/15 | 46.165631 | 44.756480 | 0.247427 | $0.7122 | $0.1017 |

The two deterministic-placement cohorts total **$178.44** over 70 completed cells at these rates. The score-only control adds **$97.29** for 45 cells. Neither subtotal includes unfinished requests, older studies, this supervising chat, local Lean compute, taxes or residency surcharges.

The in-loop cohort remains incomplete. Its per-completed-problem values
describe that subset; it contains different problems than a full cohort and
should not yet be interpreted as a matched final cost comparison.

Context and service assumptions: these experiments did not request Fast
mode or an expanded context window. Current installed metadata lists a
272,000-token default for both models. The saved usage is aggregated across
the model requests inside a CLI turn, so it cannot independently certify
each request's length or service tier. Standard API calls above 272K input
tokens cost 2x input/cache and 1.5x output rates; Fast mode costs 2x applicable
rates. Apply those only to the requests that actually qualify, not to an
entire cell just because its cumulative input exceeds 272K.

For the completed beginning/end cohort, charging every non-cached input
token as an API cache write would add only the 25% input-rate premium:
Astra/max rises from $5.15 to $5.40/problem, Astra/low from $0.93 to
$1.03/problem, and Luna/max from $0.091 to $0.096/problem. This sensitivity
does not bound potential context/tier or different cache-hit behavior.
