# Google Antigravity Gemini 3.8 Flash/high pilot

Planned condition: exact `gemini-3.8-flash/high` through the native `agy` CLI
(print mode). Same revised V2 task policy, five structural cards, score
feedback, source/goal/tactic tools and deterministic cleanup at the
beginning/end as the other native-provider stages. Same 15 warm-up
declarations, 36 required version checks, fixed original token denominators and
cached local references; no reference remeasurement, other-model context,
provider fallback or in-loop cleanup.

## Prompt transport

Print mode has no system-prompt channel. The harness system policy, provider
tool instructions and user message are merged into one inline `-p=<text>`
argument, so those sections reach the model as **user-level instructions**.
`-p=@file` is a file reference (the model must call a read tool), not prompt
loading, and is not used. A merged prompt above 120,000 bytes raises
`ValueError` before launch. The exact model is passed as the suffixed
`--model gemini-3.8-flash-high` slug with no separate `--effort` flag. The
`code` agent, `--output-format stream-json`, `--disable-slash-commands` and
`--dangerously-skip-permissions` are used; `AGY_CLI_DISABLE_AUTO_UPDATE=true`
preserves the pinned executable.

## Evidence limits

Selection evidence is the stream-json `init.model` (the requested slug). It
proves the requested selection propagated to the CLI, not which backend model
served the response; missing evidence stays unknown and only a positively
contradictory `init.model` is a model mismatch. Terminal status, conversation
identity, final-content agreement and recovered tool denials are audited.
Reported usage excludes cache reads, so normalized input adds them back and
cache writes are an unreported zero placeholder; reasoning (`thinking_tokens`)
is a subset of output. Complete usage from failed calls is retained.

## Price and budget

The exact Gemini 3.8 Flash Antigravity price is **unknown**; usage is recorded
and the price stays unknown (`unknown_price`). Because the model is unpriced,
`budget_tracking="cost"` is rejected and no native dollar guard is sent. Every
problem uses the current **3420-second** (57-minute) whole-problem deadline,
including host tools and final cleanup; a controlled deadline retains the best
fully verified proof and is distinct from a transport error.

## Status

Not yet run. The pilot runs one theorem per selected condition (`--pilot`)
before any scale-up, and completed evidence is audited with
`proof-harness audit` before a full-cohort mean is reported.
