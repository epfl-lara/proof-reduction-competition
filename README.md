# Proof Reduction Competition

Lean proof optimization for [Lean Refactor Arena](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena). The default workflow is:

**One-sweep cleanup of the whole cohort → model search → one-sweep cleanup of each model condition's outputs.**

The three phases have separate worker pools. Both cleanup phases default on, with **eight workers** and no five-minute cap. Sol 6.1/max and Qwen3.8-Flash-Next/xhigh default to **five model workers**. Restart history is **off**. The default starting state is the original dataset; reusing prepared proofs requires an explicit path.

The warm-up cohort has 15 declarations and 36 required version checks. Scores use the original token denominators and pinned local heartbeat references. Combined score is the mean of length reduction, heartbeat reduction and compatibility; local scores and organizer results remain separate.

## Setup and validation

```bash
conda activate af
python -m pip install -e '.[dev,semantic]'
make check
make test
```

Prepare the pinned Lean projects, environment map, reference export and full-cohort input packs before a run. Setup and reference preparation are explicit operations; the optimizer never silently changes reference denominators. See [architecture](docs/ARCHITECTURE.md) and [deterministic batches](docs/DETERMINISTIC_BATCH.md).

Native agents need Linux Landlock ABI 3+ and bubblewrap. Each attempt has a private PID namespace and protected source/evidence paths; missing isolation fails before inference. Semantic search uses an already cached LeanExplore index and CPU embeddings. Web and semantic discovery are enabled by default; disable them with `--no-web-search` and `--no-semantic-search` when explicitly configuring a condition.

## Run the three phases

Confirm the experiment parameters with the user before launching: cohort, model/effort, starting state, cleanup placement, each worker count, history, budgets, output directory and overall resource allocation. Offline tests and preparation do not launch an experiment.

```bash
# Preparation only: pin inputs and check runtime/reference availability.
proof-harness prepare --condition gpt-6.1-sol:max \
  --cleanup-workers 8 --model-workers 5 --output results/my_sol

# Same frozen configuration: run all three phases.
proof-harness run --condition gpt-6.1-sol:max \
  --cleanup-workers 8 --model-workers 5 --output results/my_sol

# Qwen: four hours per theorem in the MODEL phase, five model workers.
proof-harness run --provider lemex \
  --condition Qwen/Qwen3.8-Flash-Next:xhigh \
  --cleanup-workers 8 --model-workers 5 --output results/my_qwen

# Separate cleanup concurrency before and after; history is an explicit opt-in.
proof-harness run --condition gpt-6.1-sol:max \
  --before-workers 16 --after-workers 8 --model-workers 5 \
  --restart-history --output results/my_sol_history

# Model-only baseline from original proofs.
proof-harness run --condition gpt-6.1-sol:max --no-deterministic \
  --output results/my_sol_model_only

# Saved evidence only.
proof-harness report --output results/my_sol
proof-harness audit --output results/my_sol
```

`--cleanup-workers` sets both deterministic pools; `--before-workers` and `--after-workers` override them independently. `--workers` is an alias for `--model-workers`. Positive worker counts are configurable; the shared RCP admission cap of five simultaneous requests still applies across clients and batches. More cleanup workers do not authorize more gateway requests.

`--no-cleanup-before` and `--no-cleanup-after` disable an individual phase. `--no-deterministic` disables both. No deterministic transform runs inside a model job. A whole-cohort barrier separates the phases; queued theorems continue after individual worker failures, but incomplete cohorts do not acquire full-cohort scores or reusable cleanup states.

## One-sweep policy

The default is the exact `one_sweep` schedule tested in the completed development study:

```
simp menu facts search proof_theory collapse wrappers arith_min
lint delete golf reuse relax simp_min rw_min consolidate
```

Each method is visited once, with its bounded local search (`rounds=3`, `trials=32`, `sites=6`). An accepted proof must pass every required version and improve the combined score by more than 0.05 percentage points. There is no overall 300-second cleanup cap; individual Lean/discovery watchdogs and finite method work bounds still apply. Recorded discovery timeouts preserve valid incumbents as limited search outcomes, not exhaustive-search claims.

The measured one-sweep development result was **+12.184 points**, **23.5 minutes per theorem on average**, and **5.87 summed worker-hours** over all 15 theorems. Replaying those measured durations estimates **53 minutes with eight workers** or **46 minutes with sixteen**; these are scheduling estimates, not measurements on the competition hardware. The [completed Sol workflow comparison](results/summary/20261022_sol_cleanup_placement/README.md) measured 89.3761% in 3h 59m with both cleanup phases, versus 89.6591% in 3h 17m with cleanup only at the end. These are single runs; the default still enables both phases.

To run just a cleanup phase:

```bash
proof-deterministic --output results/my_cleanup --workers 8
proof-deterministic --output results/my_cleanup --audit
```

The output includes `state.json`, final proofs/evaluations, full search evidence, a report and an audit. See [batch inputs and reuse](docs/DETERMINISTIC_BATCH.md) for another dataset or cohort size.

## Starting proofs and reuse

Original dataset proofs are the default. To explicitly reuse a prior cleanup or model state:

