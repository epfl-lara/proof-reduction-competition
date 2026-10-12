# Proof Reduction Competition

Lean proof optimization for [Lean Refactor Arena](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena). The active model configurations are **Sol 6.1/max** and **Astra/max**. The default harness uses the revised prompt, source/goal tools, measured score feedback, and deterministic cleanup at the beginning and end.

The warm-up benchmark contains 15 declarations and 36 required version checks. We score candidates against the original dataset token counts and cached local heartbeat measurements. The combined objective is the mean of length reduction, heartbeat reduction and compatibility. Local measurements and organizer scores are reported separately.

## Start here

```bash
conda activate af
python -m pip install -e '.[dev,semantic]'
make check
make test
```

Core verification has no third-party runtime dependencies. Default semantic
discovery requires the semantic extra and prepared local assets. Lean evaluation
needs the pinned, prebuilt projects listed in the local environment map. The
existing warm-up references are already prepared; search never remeasures them.

Literal source search includes the project's installed Lake dependencies, with
project-local matches first. Semantic discovery is enabled by default and uses
LeanExplore's cached index and CPU embeddings:

```bash
python -m pip install -e '.[dev,semantic]'
# Prepare the index and Qwen/Qwen3-Embedding-0.6B cache before running.
lean-explore data fetch
proof-harness run --provider lemex --condition Qwen/Qwen3.8-Flash-Next:xhigh \
  --semantic-search --output results/harness/my_qwen_tools_run
```

Semantic discovery only reads already cached assets and freezes their hashes
and dependency versions. Web search is also enabled by default, through separate
host tools. The index may use different source versions, so its declaration headers and docstrings are
discovery hints; use pinned source lookup and all-version checks to validate
them. Indexed proof bodies are omitted. Strata and Arklib currently have no
project-specific index coverage; their pinned source and dependency searches
remain available.

All proof, source, profiling, semantic and web tools are available by default
for new runs. Disable discovery features explicitly with `--no-semantic-search`
or `--no-web-search`. Python callers can use `semantic_search=False` and
`web_search=False`; `semantic_search=None` also disables semantic discovery.
Default semantic assets are located only during explicit preparation, not when
importing the package or constructing `RunConfig`. Missing assets fail preflight
with setup guidance rather than silently reducing the tool set.

```bash
# Price scenarios from saved traces; no model or Lean calls.
proof-harness estimate --condition gpt-6.1-sol:max \
  --output results/harness/my_sol_run

# Run all 15 with five parallel workers. Repeating reuses completed cells.
proof-harness run --condition gpt-6.1-sol:max \
  --output results/harness/my_sol_run

# Saved evidence only.
proof-harness report --output results/harness/my_sol_run
proof-harness audit --output results/harness/my_sol_run
```

Omit `--condition` to run both active models, or specify `gpt-6-astra:max` for the SOTA condition. New runs automatically use one track budget per problem:

- **Open models (Qwen and DeepSeek): 57 minutes**, including provider admission, Lean tools and final cleanup; no dollar guard.
- **Closed models (Sol, Astra, Claude and Gemini): $3 API-equivalent estimated cost**, across all attempts; no wall-time limit by default.

The host retains the best proof verified across every required version. Resuming never replenishes the selected budget. Successful voluntary completion starts a fresh attempt from that proof while budget remains. Costs are reported from recorded usage and explicit pricing assumptions.

Model-to-track classification is declared separately from provider routing in
`MODEL_TRACKS` in `providers/registry.py` and pinned with each run's source.
Adding provider support alone does not classify a model for automatic budgets.
Default to an isolated current runtime copy for closed-track runs: without a
wall deadline, the entire cohort can hold its pinned files for hours or days.
RCP's shared five-request cap remains its throughput limiter across batches and
clients.

Batches queue the full selected cohort directly. Codex and the other closed
providers use exactly five parallel workers; Lemex uses exactly three. For 15
theorems, these are five slots across three groups or three slots across five
groups. There is no model-run pilot option or gate. An incomplete theorem or
worker failure is recorded while the remaining queued theorems continue.
The selected usage policy controls admission when usage counters are missing.

`--budget-tracking auto` is the default. Choose `--track-cost` or `--track-time` explicitly to override the track policy, and use a new output directory when changing settings:

