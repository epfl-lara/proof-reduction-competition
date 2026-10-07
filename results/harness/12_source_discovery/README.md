# Qwen with updated local discovery tools

The native Lemex `Qwen/Qwen3.8-Flash-Next/xhigh` run completed **15/15**
theorems, with **36/36** required versions passing. Its local combined mean
is **78.815525%**: length reduction 55.818720%, heartbeat reduction 80.627854%,
and compatibility 100%. These are local scores, not organizer results.

The run uses the same prepared seeds, original reference denominators and
3420-second whole-problem deadline, with literal dependency search and optional
frozen offline semantic discovery. Web discovery was disabled. The pilot and
saved-evidence audit passed. Recorded usage/pricing gaps remain unknown.

- [Run report](qwen38_xhigh_local_57m/report.json)
- [Audit](qwen38_xhigh_local_57m/audit.json)
- [Complete 15-proof export](qwen38_xhigh_local_57m/conditions/Qwen__Qwen3.8-Flash-Next__xhigh/selected_candidates.jsonl)
- [Frozen configuration](qwen38_xhigh_local_57m/config.json)
- [Tool review and validation](tool_review.json)

Requests, native events, host checks, profiles, semantic lookups and source
snapshots are preserved. Disposable workspace files were removed; native final
messages remain. The older stage-09 export is a separate cross-run selection
and is not a matched single-run comparison.
