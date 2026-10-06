# Tactic heartbeat diagnostics

Models can explicitly inspect the supplied proof or a candidate with the host
tool:

```bash
python tools.py profile candidate.lean
python tools.py profile candidate.lean --threshold-raw 1000 --limit 30
python tools.py profile candidate.lean --version v4.26.0
```

The response ranks expensive tactic invocations and declaration elaboration or
kernel phases. Each entry includes its printed tactic, raw counter delta,
normalized heartbeats, and parent identity. Sequence and repeated macro wrappers
are suppressed in the bounded view; distinct branch invocations remain distinct.
The host retains the full structured trace in the session's `profiles/` evidence.
Automatic trace snippets are Lean's pretty-printed syntax and can include macro
expansions; they are not exact source ranges. The saved tree preserves ancestry
even when the bounded ranking omits a parent.

To measure a chosen tactic or block, make a diagnostic copy of the declaration
and add a label:

```lean
theorem example_profile (n : Nat) : n = n := by
  profile_tactic "helper" in have h : n = n := by rfl
  profile_tactic "finish proof" in exact h
```

A parenthesized tactic sequence labels a block:

```lean
  profile_tactic "both branches" in (constructor <;> trivial)
```

Each observed label reports its line, Python character offsets, raw counter delta,
normalized heartbeats, and whether the wrapped invocation succeeded. Repeated
invocations are separate entries. Labels are measured even if the native trace
threshold hides the tactic. Remove `profile_tactic` wrappers before calling
`check` or returning the final declaration; the wrapper exists only in diagnostic
compilation. The tool does not rewrite a candidate for scoring.

`IO.getNumHeartbeats` and `trace.profiler.useHeartbeats` supply raw counters.
The repository's heartbeat unit is **raw / 1000**. For example, the Gemini trace
value `1813446` corresponds to `1813.446` of these heartbeat units. The default
native threshold is `10000` raw, or 10 normalized heartbeats; lowering it reveals
cheaper steps. Native trace thresholds apply before ranking, and costs are
inclusive: an outer `all_goals simp` includes its individual `simp` invocations.
Do not sum parents and children. Threshold-pruned traces cannot establish exact
exclusive costs.

Profiling runs fresh pinned `lake env lean`, with synchronous `Elab.async=false`
and the unchanged verified-target wrapper. Trace collection and labels add
overhead, so the reported diagnostic total is not a score or a replacement for
`check`. Tactic-state sharing, failed search branches and later kernel checking
also prevent interpreting these numbers as portable prices for tactic names.
Use a profile to choose where to investigate, then compare complete unannotated
declarations with `check` across every required version.

The profile API does not prepare, read or replace reference measurements. It
uses the separate `profiles` cache, keyed by exact proof bytes, pinned environment,
diagnostic implementation, version, threshold and output limit. Failed profiles
are explicit, partial, and uncached. Correctness-only sessions reject this tool.
Profiles cannot update the best proof or the check ledger. Existing mathematical
prompt and strategy-card files remain unchanged; score-mode tool instructions
describe the new operation. New experiments require new output directories.

The same diagnostic is available locally without a model call:

```bash
proof-eval profile CallElimCorrect.substOldPostSubset \
  --code-file candidate.lean --threshold-raw 100000 \
  --output profile.json
```

The terminal prints bounded feedback; `--output` saves the full trace.

```python
from proof_eval import Evaluator
from proof_eval.verification.profiling import ProfileConfig, profile

diagnostic = profile(
    Evaluator(),
    "CallElimCorrect.substOldPostSubset",
    candidate_code,
    config=ProfileConfig(threshold_raw=100_000, limit=20),
)
```

Lean's [trace implementation](https://github.com/leanprover/lean4/blob/v4.26.0/src/Lean/Util/Trace.lean)
defines the native counter and threshold behavior. The arena measurement wrapper
in `verification/backend.py` remains byte-for-byte unchanged.
