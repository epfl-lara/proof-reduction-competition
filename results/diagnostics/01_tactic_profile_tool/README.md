# Tactic profiling tool demonstration

Two explicit diagnostic requests ran through the actual copied `tools.py` client
and host Unix-socket service for `CallElimCorrect.substOldPostSubset`, on pinned
Strata/Lean `v4.26.0`. No model requests were made. Both profiles completed.

The [original declaration](workspace/candidate.lean) reproduces the main
hotspots in the supplied Gemini notes:

| Inclusive diagnostic region | Raw counter delta | Heartbeats (raw / 1000) |
| --- | ---: | ---: |
| Proof value elaboration | 5432608 | 5432.608 |
| `case app` | 1813775 | 1813.775 |
| Opening `induction post <;> simp [substOld]` | 1433619 | 1433.619 |

The [diagnostic copy](workspace/marked.lean) labels the opening block with
`profile_tactic "opening cases" in (...)`. Its observed label cost was
1433958 raw, or 1433.958 heartbeats, at candidate line 6. Profiling and annotation
add overhead; these are inclusive diagnostics, separate from arena scores.

[Original feedback](candidate_feedback.json) and
[labelled feedback](marked_feedback.json) contain the bounded tool responses.
The full host-owned traces and exact supplied declarations are in
[original evidence](host/profiles/b7fc581a6ba2b610bcdcf2a0d07f589088a3c39546aa59ef2b098b50bea1a6d4.json)
and [labelled evidence](host/profiles/24befb6fa2c918f7be4e5f2cc30b90c960b536e0b5e00d953c92ea1b3cdd6a7f.json).

[Validation](validation.json) records the final implementation/prompt hashes,
zero model requests, zero check-ledger entries, unchanged best proof/scores,
and matching reference-export hashes before and after the demonstration.
The source hashes were verified against the final implementation.

`make format` and `make check` passed. The full offline `make test` run passed
342 tests and 102 subtests. Real profiler tests cover Lean `v4.25.0`, `v4.26.0`,
`v4.32.0` and `v4.33.0-rc2`, repeated/nested labels, failed proofs, Unicode/doc
comment positions, cache reuse and bounded CLI/host feedback. The arena backend
still matches every saved warm-up reference fingerprint.

See [usage and units](../../../docs/PROFILING.md).
