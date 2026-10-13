# Bounded baseline recovery

The original baseline ended with 15 terminal cells, 13 complete and two
incomplete after observed terminal capacity failures. Its saved-evidence audit
passed. Original results, requests and configuration remain unchanged.

The user's explicit instruction to fix and restart failures autonomously is
used for one separately recorded continuation through `--carry-budgets-from`.
It uses the identical frozen baseline runtime, prompt, cards, model, effort,
tools, prepared inputs, references and original $3 per-problem allocation.
All previous successful and failed generations contribute to cumulative cost.
Unknown reported usage stays unknown; the pinned best-effort estimates govern
admission. No whole-problem wall deadline is added.

The two funded cells are `putnam_1964_b2` and `putnam_1995_a3`, with estimated
remaining amounts $0.7652424 and $0.7252032 respectively. All other cells already
reached their targets and admit no further model requests. All 15 are queued
through the ordinary five-worker runner. Final deterministic cleanup has no
model cost and its additional changes, if any, must be reported separately.

The original two automatic transport recoveries are exhausted. This manual
continuation sets `max_transport_restarts=0`, so another terminal transport
failure stops the affected cell. It sets `max_budget_restarts=14`; the previous
8 or 6 attempts plus at most 15 new admissions stay within 23 total. There is
no second manual continuation authorized by this recovery plan.

This is a recovery extension with a recorded change to admission policy, not
a clean completion of the original matched condition. Keep the original
comparison's incomplete outcome visible. If the recovery completes and audits,
compare the recovered baseline with the completed revised arm, describing this
qualification. Then apply the user's conditional step-4 gate. If recovery
fails, preserve the checked proofs and report the unresolved result; do not
claim a complete mean or launch step 4 from an incomplete comparison.

See `recovery_plan.json`, `validation.json`, `runtime_manifest.json`, `launch.json`,
and the new `baseline/` evidence. Four focused budget/carryover tests passed;
the runtime implementation was not changed. Both old and new native failure
evidence and all source-result hashes are retained.
