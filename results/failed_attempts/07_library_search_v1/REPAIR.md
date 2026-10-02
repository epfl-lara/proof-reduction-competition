# Incomplete discovery attempt, preserved for audit

This attempt was **not used as the input to stage 08**. Its selected proofs remain
fully checked, but discovery stopped early on two PhysLean problems. The complete
library-search stage restarts from stage 06 in [07_library_search](../../07_library_search/).
Candidate evaluation caches are reused; the reference measurements are unchanged.

- The electromagnetic-potential declaration reached a nested inline `by` term
  inside a probed `exact`. An earlier insertion changed its column, but the probe
  retained the old indentation. Lean rejected the instrumented source.
- The Wick-algebra declaration selected a `conv` simplifier as an ordinary tactic.
  A normal tactic probe is not valid in that syntax category.
- Inspection also found sequence containers and `rcases` patterns being nominated
  as leaf tactics. The repaired selector requires concrete tactic parser kinds
  and excludes conversion contexts and patterns.

The repaired insertion pass calculates columns after preceding insertions. It
passed a real Lean regression with two inline proof terms and Unicode, then all
12 site batches of the exact two failed incumbents (64 sites, no discovery errors).
See [repair preflight](../../validation/repaired_probe_preflight.jsonl) and its
[metadata](../../validation/repaired_probe_preflight_metadata.json).

The exact former probe implementation is retained at
[its SHA-256 snapshot](../../validation/implementation_snapshots/251d851decbec17c915f8d17107b4642a344dbffe62d41577e046ae01e574bcf/tactic_search.py).
The scoring backend and its reference fingerprints were not modified. The audit
verifies historical source snapshots by recomputing their hashes.

For cost analysis, include this attempt's recorded session time and compiler work
alongside the repaired stage. Its cached candidate evaluations can make the retry
cheaper; retry wall time alone is not the cost of obtaining the final result.
