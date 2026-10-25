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

The explicit local open-weight route is `lemex-local`. Its
[`proof-local-vllm` interface](LOCAL_MODELS.md) freezes a native profile and owns
the vLLM server and attributed raw HTTP capture proxy around the ordinary model
workflow. Gateway admission and existing provider defaults stay separate.

| Package | Responsibility | Main API |
| --- | --- | --- |
| `verification` | Pinned Lean compilation, token counts, cached references, goal observations, heartbeat diagnostics | `Evaluator`, `check_references`, `profile` |
| `optimization` | Parsed proof edits, tactic discovery, verified search and cohort cleanup | `Budget`, `optimize`, `explore`, `run_cleanup` |
| `providers` | Native agent CLIs, durable execution/isolation, terminal usage, price estimates | `codex.generate`, `lemex.generate`, `claude.generate`, `agy.generate`, `CostConfig` |
| `harness` | Cohort phase barriers, model batches, per-theorem search and reports | `PipelineConfig`, `run_pipeline`, `RunConfig`, `run`, `ProofSession` |
| `benchmark` | Explicit project setup, source task harvesting, and one-time reference processing | `process_benchmark`, `CorpusConfig`, `build_corpus` |
| `evidence` | Atomic artifacts, stable hashes and saved-evidence audits | `write_json`, `fingerprint`, `audit` |
| `interfaces` | Thin CLI and localhost HTTP evaluation interfaces | `proof-eval` |

`harness/pipeline.py` is the standard workflow: cohort cleanup before, a model-only
batch, then cleanup of each model condition's own selected outputs. Whole-cohort
barriers prevent model requests before initial cleanup completes and prevent
postprocessing before the model batch terminates. `PipelineConfig` defaults both
cleanup phases on with eight workers. Model pools are independent and configurable;
Sol and Qwen default to five. `pipeline_reporting.py` reports phase times, total
wall time, score gains and audited source links. Failed cells do not cancel other
queued cells, but full-cohort means require complete evidence.

`optimization/cohort.py` owns independent cleanup worker processes and private
caches. It invokes the exact `plans()["one_sweep"]`: sixteen methods in gain order,
one traversal, rounds=3/trials=32/sites=6 per method, no overall five-minute cap.
Each phase freshly measures the original and its explicitly chosen proof, checks
all versions and retains only >0.05-point improvements. `state.json` is exported
only for a complete audited cohort. Durable starts without terminal evidence are
never automatically replayed. `proof-deterministic` calls this cohort interface.
`optimization/supervision.py` gives each cleanup worker a separate subreaper and
coordinator-liveness pipe. It records process identities, retains the cohort lock
until its owned descendants are drained, and handles ordinary cancellation or
coordinator death without targeting other jobs. Interrupted batches cancel queued
admission and remain incomplete. Saved audits verify runtime bytes against the
current source or an exact preserved snapshot without executing snapshot code.
The old `optimization.batch` implementation remains a historical library API,
not the default CLI schedule.

`evidence/proof_states.py` freezes original proofs, a portable manifest, or explicit
name/proof JSONL. It pins exact cohort, row/proof identities, denominators and
source bytes. Model/effort lineage survives subsequent cleanup; importing another
condition's labelled model solutions is rejected. Raw JSONL is explicitly external
provenance and never treated as an audited deterministic source. `--starting-proofs`
does not implicitly skip another initial sweep; choose `--no-cleanup-before`.

`harness/runner.py` is the lower-level model-only batch. `RunConfig` defaults
`deterministic=False` and `restart_history=False`; in-cell transforms are rejected
for new configurations. `harness/budget.py` supervises each isolated theorem worker.
`harness/initial.py` freshly measures the original inside the model-phase timer;
`harness/starting.py` then freshly verifies an explicit starting state, preserving
the better original when the imported proof does not improve it. Candidate and
analysis caches are private. Canonical denominators are unchanged. The source
state, model starting score and subsequent gains are separate report fields.

New configurations permit one original-measurement retry only after a terminal
wall timeout with every other required version passing. Both attempts are saved,
use fresh private caches, and share the original model-phase clock. An interrupted
measurement or semantic failure is never replayed automatically.

