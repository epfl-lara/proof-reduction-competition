# Runtime architecture

Saved host evidence can also be analyzed with `proof-harness replay --run RUN
--protocol PROTOCOL --output NEW_DIRECTORY`. The immutable chain loader,
prefix-only stopping policies, and reporting live in `harness/discovery_tree.py`,
`harness/replay.py`, and `harness/replay_reporting.py`. Replay dispatches no model
or Lean calls, verifies raw identity before policy comparisons, and fingerprints
its read-only inputs. A cut that removes an accepted improvement cannot reveal
later restarts; matching parent proof hashes permit only recorded continuations.
Splicing assumes unchanged behavior under shifted remaining-time prompts.
Reinvestment and interpolated cost are separately labelled model estimates.
`proof-harness audit --output REPLAY_DIRECTORY` checks saved replay fingerprints
and report arithmetic. See stage 14's pre-registered protocol and outputs.

The maintained runtime is one installable package. CLI commands call library
APIs; no library imports an experiment driver. Historical studies stay in
`results/`; their retired source can be recovered from checkpoint `bfb2ade6`.

| Package | Responsibility | Main API |
| --- | --- | --- |
| `verification` | Pinned Lean compilation, token counts, cached references, goal observations, heartbeat diagnostics | `Evaluator`, `check_references`, `profile` |
| `optimization` | Parsed proof edits, tactic discovery, minimization, bounded cleanup, generic deterministic batches | `Budget`, `optimize`, `cleanup_proof`, `BatchConfig`, `run_batch` |
| `providers` | Native agent CLIs, durable execution/isolation, terminal usage, price estimates | `codex.generate`, `lemex.generate`, `claude.generate`, `agy.generate`, `CostConfig` |
| `harness` | Prompt/context policy, tool sessions, one-theorem search, batch coordination and reports | `ProofSession`, `ProofToolService`, `RunConfig`, `run` |
| `benchmark` | Explicit project setup and one-time reference processing | `process_benchmark` |
| `evidence` | Atomic artifacts, stable hashes and saved-evidence audits | `write_json`, `fingerprint`, `audit` |
| `interfaces` | Thin CLI and localhost HTTP evaluation interfaces | `proof-eval` |

`harness/budget.py` supervises one isolated theorem worker under a durable wall
deadline. `harness/search.py` owns its model request and final cleanup;
`harness/outcomes.py` selects the result from verified evidence.
`harness/runner.py` owns concurrency and the complete declared cohort.
`harness/agent.py` supplies prompt policy and the tool service to the general
native agent executor. Provider code does not import the harness or decide which proof
wins. The host-owned `ProofSession` makes that decision from evaluator results.
`providers/execution.py` owns durable execution; the four provider adapters own
command construction, authentication and event decoding. Codex and Lemex share
the Responses command builder. A custom agent implementation can be passed as
`run_cell(..., generator=...)`. The former direct RCP chat client is removed.
Prepared calls through this API use the same deadline supervisor as batch runs.
A supplied Python generator runs in an isolated Linux fork worker so its host
tools and cleanup can also be stopped; return results and durable artifacts
rather than relying on mutations of objects in the caller's process.

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

Set `provider="lemex"`, `provider="claude"` or `provider="agy"` to select a
native CLI. Omitted conditions default to DeepSeek V4.1 Flash/high, Opus
5.5/max or Gemini 3.8 Flash/high respectively; Codex defaults remain Sol
6.1/max and Astra/max. Only the active `score_edges`
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
| `profile` | `code`, optional `version`, `threshold_raw`, `limit` | Bounded inclusive tactic/phase heartbeat diagnostics; no score or selection changes |
| `search` | `query`, optional `version`, `limit` | Literal search in pinned Lean sources |
| `semantic_search` | `query`, optional `version`, `limit`, `packages` | Optional local declaration discovery; index headers and docstrings with snapshot provenance |
| `web_search` | `query`, optional `limit`, `domains` | Optional public web discovery with URLs, snippets and saved retrieval provenance |
| `web_open` | `url`, optional `start`, `end` | Optional bounded public HTTPS page excerpt with saved source bytes |
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

