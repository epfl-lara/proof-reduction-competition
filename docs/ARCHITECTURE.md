# Runtime architecture

The maintained runtime is one installable package. CLI commands call library
APIs; no library imports an experiment driver. Historical studies stay in
`results/`; their retired source can be recovered from checkpoint `bfb2ade6`.

| Package | Responsibility | Main API |
| --- | --- | --- |
| `verification` | Pinned Lean compilation, token counts, cached references, goal observations | `Evaluator`, `check_references` |
| `optimization` | Parsed proof edits, tactic discovery, minimization, bounded cleanup, generic deterministic batches | `Budget`, `optimize`, `cleanup_proof`, `BatchConfig`, `run_batch` |
| `providers` | Native agent CLIs, durable execution/isolation, terminal usage, price estimates | `codex.generate`, `lemex.generate`, `claude.generate`, `CostConfig` |
| `harness` | Prompt/context policy, tool sessions, one-theorem search, batch coordination and reports | `ProofSession`, `ProofToolService`, `RunConfig`, `run` |
| `benchmark` | Explicit project setup and one-time reference processing | `process_benchmark` |
| `evidence` | Atomic artifacts, stable hashes and saved-evidence audits | `write_json`, `fingerprint`, `audit` |
| `interfaces` | Thin CLI and localhost HTTP evaluation interfaces | `proof-eval` |

`harness/search.py` owns one theorem's model request and final cleanup.
`harness/runner.py` owns concurrency and the complete declared cohort.
`harness/agent.py` supplies prompt policy and the tool service to the general
native agent executor. Provider code does not import the harness or decide which proof
wins. The host-owned `ProofSession` makes that decision from evaluator results.
`providers/execution.py` owns durable execution; the three provider adapters own
command construction, authentication and event decoding. Codex and Lemex share
the Responses command builder. A custom agent implementation can be passed as
`run_cell(..., generator=...)`. The former direct RCP chat client is removed.

## Verification and training rewards

```python
from proof_eval import Evaluator

evaluator = Evaluator(
    dataset_path="data/benchmark_data_warmup.jsonl",
    environments_path="environments.local.json",
    cache_dir=".proof-eval",
)
result = evaluator.evaluate("putnam_1964_a4", candidate_code, versions="all")
print(result["scores"], result["per_version"])
reward = evaluator.reward("putnam_1964_a4", candidate_code)
rewards = evaluator.reward_batch(names, declarations)
```

The default input is a full declaration. `input_kind="body"` attaches the exact
dataset statement. Original tokens stay fixed; reference heartbeats come from
the local cache. Invalid primary proofs score zero. Missing infrastructure or
references stay incomplete and raise `EvaluationNotReady` for rewards. Negative
reductions are preserved. Combined rewards require all listed versions.

Reference preparation is explicit: `prepare_reference()` or `proof-benchmark`.
It must not be called from the search/reward path. The measurement backend moved
byte-for-byte to `verification/backend.py`, retaining the source hash used by all
36 warm-up reference fingerprints. Black excludes only this frozen source;
Ruff correctness checks and backend integration tests still cover it.

## Harness API and tools

```python
from pathlib import Path
from proof_eval.harness.config import RunConfig
from proof_eval.harness.runner import run

report = run(RunConfig(
    output=Path("results/harness/my_sol_run"),
    conditions=(("gpt-6.1-sol", "max"),),
    workers=10,
    pilot=True,
))
```

`RunConfig` also accepts explicit dataset, environment, cache, reference-export
and prepared-input paths, plus `names` for a pilot/subset. A subset retains the
full declared denominator and has no full-cohort mean. A prepared-input directory
contains `config.json` with the complete `names`, dataset/environment hashes,
per-name context identities and source pins, plus `inputs/*.json`. Each input pack
contains `name`, its unchanged dataset `row`, the validated deterministic `proof`
and `incumbent` evaluation including references, and `source_context`. The default
uses the already frozen warm-up packs. Pass another directory with `base=...` or
`--base` for another prepared batch; references are still required in the cache.

