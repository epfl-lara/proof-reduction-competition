# Deterministic cohort cleanup

`proof-deterministic` runs the measured one-sweep schedule independently of model
jobs. It visits all sixteen methods once in the gain-based order, with per-method
rounds=3, trials=32 and sites=6. There is no five-minute phase cap. Every retained
change must pass every required version and improve combined score by >0.05 points.

## Inputs and setup

The defaults select the frozen 15-theorem warm-up input packs. For another cohort
(for example 50 theorems), supply its dataset, pinned environment map, cached
reference export and prepared input directory. A prepared directory contains
`config.json` with the exact names/input/source identities and `inputs/*.json`
containing each original dataset row, references and source context. This is the
same input contract used by the model harness; see [architecture](ARCHITECTURE.md).

Setup/reference preparation are separate:

```bash
proof-setup --dataset data/full.jsonl --environments environments.full.local.json \
  --root .proof-eval-projects/full --workers 1
proof-benchmark --dataset data/full.jsonl --environments environments.full.local.json \
  --cache .proof-eval/full --output .proof-eval/full/reference_values.jsonl
```

Use the unmodified dataset and matching source versions. General candidate checks
never refresh reference denominators implicitly. The initial proof is measured
separately for each cleanup cell.

## Run or prepare

```bash
# Warm-up cohort, originals, eight independent theorem workers.
proof-deterministic --output results/cleanup_warmup --workers 8

# Another prepared cohort; paths are explicit and work from any directory.
proof-deterministic --base /path/to/prepared_inputs \
  --dataset /path/to/full.jsonl --environments /path/to/environments.local.json \
  --cache /path/to/reference_cache --references /path/to/reference_values.jsonl \
  --output /path/to/new_cleanup --workers 16

# No compiler/model calls: cached-reference and runtime preflight only.
proof-deterministic --output results/cleanup_warmup --workers 8 --prepare
```

Workers are a positive integer, default eight. Parallelism is across theorems;
each theorem's ordered sweep remains sequential. Finite method limits and
individual verifier/discovery watchdogs remain explicit. Discovery timeouts keep
valid incumbents and are labelled limited outcomes; other failures keep the cohort
incomplete. A failure does not cancel other queued theorems.

## Explicit proof reuse

```bash
proof-deterministic --starting-proofs results/earlier_cleanup/state.json \
  --output results/another_sweep --workers 8

# Model output manifests carry their model/effort lineage.
proof-deterministic --starting-proofs /path/to/model_state.json \
  --condition gpt-6.1-sol:max --output results/post_model_cleanup --workers 8
```

An input may be a portable `state.json`, a directory containing it, or a complete
name/proof JSONL. It must cover the exact cohort and retain theorem statements.
Raw JSONL has external provenance; imported scores are informational only.
Original and selected proofs are freshly checked in a private cache. Denominators
stay fixed, and a labelled model-produced input cannot cross model conditions.

Identical resumes audit completed cells and make no new calls for them. Changed
inputs, settings or runtime require a new output. An interrupted started cell is
not automatically replayed; inspect its evidence and explicitly configure recovery.

## Outputs and audit

A complete audited cleanup produces `state.json` with selected declarations,
identities, source scores and lineage. `cells/` retains measurements, trials,
verified search nodes, results and audits. `report.json` distinguishes mean input
score, output score, gain, actual batch elapsed time and summed per-cell durations.
Incomplete cohorts have no full-cohort mean or reusable selected-state export.

```bash
proof-deterministic --output results/cleanup_warmup --report
proof-deterministic --output results/cleanup_warmup --audit
```

These reads dispatch no Lean or model work. Exit zero means the requested action
completed/prepared/passed; incomplete or failed actions exit nonzero. A complete
one-sweep is a finite search outcome, not an optimality claim.

For automatic before/model/after orchestration use `proof-harness run`. Its
`--cleanup-workers`, `--before-workers`, `--after-workers` and `--model-workers`
select independent pools; `--no-cleanup-before` avoids rerunning a prepared state.
The older multi-sweep `optimization.batch` API remains available for historical
reproduction, but is no longer the `proof-deterministic` CLI default.
