# Local open-weight models

The `lemex-local` provider runs native Lemex against a local vLLM Responses
server. It uses the maintained host proof/source tools and the current cohort
workflow. The gateway `lemex` provider remains separate and keeps its existing
authentication, catalog selection, admission limit and default model.

The local profile declares a model revision, xhigh effort, MTP3, 266,400 context,
222,400 compaction, ten local model workers, eight hours per model phase, no
cross-restart history and no deterministic cleanup. These are explicit profile
defaults for fresh local Qwen runs across the profile CLI, public RunConfig and
server configuration. Host Lean checks default to 600 seconds; the saved profile
records that limit. Other model conditions retain their separately declared
policies. The default model is
`Qwen/Qwen3.8-Flash-Next-FP8`; the ThinkingCap Flash-Next FP8 condition is also
explicitly registered. Preparation and command previews make no model calls.

The local Qwen workflow prepares originals once on CPU with a 600-second Lean limit and no automatic retry, then imports the complete hash-bound cohort and admits those records without recompiling the originals at model startup. Original preparation must finish before GPU allocation. Selected nonoriginal states still require fresh checks in the model phase.
Historical runs whose clocks began after reference preparation retain their
frozen runtime and original labels. A new checkout is not a byte-identical
replacement for those historical releases.

## Prerequisites

Use Linux and Python 3.12 for the local runtime. Install the harness with its
development dependencies and prepare the source projects, environment map,
prepared input cohort and references described in the main README. Keep compiler
artifacts on persistent storage and use private candidate/analysis caches.

The validated serving stack was vLLM 0.31.0+cu129, Torch 2.13.0+cu129 and
Transformers 5.17.0. Native Lemex must support the Responses/profile flags used
by this adapter; the executable, configuration and catalog are pinned at
preflight. This repository does not redistribute a native client executable,
model weights, credentials, a private registry image or a trained adapter.

On A100, install the supplied lookup-only PLE compatibility plugin into the
serving environment:

```bash
python -m pip install -e '.[dev]'
python -m pip install -e integrations/vllm_ampere
```

The plugin is specific to that vLLM kernel API. It copies FP8 embedding bytes
without converting model weights. Other vLLM versions require their own
compatibility validation. Use the same serving precision for a matched model
comparison; a BF16 RL checkpoint versus a historical FP8 run is not an isolated
measurement of training gain.

Native-local process ownership uses a host-owned subreaper, Landlock and the
validated seccomp signal broker. Existing providers retain their PID-namespace
boundary. The current broker source and ELF hashes are pinned in
`providers/signal_scope.py`; point `PROOF_SIGNAL_SCOPE_BINARY` at the validated
binary in the pinned production image. An arbitrary locally compiled binary is
not silently admitted. Generic offline CI skips these kernel integrations when
the binary is absent; the production-image gate must run them with it present:

```bash
export PROOF_SIGNAL_SCOPE_BINARY=/path/to/validated/signal-scope
export PROOF_SCOPE_NATIVE_BINARY=/path/to/pinned/lemex
export PROOF_SCOPE_NATIVE_CATALOG=/path/to/prepared/models.json
python -m pytest -q tests/test_final_deadline_contracts.py \
  tests/test_signal_scope.py tests/test_signal_scope_native.py \
  tests/test_signal_scope_threads.py tests/test_owned_client_eof.py
```

The native integration fixture also pins its Lemex executable hash explicitly;
use that validated bundle for this gate. Its HTTP responses are deterministic
localhost fixtures, with no real model or Lean search calls.

## Freeze a profile and preview it

Choose a fresh run directory outside tracked result archives:

```bash
proof-local-vllm prepare --profile runs/local/profile \
  --model-cache /persistent/models
proof-local-vllm serve --profile runs/local/profile --dry-run
```

For the separate ThinkingCap condition, prepare another directory:

```bash
proof-local-vllm prepare --profile runs/thinkingcap/profile \
  --model bottlecapai/ThinkingCap-Qwen3.8-Flash-Next-FP8 \
  --model-cache /persistent/models
```

`profile.json` records the exact model revision and hashes of the private native
config/catalog. Download that exact revision into the selected Hugging Face
cache before serving; startup is offline and does not substitute another model.
Changing context, revision, capacity or native settings requires a new profile.
The profile leaves the user's normal Lemex home and credentials untouched.

## Run the maintained harness

After approving the concrete cohort and resource allocation, run:

```bash
proof-local-vllm run --profile runs/local/profile --output runs/local \
  --plugin integrations/vllm_ampere -- \
  --base /persistent/prepared-inputs \
  --dataset data/benchmark_data_warmup.jsonl \
  --references /persistent/reference_values.jsonl \
  --environments /persistent/environments.json \
  --cache /persistent/private-evaluation-cache
```

Arguments after `--` go to `proof-harness run`. Model, effort, workers, deadline,
output and restart history come from the frozen local profile. The local recipe
disables both cohort cleanup phases; the ordinary `proof-harness` Qwen default
also runs model-only. Other model conditions keep their before/model/after phases;
explicit cleanup flags remain available. Shared gateway concurrency is
not reused as local GPU capacity.

On each new GPU configuration, run the real full-window pressure and native/tool
capture checks before describing the configured concurrency as admitted. A
preview, allocated GPU, `/models` response or advertised context size is not that
measurement. `providers/capacity_probe.py` provides the synthetic pressure check;
its requests are separate from theorem clocks and native sampling defaults.

The local run captures attributed request/response body bytes and hashes through
the loopback proxy. The host keeps full tool request/response wire bytes in
`tool_rpc.jsonl`; registration credentials are omitted from the native child.
Raw reasoning, native events, candidates and Lean verdicts remain in the run
directory. Unknown requests are never automatically replayed.

At a deadline, native cleanup receipts bind exact PID/start ticks and reaping.
If only the enclosing theorem worker appears in the outer cleanup snapshot,
recovery uses the matching durable native receipt. Missing or inconsistent native
custody produces an explicit incomplete result retaining the saved best proof;
it does not become a clean trajectory or a zero reward. Historical refusals and
source bytes remain unchanged.

## RCP and source synchronization

[`examples/rcp/submit-local.sh`](../examples/rcp/submit-local.sh) previews one
four-GPU RunAI job. It requires explicit project/image/user/PVC/release paths and
only submits with `--submit`; a saved submission intent prevents blind retries.
Use a source-frozen release on the mounted PVC, not a checkout another machine
is editing. The post-entrypoint Python bootstrap restores that release's import
path after image activation sanitizes `PYTHONPATH`.

Develop from a fresh branch of the current remote main. Preserve dirty remote
worktrees separately, merge changes by responsibility, run offline and pinned
Linux gates, then publish the branch for review. Do not replace a newer checkout
with an older experiment runtime. Keep bulky raw runs, checkpoints and model
caches outside Git; preserve their immutable manifests and persistent archives.
The direct-RL experiment remains separately staged until real optimizer and
checkpoint evidence exists; this local provider guide does not approve raw SFT
files as training input.
