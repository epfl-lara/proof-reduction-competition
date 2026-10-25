# Direct policy training

The maintained implementation is `src/proof_eval/training`. `proof-train` is a
thin entrypoint in `proof_eval.interfaces.training`. Importing the package or
requesting CLI help does not start a compiler, model, optimizer or job.

The current configured baseline uses the original Qwen3.8-Flash-Next BF16 model,
GRPO with rank-8 LoRA, four rollouts per problem and two problem groups per update.
Only the disjoint 200-task RL reserve is eligible; the SFT source set and 50-task
validation reserve are checked for overlap. This is adapter training, not a full
base-weight update. The initial curriculum uses complete 32,768-token contexts,
30-minute episode boundaries and no cross-rollout history. Eight-hour,
266,400-token runs are the matched evaluation target, not an observed result.

## Storage and container responsibilities

Use the pinned training container for CUDA, PyTorch, vLLM, Megatron-SWIFT and Lean.
The RCP image activation selects a persistent mounted `ELAN_HOME`; its default
Lean4.32 compiler alone does not satisfy every benchmark version. Benchmark
projects, their exact Git revisions, installed additional compilers and derived
`.olean` imports are explicit assets. They may live on the cluster's Scratch PVC.
Model weights, run outputs and checkpoints are runtime assets as well. Maintained
Python source lives in this repository; cluster jobs use hash-bound frozen copies.

Always invoke the RCP environment entrypoint before the frozen package bootstrap.
Do not assume a remote shell inherited that activation. Its Python-path reset is
handled by the generic bootstrap, not by installing packages into a running image.
`training.release.freeze_release` combines the exact selected host source snapshot
with the repository's added training modules. It refuses to replace an existing
host module or overwrite an earlier release. Source, dataset, authorization and
repository identities are pinned separately from the large runtime assets.

An existing sealed host can be selected without replacing its frozen verifier.
The training session adapter installs its freshly checked original baseline
before the first state write. Explicit, hash-pinned host extensions may add a
missing module, but may never overwrite a module in that selected snapshot.

## Explicit preparation

```bash
proof-train --help

# Original references only; no model generation or optimization.
proof-train prepare --dataset-dir /absolute/dataset \
  --environments /absolute/environments.json --output /absolute/new-preparation \
  --system-prompt /absolute/refactor_system.md --workers 4

# Frozen release, actual container wiring, meta-device attention check and tests.
proof-train preflight --release /absolute/release --plan /absolute/release/plan.json

# Dependency imports only, with a separate explicit preparation plan/output.
proof-train prepare-imports --release /absolute/release \
  --plan /absolute/release/plan.json

# Explicit model/optimizer execution. Neither help nor preparation submits a job.
proof-train run --release /absolute/release --plan /absolute/release/plan.json
```

Build imports from each task's actual source-file header or standalone header.
A declaration snippet is not its import context. Dependency builds preserve source
and Lake configuration hashes and use finite, recorded process groups. Run these
CPU preparation steps before reserving GPUs. Reuse completed build artifacts;
never repair source proofs to make preparation pass. Missing infrastructure is a
preparation failure, not a zero-score model example.

Reference preparation can use a bounded thread pool. Each task owns its immutable
report and pack; cache writes retain the evaluator's per-reference locks. The final
manifest and training examples retain dataset order regardless of completion order.
The run refuses model admission on unresolved original reference preparation.
Only explicitly declared originals with a compiler-confirmed `sorryAx` dependency
may be excluded; keep their failed preparation records and the full cohort count.
Timeouts and missing environments never qualify for that exclusion.
Context-length exclusions stay explicit; contexts are never silently truncated.

The explicit `--timeout-retries 1` preparation policy records one further attempt
only after a completed wall timeout, selecting only the timed-out versions.
Both attempts remain saved. Semantic failures, unavailable evidence and an
interrupted/indeterminate attempt are never retried automatically. A frozen plan
may select this separately for reference preparation and fresh episode originals;
the latter uses a new private candidate cache and the existing episode clock.

## Objective and evidence

Reward is `(host-verified final best Arena score - original score) / 100`.
Only a proof passing every required version may replace the host incumbent.
Intermediate verified improvements are diagnostic potential differences; they
are not added to terminal gain a second time. There is no format, tool-count or
unverified proof-step bonus. Unavailable verification, missing exact token evidence
or failed ownership checks must not become reward zero.

The training frontend is a ReAct adapter to the Arena host proof/source tools.
It differs from native Lemex and must be described that way. Exact sampled IDs,
behavior logprobs, context/tool masks and policy versions are retained. Optimizer
receipts record successful updates, finite gradient norms and before/after hashes;
checkpoints retain file hashes. Save after every update. Allocation, downloads,
preparation, unit tests and a zero-gradient step are not proof of learned weights.

Training reward means need their actual sample/problem denominator. Claim an
improvement only after a matched held-out base-versus-adapter assessment using the
same precision, harness and evaluation budget. SFT preprocessing and SFT-plus-RL
remain separate comparisons; never train a glob of unaudited raw collection files.

## Full host tool readiness

The training image also needs the optional LeanExplore dependencies and explicit
cached corpus/embedding assets. `containers/training-tools` builds a derived
image from the exact existing CUDA/Lean image and checks that previously installed
packages retain their versions. No dependency is installed into a productive job.
Both CPU preflight and runtime hash the declared assets and execute an actual CPU
embedding/search query before preparing originals. This is one embedding call,
zero policy-model calls and no optimizer step. Missing tools cannot be disabled
silently or discovered only after original preparation.

A declared, hash-bound `original_reference_seed` may transfer successful original
reference denominators from a terminal pre-policy run. The importer checks every
source pack, exact original code, version, environment fingerprint, positive
measurement and raw cache hash, then creates receiving cache keys while retaining
the original measurement's machine/time. Candidate and analysis caches are never
imported. Preparation records cache reuse explicitly; source-invalid originals
are rechecked rather than imported. Every actual rollout still measures the
original afresh inside its own unchanged episode clock.
