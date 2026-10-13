# Prompt, feedback and strategy bundle

The [October 13 experiment](20261013T000952Z/PROTOCOL.md) compares a fresh V2
baseline with the combined changes 1–3: conditional search priorities, score
component explanations, and focused revisions to three existing strategy cards.
Both use gpt-6.1-sol/max on the same 15 prepared theorems with the same $3
API-equivalent target, best-effort accounting, tools and cleanup. The revised
cohort runs first, then the baseline, with five parallel workers total.
Restart history handoff is excluded.

- [Revised report](20261013T000952Z/revised/report.json)
- [Baseline report](20261013T000952Z/baseline/report.json)
- [Launch identity and order](20261013T000952Z/launch.json)
- [Matched configuration preflight](20261013T000952Z/matched-preflight.json)
- [Offline validation](20261013T000952Z/validation.json)
- [Exact proposed changes](20261013T000952Z/changes.patch)
- [Frozen runtime locations and hashes](20261013T000952Z/runtime_manifest.json)
- [AGY monitoring and authorized autonomous follow-up](20261013T000952Z/MONITORING.md)
- [Bounded recovery of two terminal baseline capacity failures](20261013T000952Z/recovery_01/PROTOCOL.md)

The launcher audits each condition after its cohort ends. Consult its report
and audit before quoting a full-cohort score. This is one exploratory warm-up
replicate per condition; it does not isolate the three changes, establish
held-out performance, or certify an invoice cap.

Completed: revised **89.448630%**, recovered baseline **89.265062%**. See the [qualified comparison and step-4 gate](20261013T000952Z/COMPARISON.md) and [final recovered baseline report](20261013T000952Z/recovery_02/baseline/report.json).

The authorized follow-up also completed: [step-4 final report](../17_restart_history/20261013T084641Z/FINAL_REPORT.md), **89.904622%** versus **89.448630%** revised control. The entire monitoring workflow is complete.