```bash
proof-harness run --condition gpt-6.1-sol:max --track-cost --budget-usd 3 \
  --output results/harness/my_sol_cost_run

proof-harness run --provider lemex --condition Qwen/Qwen3.8-Flash-Next:xhigh \
  --track-time --output results/harness/my_qwen_time_run
```

`--budget-tracking cost` and `--budget-tracking time` are the long forms. Each
successful voluntary completion starts another conversation and workspace from
the best verified proof while budget remains. The default safety limits are 20
optimization restarts (`--max-budget-restarts`) and two transport recoveries
(`--max-transport-restarts`): at most 23 admitted attempts per problem, including
the initial attempt. Native HTTP/stream retries stay inside their session.
Time-limited restarts stop when at most 30 seconds remain for final cleanup;
this reserve is inert in cost-only runs. Final cleanup uses deterministic
transformations and Lean, makes no model requests and spends no model dollars.
Indeterminate requests, permanent failures and unavailable verification never
trigger a retry. Strict cost tracking stops when cumulative spending is unknown.
Cost tracking requires a priced model; use time tracking for Lemex models.

Transient gateway failures have separate recovery limits. Lemex allows four
HTTP retries and five stream retries within its native conversation. After an
observed terminal transient failure, the host permits up to two new sessions
from the best verified proof, with bounded backoff and the same problem budget.
Use `--max-transport-restarts 0` to disable host recovery. Transport recovery has
its own restart count, separate from successful optimization attempts. Reconnect
notifications remain in the evidence, and
unreported usage from interrupted responses stays unknown.

New Codex cost runs default to `--usage-policy best_effort`. They retain native
request traces and a host-owned `response_usage.json` for each attempt, including
every reported response counter before and after context compaction. Missing
counters remain explicitly unreported. For budget admission, the host adds
separately recorded heuristics: compaction input uses the nearest preceding
reported inference input plus output, and compaction output uses the nearest
following reported inference input as a conservative proxy. Each estimate saves
its source counters. Missing neighbors and partial responses without counters
use canonical UTF-8 JSON bytes divided by four, rounded up. Unreported input is
priced as uncached. A failed request with no partial output is estimated at zero, an
assumption rather than evidence of zero charge. These estimates can overstate
or understate actual usage, especially for encrypted compaction payloads.

Best-effort accounting permits bounded recovery from an observed terminal
transient failure, including missing usage, while deducting all reported and
estimated spending from the same problem budget. Successful native retries keep
their successful outcome. Explicit capacity/rate-limit refusals without partial
output remain recorded as rejected requests under the existing refusal policy.
When a conservative native token allowance stops a session before the cumulative
estimate reaches the dollar target, best-effort tracking can start a fresh
session from the verified incumbent using the remaining dollars.
Estimates never replace reported counters or claim
complete usage. Missing or inconsistent trace evidence that cannot support an
estimate still stops cost tracking. Use `--usage-policy strict` to stop whenever
cumulative usage is unknown. The policy is pinned with new configurations;
historical configurations without it retain strict behavior and unchanged bytes.

For an explicitly authorized new run after an old interruption, pass
`--incumbents-from results/harness/prior_run` and a new `--output`. The harness
pins and validates that condition's saved proofs, reference identities and
theorem context without remeasurement. The new run receives a fresh track budget;
all automatic recoveries inside it share that one budget. Other model conditions
cannot supply its proofs.

To continue a stopped cost-tracked run after a runtime fix without replenishing
its budget, use `--carry-budgets-from results/harness/prior_run` with a new output.
The harness audits and pins prior evidence, counts every prior attempt, preserves
any explicitly configured original deadline, and reuses that condition's best
verified proof. Unknown cumulative spending or an unfinished prior request
blocks continuation. The source and destination must use the same usage policy;
carrying a historical budget without that field requires `--usage-policy strict`.

