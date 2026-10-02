# Validation evidence

These records check the implementation and saved experiment evidence. They are
separate from candidate trials and do not refresh the reference measurements.

- [Final main-chain audit](final_audit.json): all 30 sequential stages pass,
  including every accepted edit chain and all 36 unchanged cached references.
  The [early-arithmetic branch audit](audit_early_arithmetic.json) is separate
  because that experiment starts from stage 03 rather than the final main stage.
- [Warm-up test suite](test_suite.json): command, output, and SHA256 hashes of
  the Python implementation and tests; 180 tests and 102 subtests passed.
  [Earlier suite](test_suite_v1.json) preserves the pre-repair run.
- [Batch interface test suite](batch_api_test_suite.json): tests after the results
  relocation and new dataset-independent entry point; **186 tests and 102
  subtests pass**. The earlier test records
  remain unchanged and identify the implementation tested at their timestamps.
- [Relocated-evidence audit](relocation_audit.json): checks the complete historical
  chain at its new paths against the unchanged cache and historical source hashes.
- `audit_*.json`: independent recomputation of token counts, per-problem and
  aggregate scores, required-version coverage, and accepted edit chains. Audits
  with cache verification also compare all 36 local reference timestamps,
  heartbeats, proof hashes, and environment fingerprints with the saved export.
  Intermediate audits cover only the stages named inside their records.
- [Initial discovery preflight](discovery_preflight.jsonl) and
  [metadata](discovery_preflight_metadata.json): pilot probes before the fixed
  menu was expanded from 15 to 19 entries.
- [Expanded-menu preflight](extended_menu_preflight.jsonl) and
  [metadata](extended_menu_preflight_metadata.json): checks for the 19-entry
  menu used in stage 06.
- [Repaired-probe preflight](repaired_probe_preflight.jsonl) and
  [metadata](repaired_probe_preflight_metadata.json): every bounded batch on
  the two incumbents that exposed inline-proof indentation and `conv` site
  selection defects, plus a Unicode/inline-proof regression. Path relocations
  and source hashes are explicit in the metadata.
- [Implementation snapshots](implementation_snapshots/): exact, hash-addressed
  historical source bytes for auditing completed stages. Stage 06 used the
  earlier probe; stage 07 and later use the repaired probe. The audit verifies
  file contents against each stage's recorded hash.

The [failed library-search attempt](../failed_attempts/07_library_search_v1/REPAIR.md)
is retained with its costs and diagnostics. Its valid selected proofs were
audited, but its incomplete discovery run is excluded from the main score chain.
Repaired stage 07 reuses compatible candidate-cache entries from that attempt;
its retry timing alone is not the full cost of library search.

The audit is deliberately read-only: it checks stored evidence and reference
cache records without invoking Lean. Candidate validity comes from the saved
full-declaration compiler checks in the pinned benchmark environments.
