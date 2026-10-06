# Stage 11: Google Antigravity (`agy`)

Native-provider stage. The only condition is exact
`gemini-3.8-flash/high` through the installed `agy` CLI, using the same V2 task,
tools, score search and edge cleanup as the other native-provider stages.

- [gemini38_flash_high/PROTOCOL.md](gemini38_flash_high/PROTOCOL.md) records the
  prompt transport, selection-evidence limits, unknown price and 3420-second
  whole-problem deadline.

The budgeted launch uses
[gemini38_flash_high_3usd/PROTOCOL.md](gemini38_flash_high_3usd/PROTOCOL.md):
an explicit $3 standard Gemini API-equivalent estimate per problem, host
stream supervision and the same 3420-second deadline. Its fresh output
directory preserves the earlier unpriced plan. See that directory's saved
run and pilot evidence for current status; full-cohort results require all
15 completed cells and a passing audit.

[gemini38_flash_high_3usd_pty/PROTOCOL.md](gemini38_flash_high_3usd_pty/PROTOCOL.md)
records a prepared one-theorem pilot after the initial command tool failed
to allocate a PTY. That pilot was not launched; the full-run continuation
below supersedes it.

[gemini38_flash_high_3usd_full/PROTOCOL.md](gemini38_flash_high_3usd_full/PROTOCOL.md)
declares the full 15-problem run with at most two workers. It carries the
interrupted first problem's $0.28447995 estimated spend, original deadline and
best verified proof into the corrected runtime. The initial evidence is
preserved. The pilot must pass audit before the remaining cohort is admitted.

The full run stopped on October 6, 2026 with **5 complete problems and 10
incomplete outcomes**: nine quota errors and one Google API error 500. All
15 cells have terminal evidence, and the saved-evidence audit passed. A passing
evidence audit does not relabel incomplete searches as complete. Selected
verified proofs are preserved; there is no full-cohort model score.

On the same five problems Gemini completed, local Combined means were
**74.363540%** for Gemini 3.8 Flash/high, **87.280154%** for the $3-target
Sol 6.1/max run, and **73.216230%** for Qwen 3.8 Flash Next/xhigh. Sol won all
five comparisons; Gemini won two against Qwen. Including two interrupted
Gemini problems that had host proof checks, the seven-problem saved-proof means
were Gemini **73.518453%**, Sol **87.971065%**, and Qwen **73.468131%**.
These are partial comparisons with fixed prompts, inputs, references and
scoring. Qwen had a time budget and unknown pricing; Gemini's first problem
retained its original deadline after the PTY repair.

The full Sol run scored **89.357422%** over 15 problems. Qwen's recovered
15-proof submission portfolio scored **78.219958%**, using additional recovery
budgets. See [Sol evidence](../10_budget_resets/sol61_max_3usd/COMPARISON.md),
[Qwen submission](../09_qwen_flash_next/README.md), and
[Gemini report](gemini38_flash_high_3usd_full/report.json). These scores are
local; organizer grading remains separate.
