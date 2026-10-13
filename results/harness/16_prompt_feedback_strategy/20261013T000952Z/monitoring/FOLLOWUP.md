# Authorized overnight experiment follow-up

Owner thread: `01a12e1f-a819-7341-9d8a-84575343ddad`.
Repository: `/localhome/milikic/proof-reduction-competition`.
Current experiment: `results/harness/16_prompt_feedback_strategy/20261013T000952Z`.

The user explicitly asked on 2026-10-13 to leave the current run going, arrange
an Antigravity handshake and completion/failure notifications, fix and restart
failed jobs autonomously, and test step 4 on the better version if the results
improve on the roughly 89.4% baseline. Do not ask again for these actions.
Antigravity observes and reports; Codex makes and validates repairs and launches.

## Current run and result decision

1. Keep both frozen runtimes and historical evidence unchanged. The detached
   launcher runs revised changes 1–3, audits them, then runs and audits a fresh
   baseline. Each arm has 15 theorems, five workers, gpt-6.1-sol/max, $3 per
   problem API-equivalent target, best_effort usage policy, and no wall watchdog.
   The launcher, pins, protocol, tests, and live report paths are in the root.
2. Wait for both whole cohorts to complete and their saved-evidence audits to
   pass. Recheck `proof-harness audit` with the corresponding frozen runtime if
   needed. Report full-cohort means only for complete conditions, keeping local
   score, every-version validity, effort and reported/estimated/unknown usage
   separate. A successful audit alone does not establish full completion.
3. The historical reference is exactly **89.35742200958394%** from
   `results/harness/10_budget_resets/sol61_max_3usd/report.json`. It is a historical
   comparison with different budget/runtime details, not the matched control.
   Compare revised versus the fresh baseline on the same 15 problems and all
   three components; select the higher complete mean (baseline on an exact tie).
4. If the selected current arm exceeds that historical reference, implement
   and run ONE separate step-4 condition on the selected prompt/card/feedback
   version. Record the decision with exact reports and hashes before launch.
   Otherwise report the completed comparison and do not launch step 4.

## Step 4, if the gate passes

Step 4 is bounded restart history for the same theorem and same condition:
preserve useful source discoveries, host-measured changes and rejected trials
with reasons, and a small set of unresolved ideas across fresh attempts.
Separate verified host facts from unverified model notes. No other condition's
solutions, cross-theorem memory, mixed-model handoff, scheduler changes, early
stopping, or proof-budget increase is authorized by this experiment.

Read README.md and docs/ARCHITECTURE.md before runtime changes. Implement in
maintained src/proof_eval/harness modules. Current search.py starts fresh
messages with just the best proof at each attempt; tracking_audit.py freezes
all task payload fields other than incumbent proof/scores. Any new history
field needs bounded deterministic construction, host-owned attempt evidence,
provenance hashes, isolation and resume/audit validation. Do not merely allow
arbitrary mutable prompt content through the auditor. Preserve backend.py and
cached original reference denominators.

Run relevant offline contract tests, formatting/lint and the full offline suite
for shared behavior changes. Prepare a NEW isolated frozen runtime and NEW
output. Keep the winner's prompt/card/feedback bytes and all other model,
effort, tools, cohort, original/D0 seeds, budgets and restart limits fixed.
The new 15-theorem run starts from the same prepared original/D0 seeds, not
the first experiment's optimized solutions; the winning arm is its control.
Queue all 15 directly with exactly five workers, after previous paid workers
have stopped. Save a protocol and runtime manifest, launch durably, audit the
completed evidence, and compare the whole cohort against the selected control.

Update monitor.json ATOMICALLY to the new phase, run root, launch/completion
paths and targets; extend protected paths if needed. Keep the timer enabled.
Do not overwrite old alerts or comparison evidence. On final completion (or a
non-actionable irrecoverable outcome), write a durable final report and
workflow_complete.json in this monitor directory, then stop its timer.

## Failure recovery

Inspect terminal evidence and process identities before acting. Failed Lean
candidates, slower candidates, unknown reported usage under best_effort, normal
fresh optimization attempts, and controlled budget exhaustion are not crashes.
Quiet output is not proof of a dead request. Never kill a healthy cost-only
request just to finish by morning.

Fix confirmed infrastructure/runtime problems without altering frozen active
files. Let unrelated queued cells continue. Never repeat an active request or
one with a durable started marker but indeterminate terminal outcome. Never
delete started markers or failed attempts, invent usage, reset cost spending,
replenish budgets, change model/effort, or add a hidden wall-time deadline.
Observed terminal transport failures may recover only under the existing
bounded policy and remaining whole-problem budget. Resume uses the same frozen
configuration; a required runtime fix gets a new output/runtime and explicit
budget/attempt carryover. Inspect existing --carry-budgets-from contracts first.
Do not use --incumbents-from to disguise a recovery budget reset.

Maintain a maximum of five simultaneous closed-model requests across these
experiments and any shared RCP clients. Never stop or modify another run to
obtain slots. If safe recovery is impossible, preserve the best checked proofs,
record the exact unresolved outcome, and report honestly instead of claiming
completion. Do not resample merely to achieve a complete mean.

The monitor is operational code outside the repository. Its unit tests are
`python -m unittest discover -s /localhome/milikic/.codex/monitors/prompt123-20261013 -p 'test_*.py'`.
It polls every minute without model calls when healthy. New events get a bounded
AGY review and `codex queue` delivery to this exact thread; review failures fall
back to the host evidence. Receipt files prevent repeated delivery.
