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

Tool dispatch reads the final answer after a completed leading Qwen reasoning
block. Quoted action examples inside reasoning are not tool calls. JSON is decoded
before checking the closing action tag, preserving literal tags inside Lean
strings. The complete original reasoning, input messages, sampled token IDs and
log probabilities remain unchanged in saved training evidence.

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

## Training-library and tool-model isolation

Megatron's bridge registers legacy rotary initialization globally in Transformers.
Loading an auxiliary Qwen embedding model later in that same interpreter can fail
even when the initial tool preflight passed. Training semantic queries therefore
run in fresh, finite CPU processes using the unchanged host search implementation,
explicit frozen assets and the same version/project scope. The child masks GPUs
and removes distributed-rank variables; request, PID/start tick, source, result,
exit and failure receipts remain under the owning trajectory. It never samples
the policy or automatically repeats an unknown call.

Preflight replays the saved failing search request after invoking the real bridge
registration and confirms that the parent policy's registry remains unchanged.
A CPU Gloo rendezvous communicates rollout infrastructure failures before the
next model collective. A failed tool batch retains its raw evidence and aborts
without a synthetic reward or optimizer update.

After a known terminal, pre-update policy attempt, a hash-bound archive can declare
which task IDs already consumed policy calls. Continuation admits the remaining
cohort explicitly, preserving interrupted attempts and the full original reserve
accounting. A learned checkpoint or optimizer receipt prohibits this fresh-base
continuation and requires exact learned-state recovery instead.

## CPU host execution during training

The productive job starts one small CPU host process before loading the GPU
trainer. Rollout workers send it source-bound JSON requests over a private local
socket. The process owns the original measurements, independent proof sessions,
tool calls and score state. It uses the same frozen verifier and original
denominators. Model inputs, outputs, sampled tokens and log probabilities survive
the transport unchanged, with request/result hashes and both caller and server
PID/start-tick receipts. An unknown call is never automatically repeated.

This keeps Lean subprocess startup and tool-model imports outside the large CUDA
interpreter. Each episode still starts its original clock before its fresh
measurement, counts model-generation time and keeps private candidate caches.
The service has no policy model, masks GPUs, rejects callers outside the original
driver's process tree and ends with that job. Its own finite lifetime and closure
are recorded on HOME and Scratch. It is a productive host-tool component, not an
additional cluster job or a permanent monitor.


The rollout engine can explicitly select eager execution and disable prefix caching
with `vllm_enforce_eager` and `vllm_prefix_caching`. These settings preserve complete
inputs and the model/context budget while avoiding the cached GPU execution path
that failed on a growing conversation. A configured `gpu_runtime_probe` exercises
three synthetic growing conversations per rank in the actual loaded engine before
Arena policy requests. Its independently seeded inputs/outputs are labelled as GPU
preflight, never scored, optimized or added to the training dataset. Failed probes
stop without retry; successful probes leave model parameters and optimizer state
unchanged. Every terminal pre-update policy lineage can be listed in
`previous_policy_attempts`; their exact hash-bound consumed-task sets are combined
so a later repair cannot silently sample an older interrupted task again.

## Full training integration check

Inference alone does not validate the training graph. The explicit
`synthetic_gpu_training_check` fixture uses the actual GRPO trainer, full measured
32K text inputs, sampled tokens/logprobs, reference log probabilities, backward
pass, optimizer and checkpoint writer. It consumes zero Arena reserve tasks.
Its contrived fixture advantages and resulting adapters test software only:
they are labelled separately and never become Arena rewards, an improvement
claim, or starting weights for the real run. The real run always selects its
declared original base revision or an explicitly verified real checkpoint.

The training command retains the original model's native RoPE/MRoPE configuration.
An unnecessary manual YaRN override discards the Qwen model's MRoPE sections and
makes the training bridge interpret three-axis positions as ordinary RoPE. The
32K curriculum fits inside the native 262K window, so it needs no such override.
The GPU fixture checks the actual native position type and preserves all position
and input tensors. It makes no mathematical modification to the model.

After the library finishes training and checkpoint saves, colocated shutdown
offloads the trainer with its existing library helpers, wakes a sleeping vLLM
engine, and calls the engine-core client's explicit shutdown before Megatron
destroys the shared process groups. The pinned allocator cannot safely free
asleep cuMem pools; the upstream [allocator issue](https://github.com/vllm-project/vllm/issues/36651)
documents that failure. Per-rank terminal receipts preserve shutdown errors rather
than masking them. This terminal lifecycle hook changes no rollout, reward,
gradient or checkpoint and never generates another model request.

Colocated multi-turn inference must synchronize continuation across every rank
sharing the inference engine. In the eight-rank configuration, native data slicing
uses two four-rank model-parallel groups, while inference uses all eight ranks.
`colocate_multi_turn_world_sync` selects the library's existing boolean-gather
callback over the eight-rank world so early-finished workers keep participating
with empty request lists. It changes no requests, outputs, masks, rewards or
optimizer math. The explicit CPU distributed check and asymmetric GPU fixture
exercise four workers finishing at turn one and four finishing at turn three.
