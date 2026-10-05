# Deterministic batch interface

Use `proof-deterministic` or `proof_eval.optimization.batch.run_batch` for a new competition batch. The input follows the competition row schema; names, sources, size and versions come from that file. See [architecture](ARCHITECTURE.md) for package boundaries.

## Prepare once

Run these from the repository root in the `af` environment. Replace `full.jsonl`
with the downloaded competition dataset; it is a placeholder path. Setup requires
the source URLs, exact commits and file context supplied by the competition.

```bash
proof-setup \
  --dataset data/full.jsonl \
  --environments environments.full.local.json \
  --root .proof-eval-projects/full --workers 1

proof-benchmark \
  --dataset data/full.jsonl \
  --environments environments.full.local.json \
  --cache .proof-eval/full \
  --output .proof-eval/full/reference_values.jsonl
```

The processor reuses matching local measurements. Do not pass `--refresh` during
optimization. Cached references and their export must cover every listed version.
New versions or dependency revisions require their matching Lean environments.
The current environment map identifies a project by `(source, version)`; rows with
that pair must agree on its source commit. A changed upstream dataset schema or
conflicting pins require an adapter before running.

## Run or resume

```bash
proof-deterministic \
  --dataset data/full.jsonl \
  --environments environments.full.local.json \
  --cache .proof-eval/full \
  --references .proof-eval/full/reference_values.jsonl \
  --output results/deterministic/full_batch_v1 \
  --workers 8 --max-rounds 6 --max-trials 64 --max-sites 6 --max-sweeps 2
```

The batch CLI can also run from another working directory: use the installed command
and absolute input/output paths. Relative arguments resolve against the
caller's directory; child runners execute in the repository. All ten methods run
from the dataset originals, followed by bounded repeat sweeps. A changed proof is
retained only when its fully evaluated combined score improves by more than
`--min-gain` (default 0.05 percentage points). Every required version is requested
before accepting a candidate. Compatibility remains part of the competition
objective, rather than an additional hard 100% acceptance constraint.

`--methods wrappers facts` selects a smaller explicit method set for a pilot;
`--max-sweeps 0` runs just its first pass. Budgets are per problem and method.
These bounds are not a total wall-time/resource cap: measure throughput on the
new batch before selecting the final resource budget. This runner uses the newer
resumable stage engine for all methods; it does not promise byte-identical
reproduction of the older warm-up linter/simplifier search policy.

Repeat the identical command to resume. A batch lock prevents simultaneous
writers. Inputs, environments, source hashes and budgets must still match; use a
new output folder when they change. Completed stages reuse their recorded
results; unfinished stages resume candidate checkpoints. A recorded unavailable
discovery stops the batch and requires investigation, then a fresh output folder
for a retry of that failed discovery.

The runner checks references read-only before optimization and audits their
unchanged values at completion. It does not install environments, prepare
references, call models, train models or submit to the arena.

## Harness contract

Standard output contains one JSON manifest. Child progress goes to standard
error. Exit code **0** means the configured portfolio finished, all selected
results were fully scored, and the final audit passed. Exit code **2** means an
input/preparation problem, unavailable stage, or caught execution/audit error;
signals and uncaught process failures may use other nonzero codes. Always check
the exit code and `status`, not just whether a file exists.

The output directory contains:

- `submission.jsonl`: one `{ "name": ..., "proof": ... }` record per dataset row,
  published atomically after the complete evidence audit.
- `batch.json`: configuration, stage scores, stop reason, submission hash,
  problem/version counts and final component scores.
- `audit.json`: proof hashes, accepted transitions, score arithmetic, source
  checks and cache checks.
- Numbered stage folders with selected proofs, per-problem outcomes, rejected
  trials and checkpoints; `deterministic_comparison.json` and `.csv`.

On interruption, `batch.json` identifies the active stage and last completed
stage's candidates. A nonzero result is not a completed submission. Even a zero
result can stop at a configured search limit; it does not certify exhaustion.

Python callers with this repository's `src` on `PYTHONPATH` can use the same API:

```python
from proof_eval.optimization.batch import BatchConfig, run_batch

result = run_batch(BatchConfig(
    dataset="data/full.jsonl",
    environments="environments.full.local.json",
    cache=".proof-eval/full",
    references=".proof-eval/full/reference_values.jsonl",
    output="results/deterministic/full_batch_v1",
    workers=8,
))
if result["status"] == "finished":
    submission = result["submission"]
```

The API returns `unavailable` when a child stage cannot finish, and raises for
configuration, process or audit errors. It leaves durable evidence for diagnosis.
The general-batch integration test uses a separately created Lean project and a
new one-problem dataset, exercises all ten methods and resume from outside the
repository, and checks that cached reference bytes remain unchanged. The full
competition batch itself has not been tested before its release.