`harness/semantic.py` owns LeanExplore discovery, enabled by default. Set
`RunConfig.semantic_search=SemanticSearchConfig(index_directory, embedding_directory)`
or use the default `semantic_search=True` to discover already cached assets during
explicit preparation. `False` or `None`, and CLI `--no-semantic-search`, disable it.
Constructing a configuration does not read assets. Preparation freezes
the corpus, BM25/FAISS files, embedding snapshot and dependency versions; runtime
guards reject changes. Initialization uses CPU and local model files only, and
queries skip reranking. No ML package is imported by a normal library import.
Package scope follows module roots in the selected pinned project and its actual
Lake dependencies. Invalid package restrictions are rejected. Results identify
their separate index snapshot and omit indexed proof bodies; final verification
continues to use the unchanged pinned Lean evaluator. Host-owned
`evidence/semantic_searches.jsonl` retains requests and returned discovery hints.

`RunConfig.web_search=True` is the default and enables the host tools in
`harness/web.py`. Preparation freezes the DuckDuckGo Lite endpoint, time/size
bounds and public HTTPS scope. The canonical task prompt is unchanged; the
web condition appends an explicit read-scope permission and tool instructions.
Native Responses hosted search stays disabled because the gateway probe exposed
no working native search tool. All providers can use the same host socket tools.
The host saves start/completion records in `evidence/web_requests.jsonl` and
exact retrieved bytes in `evidence/web_responses/`. Errors remain recorded;
deadline interruptions retain started records. `harness/web_audit.py` checks
settings, body hashes and response bounds offline. Web lookups share the same
whole-problem deadline and cannot replace the selected proof or measurements.
Use `web_search=False` or `--no-web-search` to disable them. Both positive CLI
flags remain accepted. Saved configurations and historical tool availability
stay unchanged; changed settings require a new output directory.

`RunConfig.problem_timeout_seconds` defaults to 3420 (57 minutes) for every
provider. The budget starts when a worker receives a problem; batch queue time
and batch reference preflight are separate. Admission, model reasoning, all
host tools and final cleanup share that one deadline. Status feedback includes
the remaining seconds. At expiry the supervisor stops only that worker and its
descendants, including detached agent/Lean processes, then reconstructs the
best fully checked proof from atomic ledger records. Recovery performs no model
or Lean calls. Final cleanup may be skipped or interrupted; this is explicit in
the result and audited. Deadline stops are complete bounded search outcomes,
with `generation_status="budget_exhausted"` if no native final arrived; transport
failures and unknown interruptions remain incomplete. Missing usage stays
unknown. A pilot with no host checks cannot unlock the full cohort.

The 57-minute allocation is our chosen conservative budget derived from the
saved open-track 48-hour/50-problem total, not an organizer per-problem rule.

`RunConfig.budget_tracking` defaults to `None`: voluntary agent completion ends
the single native session. Select `"cost"` or `"time"` with `--budget-tracking`,
`--track-cost` or `--track-time` to admit fresh attempts after successful native
completion. Indeterminate requests, permanent failures and unavailable host
checks stop admission. Terminal transient transport failures have the separate
bounded recovery policy below. Cost tracking also stops on missing cost counters. The fresh prompt has exactly one
system message and one user message; its incumbent declaration/scores and
`candidate.lean` come from the best proof in the shared verified ledger.
`reset_for_attempt()` clears both the finish marker and saved session state.
No conversation history or previous workspace is passed to the new session.

`budget_usd_per_problem` / `--budget-usd` defaults to $3.00. Cumulative estimates
include every attempt. Each native Codex session receives the remaining dollars
converted to weighted input/output tokens, conservatively using cache-write and
long-context rates. Claude receives `--max-budget-usd` for the remaining dollars.
These native guards check between upstream responses; an in-flight response can
overshoot. Native guard exhaustion is a controlled `cost_limit` outcome and is
never resampled. Missing native terminal usage remains unknown, including on
controlled stops. `budget_enforced` is true only for time tracking; cost results
record `hard_cost_cap=false` and `cost_enforcement="native_response_boundaries"`.
The policy does not claim a strict invoice cap or override sampling defaults.

`RunConfig.max_transport_restarts` defaults to two. `providers/retries.py`
classifies observed terminal transient failures; incomplete request markers,
authentication/model failures and malformed finals are excluded. Native Lemex
uses four HTTP retries and five stream retries. A successful final following a
native reconnect remains successful, with the reconnect events preserved and
`usage_complete=false` because interrupted upstream usage may be unreported.
Host recovery after native exhaustion starts a fresh session from the shared
best-proof ledger with bounded backoff, never a replenished deadline. The attempt
auditor checks each admission, predecessor failure, incumbent and time budget.
Cost tracking admits no recovery when cumulative spending is unknown.

