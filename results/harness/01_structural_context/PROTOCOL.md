# Structural prompt, context and tools: correctness-only control

Predeclared matrix: **15 warm-up declarations × Astra/low and Luna/max = 30
cells**, one original-proof seed per cell. Compare against the corresponding
original arms of stages 09/10: Astra/low **57.222638%**, Luna/max **53.045428%**.
All means use fixed original denominators and the same 36 cached version
references. No deterministic preprocessing or postprocessing is applied.

## Changes from the historical harness

- Remove the direct-output prompt's conflicting statement that there are
  “no tool calls or repair turn,” which coexisted with the Codex tool instructions.
  Later developer instructions enabled tools, so this is a conflict-removal
  hypothesis, not proof that the conflict caused earlier failures.
- Replace the lexical tactic-card subset with five generic structural cards:
  reuse an abstraction, induct on evidence, factor a local identity, supply
  explicit witnesses, and change representation. Cards contain triggers,
  actions and checks, not theorem-specific answers or universal tactic prices.
- Add named tools for literal source search, declaration outlines, bounded
  source reads, and optional primary-version goal observations. The supplied
  preceding source excerpt and original statement/proof are retained.
- Give unambiguous source-inspection → proposal → correctness-debugging
  instructions. The first passing proposal closes the optimization attempt.

This tests the combined harness change. It does not isolate the bank, wording
and source tools individually. Ordinary shell source reads remain available;
web search, additional model calls and deterministic optimization programs are
disabled or out of scope. The historical CLI allowed cached web search, another
recorded interface difference. No remembered target-specific Astra solution is
inserted into the prompt.

## Feedback and selection

`python tools.py check candidate.lean` returns compiler diagnostics and version
pass/fail only. It exposes no candidate score, length, heartbeat count or
performance-based acceptance decision. The host measures and logs these privately.
Goal observations have allocation/timing fields removed and are diagnostic,
not proof replacements or full performance measurements.

After the first all-version-valid proposal, further changed candidates are
refused by the host. If a completed final is invalid and there is no earlier
valid proposal, up to three outer correctness repairs are allowed, as in the
historical baseline. Each call retains the baseline's 1,800-second timeout;
neither a token cap nor temperature is imposed through Codex. Model-side
correctness checks are recorded separately from outer calls.

Selection preserves the original unless the valid proposal improves the local
combined score by more than 0.05 points. Selected/fallback scores, initial
validity, checked proposals, inference usage and historical deltas remain
separate. All selected proofs must pass every listed version.

The first theorem is an engineering pilot with both models. Its results are
retained in the full cohort. Source/request identities and saved score arithmetic
are audited before expanding to the full matrix and before stage 02 starts.
Incomplete conditions have no full-benchmark mean. A lack of improvement alone
does not fail the engineering gate.

Run [README.md](README.md) is generated from durable cell records. The sibling
[score-search protocol](../02_score_search/PROTOCOL.md) reuses the same task
messages and tool implementation but exposes scores and changes the stopping rule.
