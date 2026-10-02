# Stage 00: reproducible reference control

**All 15 warm-up declarations compiled in all 36 required theorem/version checks.**
All reference heartbeat measurements are available locally. The final export reused
32 cached values and prepared the four newly available checks; no refresh was requested.

- [reference_values.jsonl](reference_values.jsonl): original token counts, published
  heartbeat counts, local heartbeat counts, exact source/dependency commits,
  compiler versions, wrapper fingerprint, machine and measurement timestamps.
- [dataset_inventory.json](dataset_inventory.json): benchmark size and source balance.
- [environment_builds.json](environment_builds.json): provisioning results for the
  14 added environments. PutnamBench v4.25.0 uses the already configured environment.

The dataset remains byte-for-byte unchanged. It contains 15 proofs from five
sources, 17,595 reference tokens, 15 distinct source/version environments and 36
theorem/version pairs. Primary versions follow the first `version_info` entry;
this is the existing evaluator's local convention, not a claim about the private
arena worker's primary version.

## Repairs required before the experiment

Expanding beyond the original Putnam-only setup exposed three integration defects:

1. Module documentation (`/-! ... -/`) is a Lean command. The evaluator now inserts
   its support import immediately after the last import, before that documentation.
2. A declaration's `/-- ... -/` comment must stay attached to the declaration
   inside the measurement wrapper. Scoped `set_option ... in` and `omit ... in`
   remain outside, retaining their original scope.
3. Lake can serialize a package name as `«doc-gen4»` while its directory is
   `doc-gen4`. Dependency verification now resolves that spelling correctly.

Regression tests cover these cases, including real Lean compilation. Changing the
backend invalidated earlier fingerprints, so fresh reference entries were necessary
under the repaired evaluator. Subsequent optimization stages reuse these entries.

The final test run passed **89 tests**, including the syntax observer in both
legacy and newer Lean module mode, objective tradeoffs, Unicode edit positions,
and aggregation with missing or failed problems.

Parallel environment provisioning also exposed a collision in Mathlib's shared
`curl.cfg`. The setup script now uses a separate download cache per project; the
failed CSLib release-candidate setup was retried successfully. Its saved build
record describes the successful retry. An exploratory unpinned Lake help command
installed v4.34.1; every build and evaluation here explicitly pins a benchmark
toolchain, and no measurement uses that additional installation.

## Interpretation

This establishes a complete **local** control, using fresh `lake env lean --json`
processes and allocation heartbeats from the existing API. Imports precede the
measured declaration; the original target is replaced, and transitive `sorryAx`
dependencies are rejected. A failed primary candidate gets zero; missing
infrastructure is reported separately.

Candidate scores use cached local reference heartbeats, never the organizer's
published heartbeat denominator. Timings, primary-version choice and elaboration
instrumentation may differ from the private scoring worker. The evaluator does not
automatically forward every package-level `lake build` option to direct Lean
invocations; both reference and candidate use the same recorded invocation and
source context. These results measure a local score proxy, not an arena submission.

The unchanged-proof score is approximately 33.333%: zero reductions and 100%
compatibility. Stage 01 stores an actual unchanged-candidate control for each row,
so tiny heartbeat differences from the cached reference remain visible.