Historical initial-only capped runs retain `optimization/bounded.py` and
`harness/initial_audit.py` semantics. Their 300-second cap, original/D0 edge cleanup,
checkpoint schemas and archived request/config bytes are unchanged. New phase
workflows carry `cohort_pipeline_version=1`; model-only cells carry
`model_phase_version=1` and `budget_scope="model_phase"`.

Extended deterministic research remains separate from the default one-sweep.
`optimization/search_graph.py` defines fixed ordered/repeated and beam schedules;
`optimization/exploration.py` executes them with durable per-expansion evidence,
all-version certificates, a monotone best-proof trace and no overall wall limit.
Beam layers finish all methods before deterministic score/hash selection. Lower
scoring branches may survive, but every edge must improve its own parent by more
than 0.05 points. This searches improving paths only; it does not cross score
valleys or prove optimality. Repeated sweeps stop after a no-change sweep or eight
sweeps; their operators still have explicit trial/round/site bounds.
`optimization/exploration_study.py` queues full original-start cohorts in fresh
worker processes with private caches. `exploration_reporting.py` audits branch
lineage, canonical arithmetic, watchdog evidence and manifests before admitting
a full-cohort mean. Completed expansions can be reused within one condition;
indeterminate expansions are never automatically replayed. Active studies use
isolated runtime copies. No model request is dispatched by this interface.
Explicit `--reuse-completed-from SOURCE` recovery audits and pins complete
source cells without copying their caches or modifying their evidence. Failed
or missing cells start afresh from original proofs in the new study directory.
Recovery reports identify reused cells and combine source/recovery timings;
the frozen source configuration records the original implementation separately.

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

`providers/isolation.py` requires bubblewrap user/PID/mount namespaces and a
private `/proc`, then installs the existing Landlock write rules. Native tools
retain host tool sockets and networking; signals cannot target ancestor or
sibling PID namespaces. The admission lock is retained by bubblewrap's
supervisor with `--sync-fd`. Host supervisors remain outside the namespace and
own deadline cleanup. Isolation preflight has no unrestricted fallback.
`providers/termination.py` commits exit evidence before native event parsing or
host-tool draining. Negative return codes prove signal termination; 128+signal
codes are labelled as an exit convention only. `evidence/watch.py` independently
scans selected result roots and user services, emits durable deduplicated local
alerts, correlates exits within five seconds, and excludes controlled budget
stops. It does not modify watched evidence or resample interrupted requests.

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
General search/reward scoring must not replace these denominators. The new
harness separately calls candidate evaluation on the original as an explicit
measured preparation phase inside its clock. The measurement backend moved
byte-for-byte to `verification/backend.py`, retaining the source hash used by all
36 warm-up reference fingerprints. Black excludes only this frozen source;
Ruff correctness checks and backend integration tests still cover it.

`proof-corpus` extracts Arena-style RSI/RL tasks from explicitly pinned source
snapshots. `benchmark/harvest_commands.lean` supplies Lean parser byte ranges;
`benchmark/harvest.py` preserves source text, counts proof tokens, assigns grouped
splits, and selects diverse tasks. `benchmark/corpus.py` owns bounded extraction
and its durable inventory. Standalone proof exports retain the complete preceding
source context and record the publisher pin separately from the Mathlib compiler
pin; related Putnam proofs and supporting lemmas share a problem split group.
`benchmark/quality.py` checks original proof denominators and obvious tautologies,
and matches broad proof-length bands to the benchmark with file/project diversity
caps. A scarce long-proof band fails explicitly. This measures proof size rather
than establishing equal mathematical difficulty. Extraction makes no model calls and prepares no
reference measurements. Compiler validation and one-time reference preparation
remain separate steps. The single [training corpus](../data/training/arena_rsi/README.md)
contains train and validation splits; Arena is the test set. Local source audits,
checked pilots, and preparation instructions are retained separately under
`.proof-eval/training/arena_rsi/artifacts/`.

## Harness API and tools

