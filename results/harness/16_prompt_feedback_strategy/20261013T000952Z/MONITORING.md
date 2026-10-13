# Autonomous follow-up

Latest policy update: [delayed capacity recovery](capacity_recovery_policy_02/README.md)
supersedes the assistant's earlier one-continuation limit. The user had already
authorized autonomous recovery. Further eligible retries wait through a cooldown,
retain the original remaining budgets, and keep at most 23 cumulative admissions
per problem. Earlier failure and setup records below remain historical evidence.

Update at 2026-10-13 07:46 UTC: the original revised cohort completed and passed
audit at 89.44863042414136%. The original baseline passed its evidence audit but
ended with 13 complete and two capacity-failed cells. The user-authorized,
separately recorded [bounded recovery](recovery_01/PROTOCOL.md) is running with
the original spent budgets carried forward. The live timer watches this recovery
and the original revised report. Original comparison/setup evidence below stays
unchanged; consult the recovery protocol before interpreting a future mean.

The user authorized an Antigravity handshake, completion/failure alerts to the
owning Codex thread, safe autonomous recovery, and one conditional step-4 run.
The existing experiment continues unchanged.

The host checks every minute through `prompt123-agy-monitor.timer`. Healthy
checks do not dispatch model requests. A new confirmed incident or completed,
audited comparison receives an Antigravity review using
`gemini-3.8-flash-high`, then a durable `codex queue` notification to thread
`01a12e1f-a819-7341-9d8a-84575343ddad`. AGY review failure falls back to the host
observation. The monitor does not repair or signal proof jobs; Codex handles
the authorized follow-up after waking. The timer remains active for step 4.

- Live monitor: `/localhome/milikic/.codex/monitors/prompt123-20261013`
- Saved setup evidence: [monitoring/setup.json](monitoring/setup.json)
- AGY acknowledgement: [monitoring/handoff_review.json](monitoring/handoff_review.json)
- Queue receipt: [monitoring/handshake_queued.json](monitoring/handshake_queued.json)
- Exact follow-up instructions: [monitoring/FOLLOWUP.md](monitoring/FOLLOWUP.md)
- Monitor validation: [monitoring/tests.log](monitoring/tests.log)

The decision uses both complete audited 15-theorem cohorts. Select the better
fresh condition, with baseline retained on an exact tie. If its local combined
score exceeds the historical reference **89.35742200958394%**, run one separate
step-4 condition with bounded same-theorem restart history on that selected
version. Keep the original/D0 seeds, model/effort, tools, budgets, cohort and
five workers fixed. Do not seed it with another condition's optimized proofs.
The fresh winner is its control; the historical reference has different
runtime/budget details and is reported separately.

Failure recovery preserves every attempt and spent budget. Active or
indeterminate requests are never resampled. Ordinary failed Lean candidates
and controlled cost stops are not infrastructure failures. Cost-only runs
retain no wall deadline; an overnight completion time is not guaranteed.

The monitor source/configuration and follow-up files below are setup snapshots.
The live directory contains later observations, receipts and phase updates.
These files are outside the pinned proof runtimes and measurement inputs.