Cost tracking passes the remaining budget to the native CLI and sums observed
costs across attempts. Codex uses a conservative weighted token allowance;
Claude uses its dollar allowance. Both check between upstream responses, so a
response already in flight may exceed the target. This is an API-equivalent
estimate with explicit stop evidence, not a certified hard invoice cap. Native
limit stops may omit usage; such counters remain unknown, with best-effort
estimates separately identified where available. Cost-only calls through
the Python search API also have no implicit deadline.
An explicit `--problem-timeout-seconds` / `RunConfig.problem_timeout_seconds`
adds a wall-time watchdog when requested; it overrides the 3420-second allocation
for time tracking. Python callers can set `budget_tracking=None` for a single
voluntary attempt under the time limit.

Each condition keeps the same model and effort for every attempt. Mixed-model
handoffs are retired. Their saved reports and evidence remain available for
read-only inspection and audit; they cannot seed or resume a new search.

There is one active task policy: [refactor_system.md](prompts/refactor_system.md)
and its five-card [strategy bank](prompts/strategy_bank.json), preserving the
revised V2 contents used for the recent Sol runs. There is no prompt-version or
search-mode selector. All providers use score feedback and cleanup at the edges.

Native Lemex, Claude Code and Google Antigravity run the same task with their own shell/edit tools:

```bash
# DeepSeek: existing .env gateway key is passed only to the Lemex child.
proof-harness run --provider lemex \
  --output results/harness/my_deepseek_run

# Qwen with the same score, source, goal and tactic-profiling tools.
proof-harness run --provider lemex --condition Qwen/Qwen3.8-Flash-Next:xhigh \
  --output results/harness/my_qwen_run

# A separate web-enabled condition, retaining the local semantic tools.
proof-harness run --provider lemex --condition Qwen/Qwen3.8-Flash-Next:xhigh \
  --semantic-search --web-search \
  --output results/harness/my_qwen_web_run

# Sign in with `claude auth login` first. Exact Opus 5.5/max, no fallback.
proof-harness run --provider claude \
  --output results/harness/my_opus_run

# Antigravity `agy` with an existing Google login. Exact Gemini 3.8 Flash/high.
proof-harness run --provider agy --track-cost --budget-usd 3 \
  --output results/harness/my_antigravity_run
```

`--web-search` enables `python tools.py web_search` and `web_open` for public
HTTPS sources. The host uses DuckDuckGo Lite for discovery and saves each
request, response and fetched source body. This works independently of native
hosted search, which the RCP probe did not expose. External information is a
discovery hint; the pinned Lean checks and scoring rules remain authoritative.
Use a new output directory when changing tool availability. Web search defaults
to enabled and requires no additional API key; `--no-web-search` disables it.