Set `provider="lemex"` or `provider="claude"` to select a native CLI. Omitted
conditions default to DeepSeek V4.1 Flash/high or Opus 5.5/max respectively;
Codex defaults remain Sol 6.1/max and Astra/max. Only the active `score_edges`
policy can be launched. Historical modes remain readable by the evidence auditor.
The canonical prompt and bank retain the revised V2 bytes. Provider wrapper
instructions may describe a different command working directory; they do not
change the mathematical task, context, score or proof-selection policy.

`ProofSession(folder, pack, evaluator, "score_edges", seed=..., cleanup=...)` is
the tool API used by the host. `dispatch()` accepts these exact JSON operations:

| Operation | Fields | Response |
| --- | --- | --- |
| `check` | `code` | Score tuple, total, correctness, pass rate, best proof |
| `status` | none | Current best proof and measured scores |
| `goals` | `code` | Lean goal observations without performance measurements |
| `search` | `query`, optional `version`, `limit` | Literal search in pinned Lean sources |
| `read` | `path`, optional `version`, `start`, `end` | Bounded source excerpt |
| `outline` | `path`, optional `version` | Declaration locations |
| `finish` | `reason` | Durable stopping decision and current best proof |

Every request includes `op`. Check feedback returns
`score_tuple = [length_reduction_pct, heartbeat_reduction_pct, compatibility_pct]`
and `total_score`; `passing_rate_pct` separately reports actual passing checks.
Only a proof passing every version and improving the combined score by more than
0.05 percentage points replaces the best proof. Invalid, regressive and duplicate
attempts preserve the ledger. The original seed is reconstructed from cached
reference evidence, without compiling it again.

`ProofToolService` exposes the session over a Unix socket. A standalone
`harness/client.py` is copied to the model workspace as `tools.py`. Landlock limits
model-process writes to its workspace/runtime; the host writes measurement
evidence and temporarily compiles inside the pinned projects. The model gets
source and goal tools and ordinary shell tools. Deterministic cleanup is a host
operation at the end, not an agent tool. The initial seed is the better validated
original or saved deterministic proof.

## Providers and costs

Native transports accept exact `model`, `effort`, prompt messages, tool
instructions, a session, a tool-service factory, and pinned CLI identity.
`harness.agent.generate` supplies that wiring for search. Requests, started
markers, CLI events and terminal responses are durable. An interrupted started
request is recorded as indeterminate and is never silently sampled again.
Codex's CLI does not provide this experiment with a hard output-token cap or
temperature control. The active configurations are Sol 6.1/max and Astra/max.

```python
from proof_eval.providers.costs import CostConfig, estimate_token_cost

cost = estimate_token_cost(CostConfig("gpt-6.1-sol", "max"), saved_token_usage)
# The same API accepts claude-opus-5-5/max.
```

`estimate_configuration()` reprices complete saved traces as a scenario;
`proof-harness estimate --provider claude` works before model or Lean calls.
`generations_cost()` includes every attempt. Missing usage remains unknown.
Codex prices remain the pinned 2026-10-04 list-price assumptions. Opus 5.5 rates
verified on 2026-10-05 are $4 input / $20 output per million, $0.20 cache reads,
$5 five-minute writes and $8 one-hour writes, from
[Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing).
Claude terminal records preserve `modelUsage` and `total_cost_usd`; the reported
all-model CLI estimate is used for observed totals, with independent aggregate
repricing shown separately. This is not a subscription invoice. The exact
DeepSeek gateway price is unverified and remains unknown rather than borrowing
another model's rate. The $3 limit applies to each problem; these comparisons
report it without a stopping budget.

Claude usage schema 2 preserves reported one-hour cache writes and the
`modelUsage` thinking-token subset when it covers all output. One-hour writes
are priced at $8/M and remaining writes at $5/M; reasoning stays included in
output and is charged once. Missing duration metadata leaves the independent
five-minute pricing scenario explicitly assumed. Failed or limited native
sessions retain any complete reported usage and cost, while their task outcome
remains incomplete. The auditor uses each record's normalization version;
historical generation and result bytes stay unchanged.

