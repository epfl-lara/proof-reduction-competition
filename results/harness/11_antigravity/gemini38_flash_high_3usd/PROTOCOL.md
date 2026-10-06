# Gemini 3.8 Flash/high with a $3 estimated per-problem budget

Condition: native `agy` 1.3.0, exact `--model gemini-3.8-flash-high`, `code`
agent and streaming JSON output. The revised V2 prompt, five structural cards,
score feedback, host proof tools and deterministic cleanup at the beginning
and end match the other current native-provider runs. The declared cohort is
the 15 warm-up declarations with cached references and fixed original token
denominators. Every required version must pass. No reference remeasurement or
other model's candidate proofs are used.

The system policy, host tool instructions and user message are concatenated
into one inline prompt because this CLI has no separate system channel.
Landlock protects pinned source projects and host evidence while the CLI uses
its documented headless tool approval flag. Selection evidence is
`init.model`; it proves CLI selection, not the served backend identity.

Each problem shares one **$3 API-equivalent budget** across all attempts and
one **3420-second whole-problem deadline**, including host checks and cleanup.
The frozen estimate uses standard [Google Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing),
verified 2026-10-06 and effective through 2026-12-31: **$0.75/M ordinary input,
$0.075/M cached input, $3.75/M output including thinking**. Cache storage and
Antigravity subscription billing are unobserved and excluded. This estimate
does not attest the actual backend or billing tier.

The host reads per-step streaming usage, replacing repeated ACTIVE/DONE
snapshots. Terminal cumulative usage replaces the step subtotal. It stops the
native child when observed spending reaches the remaining cap and records a
host-owned `cost_stop.json` with the event prefix, usage and estimate. A model
response already in flight can overshoot the cap. A killed session without
terminal usage retains an observed lower bound; its final total stays unknown.
The best proof certified by host checks survives a controlled stop. Resuming
does not replenish either budget or resample an indeterminate request.

Run from an isolated copy of the validated runtime. Start with `--pilot`,
which audits one theorem before admitting the rest of the cohort; use three
workers thereafter. Report full-cohort scores only after all 15 cells complete
and saved evidence passes `proof-harness audit`.