```python
from pathlib import Path
from proof_eval.harness.config import RunConfig
from proof_eval.harness.runner import run

# Lower-level MODEL-ONLY API. Standard before/model/after workflow:
from proof_eval.harness.pipeline import PipelineConfig, run_pipeline

report = run_pipeline(PipelineConfig(model=RunConfig(
    output=Path("results/my_sol_run"),
    conditions=(("gpt-6.1-sol", "max"),),
), cleanup_workers=8))
```

`RunConfig` also accepts explicit dataset, environment, cache, reference-export
and prepared-input paths, plus `names` for an explicit subset. A subset retains the
full declared denominator and has no full-cohort mean. A prepared-input directory
contains `config.json` with the complete `names`, dataset/environment hashes,
per-name context identities and source pins, plus `inputs/*.json`. Each input pack
contains `name`, its unchanged dataset `row`, the validated deterministic `proof`
and `incumbent` evaluation including references, and `source_context`. The default
uses the already frozen warm-up packs. Pass another directory with `base=...` or
`--base` for another prepared batch; references are still required in the cache.

Model batches queue the full cohort after cached-reference/runtime preflight.
Provider defaults are five workers for closed models, five for Qwen and three
for DeepSeek. Positive explicit worker overrides are accepted; Lemex's shared
five-session admission limit still applies independently. Model-only queue time
precedes a cell's model timer, while the pipeline records whole-workflow time.
Individual incomplete outcomes do not cancel other queued cells.

Set `provider="lemex"`, `provider="claude"` or `provider="agy"` to select a
native CLI. Omitted conditions default to DeepSeek V4.1 Flash/high, Opus
5.5/max or Gemini 3.8 Flash/high respectively; Codex defaults remain Sol
6.1/max and Astra/max. Only the active `score_edges`
policy can be launched. Historical modes remain readable by the evidence auditor.
The canonical prompt and five-card bank contain the experimental priority and
strategy revision; historical V2 runs retain their frozen bytes. Provider wrapper
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
| `remember` | `kind`, `text` | When restart history is explicitly enabled: an unverified discovery/rejection/next-step note, at most 600 characters |

Every request includes `op`. Check feedback returns
`score_tuple = [length_reduction_pct, heartbeat_reduction_pct, compatibility_pct]`
and `total_score`; `passing_rate_pct` separately reports actual passing checks.
Only a proof passing every version and improving the combined score by more than
0.05 percentage points replaces the best proof. Invalid, regressive and duplicate
attempts preserve the ledger. New harness runs use their freshly measured original seed. Historical runs
reconstructed the original from cached reference evidence.

`harness/score_feedback.py` explains saved measurements without changing scoring
or selection. `component_delta_from_previous_best_pp` reports the length,
heartbeat and compatibility contributions to a candidate's combined-score
change, each divided by three. It is null unless both declarations pass every
required version and have finite component scores. Check and status return
`best_remaining_score_loss_pp`, the incumbent's length and heartbeat losses
relative to an ideal zero-token, zero-heartbeat proof. These are upper bounds,
not forecasts of achievable gains; negative reductions remain unclipped. The
host computes deltas before replacing the incumbent and headroom after selection.
This feedback adds no Lean calls and exposes no scores in correctness-only mode.

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

`RunConfig.budget_tracking="auto"` selects `"time"` for the explicitly listed
open models (Qwen and DeepSeek) and `"cost"` for closed models. Resolved
`RunConfig.problem_timeout_seconds` defaults to 14400 (four hours) for Qwen,
3420 (57 minutes) for other open models, and `None` for cost tracking. A numeric timeout explicitly adds a watchdog to cost
tracking; there is no implicit provider or whole-problem timeout in cost-only
search. Open-model runs receive no spending guard. New configurations use schema 8;
historical configuration and result bytes retain their original budgets.

New runs pin `native_cost_guard_version=2`. A one-token Codex remainder has no
budget reminder: the native CLI requires every reminder to be strictly between
zero and the token limit. The spending guard remains enabled, so exhaustion is a
controlled stop that retains the verified incumbent. Historical configurations
without the version field retain their original guard reconstruction for audits.

The declarative `MODEL_TRACKS` table in `providers/registry.py` is independent
of provider routing and pinned with the runtime source. Automatic budgets reject
unclassified models rather than inferring a track from routing or pricing.
Matched experiments freeze this classification along with their other settings.