`RunConfig.incumbents_from` / `--incumbents-from` supports an explicitly launched
new output using a previous run's best proofs. `harness/incumbents.py` pins the
source result/configuration bytes, requires the same provider/model/effort,
theorem preparation and cached reference identities, and rejects proofs missing
any required version. Runtime guards and the auditor verify those pins. This
allocates a new problem budget only in the new output; historical evidence and
budgets remain unchanged. A better original/deterministic seed is still retained.

`RunConfig.carry_budgets_from` / `--carry-budgets-from` instead continues a
stopped cost-tracked run under a new runtime and output without resetting its
allocation. `harness/carryover.py` audits the source run and pins its result,
configuration and deadline bytes. Cumulative pricing includes all prior
generations, including failed calls; the original problem deadline is restored.
The same-condition best verified proof supplies the incumbent. Changed fixed
inputs, unknown cumulative usage, active batches and started cells without a
terminal result block continuation. Audit checks both the carried spending and
the unchanged deadline.

Time tracking uses the single persisted whole-problem deadline. If none exists,
the supervisor creates it before dispatch; resume always reuses it. Both modes
decline another attempt once at most 30 seconds remain for final cleanup and stop after at most
`max_budget_restarts + 1` attempts (default 21). Exhausted cumulative cost,
insufficient money for one conservatively priced output token, cleanup reserve,
unknown usage and the restart safety limit have separate host stopping reasons.
Final deterministic cleanup receives the best proof found across all attempts.

`ProofToolService` exposes the session over a Unix socket. A standalone
`harness/client.py` is copied to the model workspace as `tools.py`. Landlock limits
model-process writes to its workspace/runtime; the host writes measurement
evidence and temporarily compiles inside the pinned projects. The model gets
source and goal tools and ordinary shell tools. Deterministic cleanup is a host
operation at the end, not an agent tool. The initial seed is the better validated
original or saved deterministic proof.

`verification/profiling.py` runs explicit diagnostic compilations using native
heartbeat traces and optional `profile_tactic "label" in tac` annotations.
`verification/profile_trace.py` builds bounded rankings from structured trace
trees. The separate profile cache and host-owned `profiles/` evidence retain
proof/environment/configuration identities. This operation neither reads nor
writes reference measurements, and correctness-only sessions reject it. Costs
include diagnostic overhead and nested work; candidate scores still come only
from `check`. See [PROFILING.md](PROFILING.md) for units, examples and limitations.

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
DeepSeek and Qwen gateway prices are unverified and remain unknown rather than
borrowing another model's rate. The $3 limit applies to each problem. Default
comparison runs report estimated cost; only opt-in cost tracking admits new
attempts according to the remaining dollars and enables native spending guards.

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

Antigravity launches the installed `agy` CLI in print mode with stream-json
output, the exact `gemini-3.8-flash-high` model slug and `code` agent. Its print
mode has no system-prompt channel, so the harness system policy, tool
instructions and user message are merged into one inline `-p` argument and
reach the model as user-level instructions; `-p=@file` is a file reference and
is not used. Each request records the `init.model` selection evidence, which
proves the requested selection propagated but not the backend identity. Usage
is normalized by adding reported cache reads back into input (cache writes are
unreported); complete usage from failed calls is retained. Terminal status,
conversation identity, final content, denials and supervised deadlines are
audited, and the exact Antigravity billed price stays unknown. Opt-in cost
tracking uses the frozen standard Gemini API rates ($0.75/M input, $0.075/M
cached reads, $3.75/M output including thinking; effective through 2026-12-31)
as an explicit API-equivalent proxy. The host supervisor tails `events.jsonl`,
replaces repeated per-step usage snapshots, and stops the native child when
observed spending reaches the remaining per-problem cap. Terminal cumulative
usage replaces rather than adds to the step subtotal. `cost_progress.json`
records the observed lower bound; `cost_stop.json` pins the event prefix,
remaining guard, usage and estimate behind a controlled stop. Offline audit
reconstructs that stop without calling a model or Lean. Unreported in-flight
usage and cache storage remain unknown, so this is not a hard invoice ceiling.

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

New schema-4 runs also save one host-owned `attempt.json` per admitted attempt,
covering prompt identity, incumbent certificate, cleared finish state, check
boundaries, time allocation, native cost guard and cumulative cost before/after.
`result.json` embeds these records and the durable `search_stop.json` decision.
The auditor checks restart admission and fresh context in addition to all
existing measurement invariants. Deadline recovery can record a stopped
admission with `dispatch_status="not_dispatched"` if request setup never finished;
it does not invent a native request or resample it. Historical schemas and
artifact bytes remain unchanged.

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