The 15-problem [original and one-sweep starting sets](problems/README.md#choose-the-models-starting-proofs) are saved side by side, each as `state.json` and `{name, proof}` JSONL. Use `--starting-proofs problems/starting_states/one_sweep --no-cleanup-before` to reuse the selected saved cleanup; omitting the starting-state flag runs the full pipeline from originals.

```bash
proof-harness run --condition gpt-6.1-sol:max \
  --starting-proofs results/my_cleanup/state.json \
  --no-cleanup-before --output results/my_sol_from_cleanup
```

`--starting-proofs` accepts a `state.json`, a cleanup directory containing that file, or explicit JSONL records with `name` and a full `proof` declaration (`code` is also accepted). The state must cover the exact declared cohort. Selecting a state does not implicitly disable cleanup; use `--no-cleanup-before` to avoid another sweep. Model-produced manifests retain model/effort lineage and cannot seed another condition. Raw JSONL has external, unverified provenance until the fresh compiler checks; it is not represented as an audited deterministic checkpoint.

Every model cell freshly measures its original proof and verifies any selected state against every required version in its own private cache. The original scoring denominators remain fixed. Invalid or interrupted input checks never trigger a silent replay, and a valid imported proof does not replace a better verified original. Reports separate the starting state, before-cleanup gain, model gain and after-cleanup gain. Reusing a state does not erase its earlier compute cost.

The older `--deterministic-checkpoint` interface remains a separate closed-track, cost-only compatibility path requiring `--no-deterministic`. It does not accept model-produced seeds. Use `--starting-proofs` for the new phase workflow.

## Budget and time accounting

| Condition | Default per-theorem model budget | Default model workers |
| --- | --- | ---: |
| Sol 6.1/max, Astra/max and other closed models | $3 API-equivalent estimate; no implicit wall deadline | 5 |
| Qwen3.8-Flash-Next/xhigh | Four hours (14,400 seconds) | 5 |
| DeepSeek V4.1 Flash/high | 57 minutes (3,420 seconds) | 3 |

`--problem-timeout-seconds` changes the model-phase time budget or adds an explicit watchdog to a closed cost run. `--budget-usd` changes the per-theorem cost target. `--track-time` and `--track-cost` explicitly select the budget policy. A mixed cohort with incompatible default time allocations needs an explicit timeout.

Model-phase time includes its original/selected-proof measurements, provider admission, model inference and host tools. Both cleanup phases have separately measured wall time and do not consume that timer. The pipeline report also records total elapsed wall time, including phase transitions and resume gaps. With no overall workflow watchdog, the per-theorem timer alone does **not** enforce the user-reported 48-hour node allocation. Confirm scheduling against the full cohort and hardware before an experiment. For example, 50 Qwen problems at four hours and five workers allocate 40 hours to model waves alone, before both cleanup phases and overhead.

Resuming never replenishes a budget. Indeterminate native requests are not automatically resampled. Terminal transient failures have separately bounded recovery: defaults are 20 optimization restarts plus two transport recoveries, at most 23 admitted attempts per theorem. Every condition keeps one model and effort throughout.

New Codex cost runs use `--usage-policy best_effort`: native reported counters remain separate from heuristic estimates for missing usage. Strict mode stops when cumulative usage is unknown. API-equivalent estimates are not invoices or certified hard caps; response boundaries can overshoot. Qwen/DeepSeek gateway prices remain unknown. See [accounting details](docs/ARCHITECTURE.md).

## Native providers, isolation and monitoring

Use `--provider codex`, `lemex`, `claude` or `agy`. Codex defaults to Sol 6.1/max and Astra/max; Lemex defaults to DeepSeek V4.1 Flash/high, so specify Qwen explicitly. Claude uses exact Opus 5.5/max without fallback; Antigravity uses Gemini 3.8 Flash/high. Native sampling defaults are unchanged.

For isolated Lemex runs, pin a private catalog with `PROOF_EVAL_LEMEX_CATALOG` before preparation and execution. Missing explicit catalogs fail preflight. Credentials go only to the provider child environment and must never enter results or Git.

Use an isolated runtime copy whenever code development may continue during an experiment. Source, prompts, model identity, settings and input hashes stay frozen until the run is terminal. Use a new output directory after changing them. Completed stages are audited and reused on identical resume; started cells without terminal evidence remain incomplete for investigation.

`proof-watch --spec watch.json --output watch-results` monitors explicit result roots/services and records deduplicated local alerts for failures, missing terminal evidence, correlated exits and completion. It never retries, stops jobs or sends chat/email messages.

## Evidence and decisions

The [October 21 summary manifest](results/summary/20261021_deterministic_workflows/manifest.json) covers all **8 Sol and 5 Qwen conditions**, **24 capped deterministic policies**, **5 extended policies**, and **630 selected theorem results**. It includes source hashes, final declarations/evaluations, saved reports/audits and [model](results/summary/20261021_deterministic_workflows/model_conditions.csv) / [deterministic](results/summary/20261021_deterministic_workflows/deterministic_conditions.csv) tables. Full raw session evidence is preserved in a private local archive; compact publication files do not replace the raw dependencies of historical audits.

The best observed Sol result was **90.237%** in the legacy PR/history-off configuration. Clean original-start model-only scores were **89.645% / 89.453%** for Sol history on/off and **80.038% / 81.148%** for Qwen. These single development runs do not establish repeatability. The new one-sweep/before-and-after, history-off workflow is a user-selected trade-off based on measured preprocessing value and available hardware, not a claim of a measured new model winner.

The six new transforms were adapted from [Gordan's PR #1](https://github.com/epfl-lara/proof-reduction-competition/pull/1). The existing ten methods remain in the selected sweep. We did not adopt the PR's alternative restart/tree orchestration; the maintained host harness owns restarts, budgets, verification and phase barriers.

Other references: [rules snapshot](RULES.md), [warm-up data](data/benchmark_data_warmup.jsonl), [organizer heartbeats](data/benchmark_heartbeats.jsonl), [result index](results/README.md), [proof examples](problems/README.md), [canonical prompt](prompts/refactor_system.md), [strategy bank](prompts/strategy_bank.json), and [RSI/RL corpus](data/training/arena_rsi/README.md).
