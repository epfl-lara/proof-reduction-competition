# Bounded restart history

The [step-4 protocol](20261013T084641Z/PROTOCOL.md) tests same-theorem host history on the winning revised 1–3 configuration. The control scored 89.448630%; the new run starts from original/D0 seeds with gpt-6.1-sol/max, five workers and $3 per theorem.

- [Runtime pins](20261013T084641Z/runtime_manifest.json)
- [Matched configuration check](20261013T084641Z/matched_preflight.json)
- [Gate decision](20261013T084641Z/comparison_decision.json)

Status and results belong to the saved run report; prepared inputs alone do not mean the cohort has launched or completed.

Launched at 2026-10-13 08:50:20 UTC with five live native workers. [Launch identity](20261013T084641Z/launch.json), [validation](20261013T084641Z/validation.json), [live report](20261013T084641Z/history/report.json). AGY monitors completion and confirmed failures.

Completed and audited: **89.904622%**, versus **89.448630%** for revised control (**+0.455991 pp**); 10 theorem gains and 5 regressions. All 15 complete and all 36 required version checks passed. [Final report](20261013T084641Z/FINAL_REPORT.md) and [exact comparison](20261013T084641Z/FINAL_COMPARISON.json). The monitor is stopped; restart history remains opt-in.
