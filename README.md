# EPFL-LARA — Lean Refactor Arena

**1st place, open-source LLM track**, in [Lean Refactor Arena](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena) at [VeriCodeGen: AI for Verifiable Coding](https://vericodegen.github.io/), NeurIPS 2026.

This repository contains our competition submission. Ten proof workers use
Qwen3.8-Flash-Next-FP8 through a Codex harness, guided by seven strategy cards.
vLLM serves the model with FP8 weights, multi-token prediction and prefix reuse.
CPU cleanup simplifies the resulting proofs. Every accepted change passes all
required Lean versions.

## Setup

Use **four A100 80 GB GPUs** for search and shared storage with roughly **500 GB**
free for weights, Lean projects and outputs. CPU setup and cleanup need no GPUs.
Build the included [Docker image](docs/IMAGE.md), then run these commands inside
it. The host must allow nested user/mount namespaces; see [host requirements](docs/HOST_REQUIREMENTS.md).

```bash
bash check-host.sh --backend readonly-mounts --directory /shared/arena-guard-checks
bash setup-namespace.sh /shared/arena-work
```

Setup downloads pinned public dependencies and weights, builds the Lean projects
and measures the original proofs. Keep the same shared paths for every phase.

## Model search and cleanup

In the four-GPU allocation:

```bash
bash run-namespace.sh /shared/arena-work /shared/arena-output
```

All **60 problems** receive **28,620 seconds (7 h 57 min) each**, with ten running
in parallel: six waves, about **47 h 42 min** of search. Preparation and model
loading precede search; final export and cleanup follow it. The workflow records
each phase separately. We count GPU model search, including tools and Lean
checks, toward the competition's 48-hour budget.

**CPU cleanup is enabled by default with 32 workers.** It makes no model calls
and starts after the model server stops. Append `--no-cleanup` to export the
model proofs directly. To release the GPU allocation before cleanup, finish that
run with `--no-cleanup`, then use the same paths in a separate CPU allocation:

```bash
PROOF_EVAL_FILESYSTEM_BACKEND=readonly-mounts \
  bash cleanup.sh /shared/arena-work /shared/arena-output
```

The final file is **`/shared/arena-output/submission.jsonl`**. The workflow also
preserves `model-submission.jsonl` before cleanup. Check successful completion
and the [output records](docs/ARCHITECTURE.md#outputs) before using either file.

## Team

Lazar Milikic, Gordan Duric and Viktor Kuncak — **EPFL** ([website](https://epfl-lara.github.io/)).  
Contact: [lazar.milikic@epfl.ch](mailto:lazar.milikic@epfl.ch).

[Strategy bank](docs/STRATEGIES.md) · [Runtime overview](docs/ARCHITECTURE.md) · [Third-party licenses](THIRD_PARTY.md)
