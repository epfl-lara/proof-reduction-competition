# Repaired context comparison

The cohort is the same **225 initial cells** as the direct-output experiment:
15 fixed deterministic incumbents × three models × five context conditions.
Every initial proposal is reused exactly. No initial model request is repeated,
and repaired proofs never become another cell's starting proof.

Each nonempty invalid proposal may receive up to three correctness-only correction
calls through [the fixed debugger](../../../docs/VALIDITY_REPAIR.md). The first
proof passing all required versions stops the loop. The debugger gets no candidate
length, heartbeat, score, reward, or acceptance feedback. A valid but inferior
proof therefore stops immediately; score-based incumbent fallback happens afterward.
Empty initial responses are not regenerated. Empty correction responses and
transport/unavailable outcomes terminate that attempt under this fixed policy.

Repair calls inherit the initial model, temperature 0.3, high reasoning setting,
and 32,768-token output cap including reasoning. Additional concurrency is limited
to one repair request per model. The worker processes completed initial cells as
they arrive and waits for pending initial outputs, without changing their prompts.

The five completed [pilot cells](../02_validity_repair/README.md) are reused when
their complete input, request and implementation configuration matches. Their
three already-made repair requests remain counted; copying artifacts is not a
new sample. This avoids spending the same pilot calls again or selecting a more
favorable repair draw.

`matrix_config.json` fixes the full cohort and implementation before this run.
`arrivals.json` records initial-result hashes as those results arrive.
`config.json` is the final audit manifest, written once all initial cells exist;
per-cell configurations already pin every consumed result at first use. Request
start markers prevent resampling on resume. Reference values and environment
identities are checked without preparing new references.

Reports must distinguish:

- Initial raw candidate outcomes.
- Final raw candidate outcomes after correctness repair, including copied
  incumbents and failures.
- The harness's selected proof and combined score after incumbent fallback.
- Initial and additional request counts, token usage, truncation and infrastructure
  failures, including calls belonging to unfinished cells in partial snapshots.

Full-condition means require all fifteen problems. Transport failures remain
unknown raw outcomes rather than fabricated zero scores. The final comparison
uses the same paired card/goal/cost contrasts as the initial experiment, with one
stochastic trajectory per cell; it does not pool the best results across arms.
This is a development comparison on fifteen warm-up proofs, not evidence of a
universally best prompt or model.

The initial and repair workers overlap on shared model services, so request
latency is descriptive. There is no controlled hardware-speed comparison.
