# Qwen 3.8 Flash Next with a whole-problem deadline

Run the full 15-problem warm-up cohort using native Lemex, exact
`Qwen/Qwen3.8-Flash-Next/xhigh`, and three simultaneous problem workers.
The user requested no pilot. Native sampling defaults remain untouched.

The revised canonical prompt, five strategy cards, source/goal tools, score
feedback, and tactic heartbeat profiling match the current Sol profiling setup.
Seeds are the better cached original or deterministic proof, never another
model condition's answers. Final deterministic cleanup remains enabled.

Each problem has one 3420-second (57-minute) wall deadline covering provider
admission, reasoning, tools, Lean checks and final cleanup. On expiry retain
the best proof already verified on every required version. A skipped or
interrupted final cleanup is recorded. Native finals, controlled deadline stops
and infrastructure failures remain distinct; missing usage stays unknown.

The 57-minute allocation is a chosen conservative division of the saved
48-hour/50-problem open-track total, not an organizer per-problem rule. These
gateway runs do not establish the required local GPU hardware/runtime.

Keep original token denominators and cached local heartbeat references fixed.
No original proof is remeasured. The byte-frozen Lean backend is unchanged.
Full-cohort averages are withheld until every declared bounded outcome is
complete. All selected candidates must pass all 36 required version checks.

An ignored, frozen runtime copy under `.proof-eval/runtimes/` isolates this job
from other development and experiments. `launch.json` records its source hashes.
It is a runtime copy of the current maintained code, not an executable historical
audit snapshot. The exact gateway price is unknown.

Progress and evidence are in [qwen38_xhigh_57m](qwen38_xhigh_57m/README.md).

An independent completion checker runs the saved-evidence audit after the host
finishes, preserving `audit.json` and any failure. It makes no model or Lean calls.
