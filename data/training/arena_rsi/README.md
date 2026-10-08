# Arena-style RSI/RL dataset

One corpus of **2,107 original Lean proof-refactoring tasks**, using the Arena
schema and original proof-token denominators.

| Split | File | Tasks |
| --- | --- | ---: |
| Train | [train.jsonl](train.jsonl) | 2,057 |
| Validation | [validation.jsonl](validation.jsonl) | 50 |

The Arena [benchmark](../../benchmark_data_warmup.jsonl) is the test set.
Validation covers 42 source/problem groups: 30 LeanPool, 6 ArkLib, 5 Strata,
4 PhysLib, and 5 main Putnam problem proofs. It spans four proof-token bands
(below 500, 500–999, 1,000–1,499, and at least 1,500 tokens), with 20, 3, 13,
and 14 examples respectively. CSLib's sole example stays in training.
No source/problem group crosses train and validation. The JSONL filename defines the active split.
Rows retain their original extraction metadata (including historical split labels)
to preserve task identities and existing reference-cache keys.

These are RSI/RL tasks with original proofs as baselines, rather than supervised
pairs of original and improved proofs. All rows passed source-fidelity and
selection audits. **62 tasks have compiler evidence and 22 have prepared heartbeat
baselines**; bulk compilation and baseline preparation remain pending.

Source archives, licenses, provenance, audits, setup files, and compiler evidence
are retained outside this folder at
`.proof-eval/training/arena_rsi/artifacts/` from the repository root.
Metadata evidence paths are relative to that directory. The pinned source projects
and existing reference caches remain in place. See its `SETUP.md` for evaluation.
