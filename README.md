# Proof Reduction Competition

Workspace for participating in [Lean Refactor Arena](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena), part of the AI for Verifiable Coding workshop at NeurIPS 2026.

The task is to refactor existing Lean 4 proofs while preserving their statements, improving proof length, elaboration cost, and compatibility across the listed toolchains. Closed-source and open-source LLM entries compete in separate tracks.

## Repository contents

- [RULES.md](RULES.md): competition rules and submission requirements, checked on October 2, 2026, with pinned source links.
- [data/benchmark_data_warmup.jsonl](data/benchmark_data_warmup.jsonl): the original, unmodified warm-up benchmark.
- [.gitignore](.gitignore): Python environments, caches, build artifacts, Lean/Lake build outputs, and local credentials.

This initial setup contains documentation and benchmark data. Python dependencies, a Lean project, and the refactoring harness will be added when the implementation is selected. Each benchmark row specifies its own evaluation versions; there is no single repository-wide Lean toolchain yet.

## Initial benchmark

The warm-up dataset contains **15 declarations**, with three each from Strata, PhysLib, CSLib, ArkLib, and PutnamBench. It totals 17,595 reference proof tokens as reported by the dataset. LeanPool is listed among the competition's sources but has no rows in this warm-up file.

The local file was verified byte-for-byte against the organizer's dataset at Space revision `d9e46ee13c822925fb3031b0a0eac53b51631198`:

- [Pinned upstream dataset](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena/blob/d9e46ee13c822925fb3031b0a0eac53b51631198/benchmark_data_warmup.jsonl)
- Size: 113,826 bytes.
- SHA-256: `6209680cf00cde0765b77b24834cd72c64dd585b2f7e3f2a58209980ab59a804`.

Each JSONL row includes:

| Field | Meaning |
| --- | --- |
| `name` | Unique benchmark ID to use in a submission. |
| `source` | Source corpus. |
| `statement` | Fixed declaration statement, without `:=` and the proof body. |
| `src` | Original complete declaration, including its proof. |
| `proof_length`, `num_lines` | Reference proof token count and declaration line count. |
| `header` | Imports and options for standalone rows; empty for project-resident rows. |
| `file_path`, `url` | Source file and repository for project-resident rows. |
| `start_line`, `end_line` | Declaration location, when present. |
| `version_info` | Evaluation toolchain labels paired with pinned repository commits. |

For project-resident declarations, evaluation takes place inside the source repository at the specified revisions. For PutnamBench, the row supplies a standalone header and `version_info` identifies Mathlib release revisions. The benchmark file does not include reference heartbeat counts; the organizer stores those separately.

## Participation

1. Read [RULES.md](RULES.md) and choose a track.
2. Use the exact statement from each row and replace only its proof body. Validate in the row's repository context and listed versions.
3. Produce a UTF-8 JSONL file with a `name` and a `proof` string per submitted declaration. `proof` must contain the complete declaration, not just the tactics.
4. Upload proofs in the arena's Submit tab. Keep the submission key issued on the first successful upload outside Git.
5. For the full benchmark, submit the reproduction code archive in the arena and the technical report on OpenReview by the deadline.

The full benchmark is scheduled for **November 1, 2026**, and proofs, code, and reports are due **November 8, 2026**. See the saved rules and live competition page for updates.
