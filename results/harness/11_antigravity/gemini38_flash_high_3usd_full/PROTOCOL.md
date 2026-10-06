# Gemini 3.8 Flash/high: full budgeted continuation

Run all 15 warm-up theorems with native Antigravity 1.3.0, exact
`gemini-3.8-flash/high` (`--model gemini-3.8-flash-high`), and at most **two
problem workers**. Audit one pilot before admitting the remaining cohort.
Keep the revised V2 task, five strategy cards, host proof tools, fixed original
denominators, prepared reference measurements, and deterministic cleanup at
the beginning and end. Native sampling defaults remain unchanged.

Each problem has **$3 standard Gemini API-equivalent estimated spending** and
a **3420-second whole-problem deadline**, including tool checks and final
cleanup. The frozen rate card verified October 6, 2026 uses $0.75/M ordinary
input, $0.075/M cache-read input, and $3.75/M output including thinking, effective
through December 31, 2026. Source: [Google pricing](https://ai.google.dev/gemini-api/docs/pricing).
The host deduplicates streamed step usage, replaces subtotals with terminal
usage, stops the native process at the remaining estimate, and admits further
attempts only while cumulative known spending and time remain. In-flight
responses can overshoot. This estimates standard Gemini API-equivalent usage;
Antigravity invoices, backend identity, subscription charges and cache-storage
durations are unverified. Missing final usage stays unknown and blocks another
cost-tracked request.

The initial `CallElimCorrect.substOldPostSubset` attempt in
`../gemini38_flash_high_3usd` was interrupted after native command execution
failed to allocate a PTY. Its complete terminal usage estimates
**$0.28447995**; it has zero host tool checks and an incomplete outcome.
This continuation pins and audits that evidence, includes its spending in the
$3 allocation, reuses its best host-verified proof, and retains its original
start **2026-10-06 16:57:59 UTC** and deadline **17:54:59 UTC**. Recovery time
counts against that deadline. The remaining 14 problems start their own
deadlines when admitted to a worker. Historical request/result bytes remain
unchanged.

The corrected adapter permits `/dev/ptmx` and `/dev/pts` for native command
PTY allocation. The offline isolation test also checks that protected source
projects and host evidence remain unwritable. Run from a new isolated runtime
with immutable source, prompts and native binary; save its identity manifest.
Native `init.model` records CLI selection and does not attest the served backend.

Launch from that runtime:

```bash
python -m proof_eval.harness.cli run \
  --provider agy --condition gemini-3.8-flash:high \
  --track-cost --budget-usd 3 --problem-timeout-seconds 3420 \
  --workers 2 --pilot \
  --carry-budgets-from /localhome/milikic/proof-reduction-competition/results/harness/11_antigravity/gemini38_flash_high_3usd \
  --output /localhome/milikic/proof-reduction-competition/results/harness/11_antigravity/gemini38_flash_high_3usd_full
```

Use `run.json`, `pilot_audit.json`, per-cell ledgers and the final audit for
completion evidence. Require all 15 cells before reporting a full-cohort mean.
Keep local scores separate from organizer scores.