Lemex uses its installed model catalog, pinned by hash, and an explicit Responses
endpoint. Set `LEMEX_API_KEY`/`LEMEX_BASE_URL`, or reuse literal gateway credentials
from the existing `.env`; credentials go only into the child environment. The
host takes a shared filesystem admission slot for each native Lemex session,
conservatively limiting all concurrent batches on this machine to five sessions.
Admission files live under `~/.proof-arena/lemex-slots`, outside model-writable
runtime/cache directories. The child holds the slot descriptor until it exits,
even if its host process ends first.
Other machines or clients using the same key must respect the same shared limit.
No sampling temperature is sent: there is no old 0.3 setting or 32K output cap.
The gateway's effective default temperature is not independently verified.

Claude launches from the repository, with its normal settings/login discovery,
using the exact `claude-opus-5-5` model and `max` effort. It receives an isolated
writable workspace and explicit tool-client paths. Built-in file tools and
approved proof-client/read-only shell commands are available. `dontAsk` plus
`--permission-prompts none` prevents unattended permission waits. There is no
permission bypass, bare mode, fallback model, turn limit or dollar stopping limit.
Unrelated MCP servers are excluded for this matched benchmark. Linux Landlock
protects source projects and the host evidence regardless of CLI permissions.
Terminal `is_error`, subtype, actual model, permission denials, session ID, usage
and cost are preserved and checked. A successful native result may include
recovered tool denials; those remain in its evidence. Errors, limits, missing or
inconsistent session IDs and model mismatches leave an incomplete outcome.
See [headless Claude Code](https://code.claude.com/docs/en/headless).

## Artifacts and resuming

A run freezes code, prompts, dataset, environment map, inputs, controls, CLI
identity and cost assumptions. Each cell saves input, model events, a host proof
ledger, selected evaluation and usage. Deterministic jobs are proof/provenance
keyed and share completed results across cells. Final cleanup cannot replace a
better raw proposal. Output locks and atomic JSON writes prevent overlapping
writers and torn checkpoints.

Repeat the same command to reuse completed cells. Changes to frozen inputs or
implementation require a new output directory. Started requests without terminal
evidence need investigation; resuming does not authorize resampling.
`proof-harness audit` recomputes saved score arithmetic and selection, checks
source/proof identities, version evidence, cleanup stages, controls and usage.
It makes no compiler/model calls. Historical source pins resolve to verified,
content-addressed snapshots rather than importing or executing old drivers.

When every cell in a condition completes, reporting exports
`conditions/MODEL__EFFORT/selected_candidates.jsonl` in organizer submission format:
one `{"name": ..., "proof": "complete declaration"}` object per line.

## Command migration and quality

| Previous entry point | Maintained command |
| --- | --- |
| `src/process_benchmark.py` | `proof-benchmark` |
| `src/setup_benchmark.py` | `proof-setup` |
| `src/run_deterministic_batch.py` | `proof-deterministic` |
| `src/run_experiments.py` | `proof-transform` |
| `src/audit_experiments.py` | `proof-audit` |
| `src/report_experiments.py` | `proof-report` |
| `src/run_agent_harness.py` | `proof-harness run/prepare/estimate/report` |
| `src/audit_agent_harness.py` | `proof-harness audit` |
| `src/continue_agent_harness.py` | `proof-harness run --pilot` |
| `src/rcp.py` | retired; native Lemex via `proof-harness --provider lemex` |

Other one-shot, repair, per-model and analysis drivers are retired. Their saved
results remain readable; recover their code from `bfb2ade6` when historical
reproduction is specifically needed. There is no live legacy scripts directory.

`make format`, `make check`, and `make test` use pinned Black/Ruff and the offline
pytest suite. GitHub Actions runs the same checks. Lean/Codex local integration
tests skip explicitly when dependencies are absent; tests using the installed
Codex route requests to a localhost fake server. Remote paid tests are marked
`live` and excluded by default. Run them only explicitly with `pytest -m live`.
