# Sol 6.1/max after the package refactor

This is a new 15-problem warm-up replicate of `05_model_config`'s Sol condition,
using `gpt-6.1-sol` with **max** reasoning. It tests the maintained package APIs.
The pre-refactor result was **87.3422148453% combined**, with 100% compatibility.

The full prompts and tool instructions match all 15 pre-refactor Sol requests.
All 36 cached reference records remain available. The measurement backend moved
byte-for-byte, retaining its pinned implementation hash. References are never
remeasured. The original token and heartbeat denominators are fixed.

The agent uses revised structural context, source/goal/check/status/finish tools,
iterative score feedback, the better original/saved deterministic seed, and the
same bounded ten-method final cleanup. Only a proof passing every required version
and gaining more than 0.05 percentage points may replace the best proof. In-loop
cleanup remains retired. There is no imposed total model token, attempt or time
budget; every terminal problem reports the API-equivalent cost and the $3 flag.

The new CLI runs and audits one theorem before launching the rest, then reuses
that pilot cell. Requests are durably recorded, interrupted requests are not
resampled, and all final candidates retain all-version evidence. A complete mean
requires all 15 problems; a single replicate cannot establish statistical equality
or a causal performance change from source organization.

Run or resume with:

```bash
proof-harness run --condition gpt-6.1-sol:max --pilot --workers 10 \
  --output results/harness/06_refactor_regression
proof-harness audit --output results/harness/06_refactor_regression
```

See `validation_before_run.json`, `config.json`, `pilot_audit.json`, the host
per-cell evidence ledgers, `audit.json`, and [COMPARISON.md](COMPARISON.md).