Closed-track runs should default to an isolated current runtime copy: without
a wall deadline, the cohort's pinned files can remain frozen for hours or days.
RCP's shared limit of five concurrent requests constrains its throughput across
batches and clients even when wall time does not bound a run.

The time budget starts when a worker receives a problem; batch queue time
and batch reference preflight are separate. Admission, model reasoning, all
original/selected-proof measurement and all host tools share that model-phase deadline. Cohort cleanup has separate timers. Status feedback includes
the remaining seconds. At expiry the supervisor stops only that worker and its
descendants, including detached agent/Lean processes, then reconstructs the
best fully checked proof from atomic ledger records. Recovery performs no model
or Lean calls. The before/after cleanup phases do not consume this model budget. A deadline
during original measurement is an incomplete measurement outcome. Deadline stops are complete bounded search outcomes,
with `generation_status="budget_exhausted"` if no native final arrived; transport
failures and unknown interruptions remain incomplete. Missing usage stays
unknown. Those stopping conditions apply to the affected theorem; other queued
theorems continue independently.

Qwen's four-hour/five-worker policy is the user's new allocation; the prior
57-minute total-problem runs retain their historical meaning. The user-reported
48-hour resource allowance is for one 64-core node with four A100 80GB GPUs.
Pipeline reports include all phases, but there is no automatic 48-hour workflow
watchdog. Confirm the overall resource plan before starting an experiment.

Each condition keeps one model and effort throughout its search. There is no
first-attempt model override. Retired mixed-model runs remain read-only:
`harness/archived_schedules.py` preserves their model identities and cost schemas
for saved-evidence audits, and reporting returns their existing archived report.
New search, resume and incumbent/budget imports cannot activate that schedule.

Automatic tracking admits fresh attempts after successful native completion.
Select `"cost"` or `"time"` with `--budget-tracking`, `--track-cost` or
`--track-time` to override the track. Python callers can explicitly select `None`
to end at voluntary completion under a time limit. Indeterminate requests, permanent failures and unavailable host
checks stop admission. Terminal transient transport failures have the separate
bounded recovery policy below. Strict cost tracking also stops on missing cost
counters. The fresh prompt has exactly one
system message and one user message; its incumbent declaration/scores and
`candidate.lean` come from the best proof in the shared verified ledger.
`reset_for_attempt()` clears both the finish marker and saved session state.
No full conversation history or previous workspace is passed to the new session.
An explicitly enabled restart-history condition receives the bounded evidence summary.

`budget_usd_per_problem` / `--budget-usd` defaults to $3.00. Cumulative estimates
include every attempt. Each native Codex session receives the remaining dollars
converted to weighted input/output tokens, conservatively using cache-write and
long-context rates. Claude receives `--max-budget-usd` for the remaining dollars.
These native guards check between upstream responses; an in-flight response can
overshoot. Native guard exhaustion is a controlled `cost_limit` boundary. Strict
tracking stops there; best-effort Codex tracking can admit a fresh session from
the verified incumbent while its cumulative estimate remains below the dollar
target, using the existing optimization restart limit and remaining dollars.
Missing native terminal usage remains explicitly unreported,
including on controlled stops; best-effort accounting may retain a numeric
estimate. `budget_enforced` is true only for time tracking; cost results
record `hard_cost_cap=false` and `cost_enforcement="native_response_boundaries"`.
The policy does not claim a strict invoice cap or override sampling defaults.

`RunConfig.max_transport_restarts` defaults to two. `providers/retries.py`
classifies observed terminal transient failures; incomplete request markers,
authentication/model failures and malformed finals are excluded. Native Lemex
uses four HTTP retries and five stream retries. A successful final following a
native reconnect remains successful, with the reconnect events preserved.
Historical exec-only accounting marks any reconnect's usage incomplete. New
Codex 0.162+ identities pin response-usage schema 2 and enable native local
request tracing in the isolated workspace. `providers/response_usage.py`
reconciles completed-response counters, explicit capacity/rate-limit refusals
without partial output, and the native final; it writes the host-owned
`response_usage.json`. Hidden first retries are included in this trace. Every
complete inference counter is retained across compaction, failed turns and
native budget stops. Compaction and failed requests without counters remain
explicitly unknown rather than erasing the known subtotal. The saved-evidence
auditor rebuilds accounting and verifies trace/payload hashes according to each
record's schema; schema-1 evidence and historical bytes remain unchanged.

