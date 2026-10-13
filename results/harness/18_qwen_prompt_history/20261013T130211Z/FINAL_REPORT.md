# Qwen prompt 1–4 completed

Qwen/Qwen3.8-Flash-Next/xhigh achieved **81.769564% local combined score**, with all **15/15 theorems complete**, all **36 required version checks passing**, and the saved-evidence audit independently repeated successfully. This is a local result, not an organizer score.

| Metric | Historical Qwen | Prompt 1–4 Qwen | Difference |
|---|---:|---:|---:|
| Combined | 79.521934% | 81.769564% | +2.247629 pp |
| Heartbeat reduction | 80.533871% | 82.868760% | +2.334889 pp |
| Length reduction | 58.031932% | 62.439932% | +4.408000 pp |
| Compatibility | 100.000000% | 100.000000% | +0.000000 pp |

Ten theorems improved and five regressed. Largest gains: SKI parallel reduction (+12.0865 pp), Binius fiberwise distance (+11.1749 pp). Largest regressions: CallElim extractedOldExprInVars (-6.1787 pp), Wick algebra (-4.0438 pp). All theorem results are in [FINAL_COMPARISON.json](/localhome/milikic/proof-reduction-competition/results/harness/18_qwen_prompt_history/20261013T130211Z/FINAL_COMPARISON.json).

## Condition and completion

One full 15-theorem cohort, original/D0 seeds, native Lemex, three workers, 3420 seconds per whole problem including host tools and final cleanup. The revised prompt, feedback, strategy cards and bounded restart history used the frozen Sol step-4 runtime. No solutions were transferred from another condition.

Started 2026-10-13 13:04:17 UTC; finished 17:49:38 UTC (15:04–19:49 Zurich). All 15 outcomes were controlled deadline stops preserving checked proofs. Run and audit exited 0; no manual recovery or additional experiment was launched. Generation outcomes: {'received': 32, 'budget_exhausted': 8}. No terminal transport errors were recorded. Final cleanup added 0 mean score points; no incomplete cleanups.

The fresh audit verified 510 saved checks, 719 version outcomes and 40 requests. It rechecked saved evidence and arithmetic, without new Lean runs or model calls. Selected proofs retain all 36 passing required-version checks.

## Usage and restart history

40 model calls, 3,049,496 reported completion tokens, **8 calls with unknown usage**, 471 agent tool checks and 145 improvements. Completion-token counters are incomplete. **Total cost remains unknown** because gateway prices are unreported. This was a time-budget condition; the generic report's $3 field was inactive and is not a spend cap.

Restart ledger: {'model_note': 23, 'source_observation': 76}; 8 theorems stored model notes. 40 requests included the bounded history object; nonempty sections by request: {'host_checked_trials': 25, 'retrieved_source_observations': 24, 'unverified_model_notes': 21}. Maximum serialized history: 11990 characters (limit 12,000). Model notes remain explicitly unverified; host-checked results are separate. These usage counts do not establish a causal benefit from history alone.

## Comparison limits and disposition

Historical Qwen is descriptive only: runtime, prompts and native CLI changed. Its original saved audit passed; a fresh historical re-audit could not resolve the pinned historical src/proof_eval/harness/audit.py source (SHA-256 94c6c25061c8e8d9c5b9f12953246ad87262203ebfb95fdecf923d0810e73aa0). Historical selected-proof validity and score means were read and recomputed from saved results; historical evidence was not modified. The current Qwen fresh audit passed.

The +2.247629 pp historical difference is encouraging but cannot be attributed to prompts 1–4 alone. Sol's 89.904622% is on a separate model/budget track. No default adoption, replication or further model condition is authorized by this workflow.

[Fresh audit confirmation](/localhome/milikic/proof-reduction-competition/results/harness/18_qwen_prompt_history/20261013T130211Z/qwen_final_audit_confirmation.json), [runtime and native binary pins](/localhome/milikic/proof-reduction-competition/results/harness/18_qwen_prompt_history/20261013T130211Z/runtime_manifest.json), [full metrics and hashes](/localhome/milikic/proof-reduction-competition/results/harness/18_qwen_prompt_history/20261013T130211Z/FINAL_COMPARISON.json), [launch completion](/localhome/milikic/proof-reduction-competition/results/harness/18_qwen_prompt_history/20261013T130211Z/launch_complete.json). Historical and current result/config/request bytes remain unchanged.
