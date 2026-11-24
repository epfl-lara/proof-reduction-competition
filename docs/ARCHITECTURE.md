# Runtime overview

## Preparation

`setup-namespace.sh` selects read-only mount protection and calls `setup.sh`.
Setup materializes the checksum-verified bundle in the shared work directory,
downloads pinned public assets, restores the Lean projects, installs isolated
harness and serving environments, and measures the original proofs on every
required Lean version. `bundle.json` and the dependency manifests pin the inputs.

## Search

Ten proof workers share one local vLLM server. Each problem receives one
28,620-second budget across its native attempts. A Codex tool loop explores
proof edits using the same [seven-card strategy bank](STRATEGIES.md).
The host checks candidates, keeps the reference measurements fixed, and accepts
only changes that pass every required version and improve the combined score
by more than 0.02 points. Native clients cannot write the trusted source or
measurement records.

## CPU cleanup

`run-namespace.sh` first completes model search, exports the model proofs and
stops the server. It then runs CPU cleanup with 32 workers by default. Cleanup
uses no model and keeps only certified score improvements. `--no-cleanup` ends
after model delivery; `cleanup.sh` can run later in a separate CPU allocation.
Per-method failures retain the best certified proof. A global cleanup failure
exports the sealed model-proof set with an explicit fallback status.

## Outputs

`model-submission.jsonl` contains the model-stage proofs;
`submission.jsonl` contains the final export. Export verifies exact benchmark
membership, proof bytes, fixed references and every required version certificate.

Check the command's successful exit and `search-ready.json` with
`search_completed: true` for model delivery. For a cleaned result, also check
`submission-ready.json` with `cleanup_completed: true`; a fallback is not a
completed cleanup. `search-timing.json` and `timing.json` record phase timings.
Native traces, verification records and diagnostics remain in the run directory.