Schema-8 configurations pin `RunConfig.usage_policy` / `--usage-policy`.
New Codex cost runs default to `"best_effort"`; `"strict"` preserves the policy
of stopping admission when cumulative reported usage is incomplete. Configurations
without this field retain strict behavior. Best-effort accounting keeps reported
`token_usage` separate from per-request heuristics in `usage_estimates` and the
combined `estimated_token_usage` used for budget pricing. For compaction, estimated
input uses the nearest preceding complete inference input plus output, and
estimated output uses the nearest following complete inference input, a
conservative proxy that includes retained context. The estimation record pins
the source call IDs and counter fields. If a neighbor is absent, that side uses
canonical UTF-8 JSON bytes divided by four, rounded up; partial responses without
counters use the same byte heuristic. Unreported input is assumed uncached.
Failed requests without partial output receive an explicit zero-cost estimate;
explicit capacity/rate-limit refusals remain classified as rejected requests
under the existing refusal policy. These are reproducible
assumptions, not reported counters or guaranteed bounds; encrypted payloads can
distort the byte heuristic. Numeric incomplete costs retain unknown-request
flags and their estimation basis. Missing or inconsistent evidence without a
usable estimate still blocks admission.
Host recovery after native exhaustion starts a fresh session from the shared
best-proof ledger with bounded backoff, never a replenished track budget. The attempt
auditor checks each admission, predecessor failure, incumbent and time budget.
Strict cost tracking admits no recovery when cumulative spending is unknown.
Best-effort tracking may recover an observed terminal transient failure while
its numeric cumulative estimate remains below the original problem budget.
Neither policy permits recovery of an indeterminate or active request.

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
generations, including failed calls; any explicitly configured original problem
deadline is restored. Cost-only carryover pins the prior spending and creates
no deadline marker.
The same-condition best verified proof supplies the incumbent. The source and
destination must use the same usage policy; a historical configuration without
the field requires `--usage-policy strict`. Changed fixed inputs, cumulative
usage that the selected policy cannot price, active batches and started cells
without a terminal result block continuation. Audit checks both the carried
spending and the unchanged deadline.

Time tracking uses the single persisted model-phase deadline. If none exists,
the supervisor creates it before dispatch; resume always reuses it.
New runs use `cleanup_reserve_seconds=0`: deterministic work runs in separate
before/after cohort phases. Historical edge-cleanup runs retain their saved
30-second reserve for auditing. Cleanup makes no model requests or model spend.
Both modes allow at most `max_budget_restarts + max_transport_restarts + 1`
admitted attempts (default 23: 20 optimization restarts, two terminal transport
recoveries and one initial attempt). Native retries remain within their session.
Exhausted cumulative cost, insufficient money for one conservatively priced
output token, cleanup reserve,
usage that the selected policy cannot price, and the restart safety limit have
separate host stopping reasons.
The final output is the best fully verified proof across initial work and model attempts.

`ProofToolService` exposes the session over a Unix socket. A standalone
`harness/client.py` is copied to the model workspace as `tools.py`. Landlock limits
model-process writes to its workspace/runtime; the host writes measurement
evidence and temporarily compiles inside the pinned projects. The tool service
waits for accepted requests to finish before closing an attempt, including when
a native cost stop disconnects the model during a Lean check. This keeps the
attempt's check boundary and the next incumbent consistent with the host ledger.
The process supervisor still enforces any configured whole-problem deadline. The model gets
source and goal tools and ordinary shell tools. Deterministic cleanup is a host
operation before model search, not an agent tool. New runs always begin with
a fresh measurement of the original proof.

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
For CLI 0.162 and later, Codex preparation also checks and fingerprints the
executable `codex-code-mode-host` companion. An incomplete copied CLI bundle
fails before a model request can start.

