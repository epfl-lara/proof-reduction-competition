# Sol 6.1 cleanup placement: completed October 22

All runs use the same 15 original warm-up proofs, Sol 6.1/max, history off,
five model workers, a $3 estimated API-equivalent target per problem and no
model wall-time watchdog. Cleanup uses the one-sweep plan with eight workers.
These are local combined scores, not organizer results or proof pass rates.

| Completed configuration | Model score | Final score | Initial cleanup | Model phase | Final cleanup | Whole workflow |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Cleanup before and after | 89.2971% | 89.3761% | 43m 30s | 2h 59m 47s | 15m 16s | 3h 59m 24s |
| Cleanup only at the end, fresh rerun | 89.5856% | **89.6591%** | None | 3h 3m 38s | 12m 57s | **3h 17m 3s** |

The end-only rerun finished **0.2831 percentage points higher and 42m 21s sooner**.
Each configuration is one run; this does not establish repeatability or a causal
advantage. The rerun also contains the native budget-reminder correction in
commit `8d569f98de06c868d0110331e46fed096e146096`. Prompts, native CLI, inputs,
references, model, effort, worker counts, history and budgets otherwise match.
The repository default remains cleanup before and after; end-only was explicitly
selected for these experiments.

Final cleanup added **0.07355 points** to its freshly checked inputs and improved
eight of the fifteen proofs. The final mean proof-token reduction is **81.0882%**,
heartbeat reduction **87.8892%**, and compatibility **100%**. Both complete runs
passed all **36 required final version checks** and their full pipeline audits.
The end-only run completed 204 model requests with 1,151,363 recorded output
tokens. One temporary model-capacity failure recovered under the existing bounded
policy; no cells remained incomplete. Its completion time was October 22 at
14:42:33 UTC (16:42:33 Europe/Belgrade).

## Cost and timing interpretation

The end-only rerun recorded **$45.0808244 API-equivalent cost**, with no unknown
usage calls. All fifteen problems slightly exceeded the approximate $3 target
at native response boundaries; the maximum was **$3.0145232**. These are estimates
under the pinned rate assumptions, not invoices or a certified hard dollar cap.
The before-and-after run recorded $45.0993708 with one unknown-usage call; its
missing usage must not be treated as confirmed zero cost.

Phase times above include phase orchestration. Cleanup's internal worker-batch
time was 12m 44s for the end-only rerun, with 1.175 summed worker-hours. Whole
workflow time includes all phase transitions. Model-only time is not total time.
Fresh cleanup verification can produce tiny differences from saved model scores;
cleanup gain uses its own freshly measured input score.

## Preserved interrupted run

The first end-only run finished fourteen model cells but left
`Fsub.Typing.progress` incomplete. With roughly $0.0000208 remaining, it requested
a one-token limit and a reminder at one token; the native CLI rejected that
configuration. Its verified incumbent was retained, and final cleanup did not
start. This run has **no full-cohort final score** and is excluded from the table.
The corrected rerun started every problem from its original proof, using fresh
measurements and private caches; it reused no partial model outputs.

## Files and evidence

- [Comparison metadata](comparison.json) includes settings, phase reports,
  incomplete outcomes and hashes linking the compact bundle to raw evidence.
- [Per-theorem scores](theorem_scores.csv) contains both complete cohorts.
- [End-only final proofs](end_only_rerun/proofs.jsonl) and
  [before-and-after final proofs](before_and_after/proofs.jsonl) each contain
  fifteen organizer-format `name`/`proof` records. These are model-produced
  outputs, not deterministic starting sets or submitted organizer results.
- Each complete condition's `selected_proofs.json` preserves the final
  declarations, all-version evaluations, model scores and source-result hashes.
- Each condition's `source/` directory contains byte-identical saved reports,
  configurations and audits. The interrupted condition has only a model evidence
  audit, not a successful pipeline audit.
- [Archive receipt](archive_receipt.json) identifies verified private copies of
  all three raw runs outside the checkout. Original raw files are retained too.
  Compact publication files do not include full request logs, caches or runtime
  dependencies and do not by themselves enable a full raw-evidence audit.