Lemex defaults to `deepseek-ai/DeepSeek-V4.1-Flash/high`. The direct RCP chat
client and its temperature/output-cap settings are retired. Native Lemex sends
no temperature override; the gateway's effective default is not exposed by the
CLI. Claude uses `claude-opus-5-5/max`, with normal project configuration and
authentication discovery. Each provider has separate output and usage evidence.
Claude's reported API-equivalent cost includes its actual cache durations and
any auxiliary models. Antigravity uses `gemini-3.8-flash/high` (the suffixed
`--model` slug, no separate effort flag) and prints stream-json evidence from an
existing `agy` login; its system policy, tool instructions and user message are
merged into one prompt and therefore reach the model as user-level instructions.
Complete usage from failed calls is also retained. The exact DeepSeek gateway
price and the exact Antigravity price remain unknown. Antigravity cost tracking
uses an explicit standard Gemini API-equivalent estimate: $0.75/M ordinary
input, $0.075/M cached input, and $3.75/M output including thinking, effective
through December 31, 2026. A host supervisor watches the streamed usage and
stops the native process at its remaining per-problem budget. Repeated step
snapshots are counted once; terminal usage replaces the step subtotal. An
in-flight response can overshoot, and cache-storage/subscription charges are
not inferred. Missing terminal usage remains unknown, with the observed
subtotal retained. See [Google pricing](https://ai.google.dev/gemini-api/docs/pricing).

Every completed condition exports `conditions/MODEL__EFFORT/selected_candidates.jsonl`, with one complete declaration per benchmark ID in the organizer's submission format. Invalid or regressive attempts preserve the best proof passing every required version. In-loop deterministic cleanup is retired.

## APIs and code organization

All maintained code lives in [src/proof_eval](src/proof_eval). There are dedicated packages for verification, deterministic optimization, provider calls, the model harness, benchmark setup/processing, evidence, and CLI/HTTP interfaces. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for APIs, tool requests, artifacts, resume behavior and the command migration table. [AGENTS.md](AGENTS.md) records implementation and measurement practices. Black, Ruff and pytest run in GitHub Actions using the same `make` commands.

```python
from pathlib import Path
from proof_eval import Evaluator
from proof_eval.harness.config import RunConfig
from proof_eval.harness.runner import run

# Candidate scoring / GRPO reward adapter; references are read from the cache.
evaluator = Evaluator()
result = evaluator.evaluate("putnam_1964_a4", candidate_code, versions="all")
reward = evaluator.reward("putnam_1964_a4", candidate_code)

# Model search uses the same host evaluator and tools.
report = run(RunConfig(
    output=Path("results/harness/my_sol_run"),
    conditions=(("gpt-6.1-sol", "max"),),
))
```

`proof-eval` also provides a JSON CLI and localhost HTTP API:

```bash
proof-eval evaluate putnam_1964_a4 --code-file candidate.lean
proof-eval profile putnam_1964_a4 --code-file candidate.lean --output profile.json
proof-eval serve --port 8765 --workers 2
```

Models can use `python tools.py profile candidate.lean` to find tactic heartbeat
hotspots, or add `profile_tactic "label" in tac` in a diagnostic copy to measure
a chosen tactic or block. Costs are inclusive and include profiling overhead;
`check` still owns scoring and proof selection. See [tactic profiling](docs/PROFILING.md).

The generic deterministic API accepts a new competition batch with explicit paths and prepared references. See [docs/DETERMINISTIC_BATCH.md](docs/DETERMINISTIC_BATCH.md). `proof-benchmark` processes references once; `proof-setup` builds the pinned source projects. These are explicit setup actions, separate from search.

## Data, rules and results

- [RULES.md](RULES.md): saved competition rules and pinned upstream links.
- [data/benchmark_data_warmup.jsonl](data/benchmark_data_warmup.jsonl): unmodified warm-up data; SHA-256 `6209680cf00cde0765b77b24834cd72c64dd585b2f7e3f2a58209980ab59a804`.
- [data/benchmark_heartbeats.jsonl](data/benchmark_heartbeats.jsonl): organizer heartbeat references, preserved separately from local ratios.
- [RSI/RL task corpus](data/training/arena_rsi/README.md): 2,057 training and 50 diverse validation tasks from a corpus covering all six sources, curated against Arena's proof-length distribution. Arena is the test set. Source fidelity and native parsing are audited; bulk compilation and heartbeat preparation remain pending.
- [problems](problems/README.md): all 15 initial, deterministic and best proof examples with provenance.
- [results](results/README.md): experiment index, including [deterministic](results/deterministic/README.md) and [model harness studies](results/harness/README.md).
- [Sol configuration results and submission](results/harness/05_model_config/README.md): the pre-refactor Sol/max result was 87.342215% combined with 100% compatibility.
- [Refactor validation and fresh Sol replicate](results/harness/06_refactor_regression/COMPARISON.md): 86.575834% combined, 100% compatibility, 36/36 passing versions; the earlier stronger submission is preserved.
- [Native provider studies](results/harness/07_native_agents/README.md): Opus completed one problem; DeepSeek retained an improved proof after a transport failure. Both cohorts are incomplete.
- [Sol tactic-profiling trial](results/harness/08_tactic_profiles/sol61_max/PROTOCOL.md): 15/15 complete and audited; 86.951351% combined, 100% compatibility. Profiling was used on every problem; one repeat does not establish a causal score gain.
- [Qwen Flash Next results and submission](results/harness/09_qwen_flash_next/README.md): the combined original/recovery selection reaches 78.219958% locally over all 15 problems, with 100% compatibility and 36/36 passing version checks. The saved-evidence audits and submission provenance are included.
- [related_work](related_work/README.md): literature, papers and research proposals.
- [prompts](prompts): the one active revised task policy and strategy bank.

Historical study drivers and their dedicated tests were retired during the package cleanup. Their result evidence remains unchanged, and their original sources are saved in Git checkpoint `bfb2ade6` and content-addressed audit snapshots. Current experiments use the maintained APIs and commands above.