```python
from proof_eval.providers.costs import CostConfig, estimate_token_cost

cost = estimate_token_cost(CostConfig("gpt-6.1-sol", "max"), saved_token_usage)
# The same API accepts claude-opus-5-5/max.
```

`estimate_configuration()` reprices complete saved traces as a scenario;
`proof-harness estimate --provider claude` works before model or Lean calls.
`generations_cost()` includes every attempt. Missing reported usage remains
unknown. The pinned best-effort Codex policy can price separately recorded
estimates and return an explicitly incomplete numeric total for budget decisions;
strict policy keeps that total unknown. Neither policy certifies an invoice cap.
Codex prices remain the pinned 2026-10-04 list-price assumptions. Opus 5.5 rates
verified on 2026-10-05 are $4 input / $20 output per million, $0.20 cache reads,
$5 five-minute writes and $8 one-hour writes, from
[Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing).
Claude terminal records preserve `modelUsage` and `total_cost_usd`; the reported
all-model CLI estimate is used for observed totals, with independent aggregate
repricing shown separately. This is not a subscription invoice. The exact
DeepSeek and Qwen gateway prices are unverified and remain unknown rather than
borrowing another model's rate. The $3 limit applies to each problem. Closed-model runs
default to cost tracking, admitting new attempts according to
the remaining dollars and enabling native spending guards without a time limit.

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
permission bypass, bare mode, fallback model, turn limit. Cost tracking passes the remaining dollar allowance explicitly.
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
ledger, selected evaluation and usage. New deterministic phases have private per-cell caches and only reuse their own
completed, audited cells on identical resume. Historical shared cleanup jobs remain
auditable. Postprocessing preserves the model-selected incumbent unless a freshly
checked candidate improves it. Output locks and atomic JSON writes prevent overlapping
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

`harness/restart_history.py` implements the opt-in version-1 restart-history
policy (off by default). It saves source-tool observations and model notes in the host-owned
`evidence/restart_events.jsonl`; at most 64 events are admitted per attempt.
Checks remain in the existing validated proof ledger. Each fresh attempt gets
up to two accepted and four rejected nonduplicate trial summaries, three source
observations, and the latest note of each kind, bounded to 12,000 serialized
characters. Notes and retrieved text remain explicitly separate from measured
proof facts. Canonical system-prompt and strategy-card bytes are unchanged.
`restart_history_version` pins this behavior when enabled. Opt in
with `--restart-history` or `restart_history=True`; historical
configurations that omit the field retain their original behavior. Attempt records freeze event
prefix counts and hashes. `restart_history_audit.py` validates scope, attempt
boundaries, event hashes, and exact deterministic reconstruction of each prompt
summary. Future evidence, another condition's notes and arbitrary prompt history
are rejected. Existing isolation, no-resampling, proof selection and budget
contracts apply unchanged; resuming a completed cell makes no new requests.

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
| `src/continue_agent_harness.py` | `proof-harness run` |
| `src/rcp.py` | retired; native Lemex via `proof-harness --provider lemex` |

Other one-shot, repair, per-model and analysis drivers are retired. Their saved
results remain readable; recover their code from `bfb2ade6` when historical
reproduction is specifically needed. There is no live legacy scripts directory.

`make format`, `make check`, and `make test` use pinned Black/Ruff and the offline
pytest suite. GitHub Actions runs the same checks. Lean/Codex local integration
tests skip explicitly when dependencies are absent; tests using the installed
Codex route requests to a localhost fake server. Remote paid tests are marked
`live` and excluded by default. Run them only explicitly with `pytest -m live`.

Legacy closed-track checkpoint experiments may use `--deterministic-checkpoint`
with a complete audited deterministic exploration condition and
`--no-deterministic`. Confirm the starting point with the user for each new
experiment. This opt-in requires cost tracking without a wall deadline; the
default remains original-start. Original proofs are still freshly measured,
canonical denominators stay fixed, and each checkpoint is freshly checked in
a private cell cache before any model call. No model-produced seed is accepted
through this interface. Reports separate the checkpoint score from subsequent
model gains. Keep the source condition and runtime frozen; incomplete checkpoint
verification is never automatically replayed.
