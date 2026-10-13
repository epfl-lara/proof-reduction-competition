# Prompt, feedback and strategy bundle

Compare the current V2 harness against changes 1–3 using gpt-6.1-sol/max.
The revised full cohort runs first, then the fresh baseline. Each condition
queues all 15 theorems with five workers; there is no pilot gate. Sequential
conditions keep total model parallelism at five.

Both conditions use the same cached references, prepared seeds, tool set,
cleanup, restart limits, pinned native CLI, best-effort usage policy and $3
API-equivalent target per theorem. There is no wall-time watchdog. Reported
usage and heuristic estimates remain separate; this is not an invoice cap.

The revised condition changes only proof-search priorities, model-facing score
explanations and three existing strategy cards. Restart history handoff is not
included. No condition receives another condition's solutions.

The primary result is the paired final local combined-score difference over all
15 theorems after both saved-evidence audits pass. Report each score component,
search effort, compatibility and cost completeness separately. Preserve failed
attempts and incomplete outcomes. This single warm-up replicate tests the bundle;
it does not isolate its components or establish held-out performance.

`runtime_manifest.json` identifies the frozen runtime copies and source commit.
`protocol.json` records the controls. Outputs are in `revised/` and `baseline/`;
each produces `report.json`, `run.json`, `audit.json` and a full submission only
when eligible. Launch evidence and validation logs are stored alongside them.
