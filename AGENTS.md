# Working in this repository

This repository optimizes Lean proofs for Lean Refactor Arena. Read `README.md`
and `docs/ARCHITECTURE.md` before changing the runtime. The active model conditions
are **gpt-6.1-sol/max** and **gpt-6-astra/max**. The default search uses the revised
prompt and score feedback, with three separate cohort phases: one-sweep cleanup
of every theorem, model search, then one-sweep cleanup of each model condition's
outputs. Both cleanup phases default on, with eight workers and no five-minute
cap. Model jobs contain no deterministic transforms. Sol and Qwen default to
five model workers; phase worker counts are independently configurable.
Restart history is off by default; enable it explicitly with `--restart-history`.
The default starting state is the original dataset. Reuse cleaned/optimized proofs
only through an explicit `--starting-proofs` path, retaining source provenance,
fresh all-version checks and private per-cell candidate/analysis caches.
There is one canonical prompt in `prompts/refactor_system.md`, with the experimental
priority and five-card revision in `prompts/strategy_bank.json`; historical V2
runs retain their frozen bytes. Provider probes use native
Lemex (`deepseek-ai/DeepSeek-V4.1-Flash/high` and
`Qwen/Qwen3.8-Flash-Next/xhigh`) and Claude Code
(`claude-opus-5-5/max`), keeping the same task and host proof tools.

## Organize code by responsibility

- Put maintained Python code in `src/proof_eval/`. Use its existing packages:
  `verification`, `optimization`, `providers`, `harness`, `benchmark`, `evidence`,
  and `interfaces`.
- Entry points belong in `pyproject.toml` and thin CLI modules. Library modules
  must never import an executable experiment script. Do not add `src/run_*.py`,
  per-model drivers, duplicated utilities, or a miscellaneous scripts folder.
- Keep transport, prompt policy, proof selection, verification, and reporting
  separate. `harness/search.py` handles one theorem; `harness/runner.py` handles
  a batch. Reuse `evidence/io.py` for identities and atomic JSON writes.
- Annotate public interfaces and use explicit configuration objects. Importing a
  library must not dispatch requests, compile Lean, read credentials, or create
  result files. Put such work behind explicit calls.
- Give modules one purpose. Split a growing module when responsibilities diverge;
  avoid adding another study's orchestration to an existing large file.

## Preserve measurement and experiment contracts

- Before launching each new experiment, ask the user to confirm one concrete
  configuration: dataset/cohort, model and effort, starting proof state/path,
  before/after cleanup, worker counts for each phase, history setting, model
  time/cost limits, output directory and overall resource allowance. Previously
  confirmed settings authorize that exact experiment; do not ask again for its
  unchanged resume. Preparation, offline tests and read-only analysis need no
  experiment approval. Do not launch a model or Lean search experiment merely
  to test a code change.
- New harness runs explicitly measure the original proof on every required version
  inside the model-phase clock before any model call. Keep canonical scoring denominators
  pinned; save the fresh measurement separately. General evaluator/reward calls must
  still never remeasure reference denominators implicitly. An explicitly selected
  starting proof is freshly verified; never import another run's candidate/analysis
  cache. Raw JSONL inputs have declared external provenance, not an implied audit.
  Labelled model-produced inputs must match the receiving model and effort.
  New runs allow one recorded original-measurement retry only after a terminal
  wall timeout; keep both attempts, the same pinned verifier, private caches,
  and the original problem clock. Never replay an interrupted measurement or
  retry a semantic failure.
- Keep the dataset's original token denominator. Measure candidates using fresh
  pinned `lake env lean`, synchronous `Elab.async=false`, and the existing
  `IO.getNumHeartbeats` wrapper. Timing and `--profile` are not heartbeats.
- `verification/backend.py` is intentionally byte-frozen: its source hash is part
  of existing reference fingerprints. Black excludes that single file; Ruff
  still checks correctness rules. A backend change needs an explicit measurement
  version and a separately prepared cache, never silent cache substitution.
- Keep the best proof passing **every required version**, with the configured
  0.05 percentage-point improvement margin. Deterministic work defaults to the
  measured `one_sweep` plan: all sixteen methods in gain order, one traversal,
  per-method rounds=3, trials=32, sites=6; no overall five-minute cap. Keep finite
  work bounds and verifier/discovery watchdogs. Cleanup must finish across the
  cohort before model search begins; postprocessing starts after the model batch
  and uses each condition's own outputs. Use --no-deterministic for model-only.
  A recorded deterministic discovery timeout retains its valid incumbent and is
  a limited search outcome, not a claim that discovery completed. Other discovery
  failures remain incomplete. Preserve and audit the terminal timeout evidence.
- Keep prompts, model settings, model-to-track classification in
  `providers/registry.py`, source projects, denominators, and cohort size fixed
  for matched experiments. Routing additions must declare their track separately
  in `MODEL_TRACKS`; classification changes require a new output directory.
  Do not feed another condition's solutions to a model. Report full-cohort means
  only when the full declared cohort is complete.
  Each condition keeps one model and effort for all attempts. Mixed-model
  handoffs are retired; preserve their saved evidence for read-only audit.
- Model requests need durable started markers, host-owned evidence, output locks,
  and no automatic resampling of an indeterminate request. Preserve partial work.
  Observed terminal transient transport failures may use bounded, recorded
  recovery from the best verified proof under the same selected problem budget.
  Preserve every failed attempt. Strict cost tracking stops when cumulative usage
  becomes unknown. New Codex cost runs default to pinned `usage_policy="best_effort"`:
  retain reported counters, explicit unknowns and separate heuristic estimates;
  use their estimated total for admission and bounded terminal transport recovery.
  Never retry an indeterminate or still-active request. Historical configurations
  without a usage policy retain strict behavior; changing policy needs a new output.
  Codex may use tools; the host checks proofs and owns the ledger. Do not let model
  processes write the pinned source projects or host evidence.
  Default host bounds are 20 optimization restarts and two terminal transport
  recoveries: at most 23 admitted attempts per problem, including the initial
  attempt. Configure them separately with `max_budget_restarts` and
  `max_transport_restarts`; native HTTP/stream retries stay inside their session.
- New runs automatically select one track budget: Qwen uses a 14400-second
  (four-hour) model-phase deadline per theorem; other open models retain their
  explicit/default allocation (currently 3420 seconds for DeepSeek). Model-phase
  measurement, admission and tools count inside that timer; cohort cleanup is
  measured separately and contributes to whole-workflow wall time;
  closed models use a $3 per-problem API-equivalent cost budget with no implicit
  wall-time limit. A numeric timeout explicitly adds a watchdog to cost tracking.
  Preserve the best fully checked proof when the selected budget is exhausted;
  distinguish a controlled budget stop (deadline or cost limit) from a missing
  native final or transport error. Resuming never replenishes a budget.
  Default to an isolated current runtime copy for closed-track runs. Their pinned
  files remain frozen until every cell is terminal, which can take hours or days
  without a wall-time limit. Use an isolated copy for other runs whenever
  development must continue.
  New runs have no model-budget cleanup reserve. Cleanup spends no model dollars.
  Report before/model/after times and total elapsed time; never present model-only
  time as the full workflow. The user-reported competition allocation is a 48-hour
  node with 64 physical CPU cores and four A100 80GB GPUs; this is a whole-workflow
  resource allowance, not a GPU-hour conversion or an automatic harness watchdog.
  Confirm the resource plan for the selected cohort. Historical 57-minute total
  deadlines, five-minute initial caps and edge cleanup remain read-only evidence.
- Do not edit pinned runtime or prompt files while an experiment is running.
  Use a new output directory when code, inputs, settings, or budgets change.
- Keep historical result/config/request bytes unchanged. Auditors may verify
  matching sources under `results/deterministic/validation/implementation_snapshots`;
  they must not execute snapshots. Retired drivers can be recovered from the
  pre-refactor checkpoint `bfb2ade6` in an isolated checkout.
- Preserve generated result bytes even when an original proof contains trailing
  whitespace. `.gitattributes` exempts those archives from Git whitespace checks;
  Black and Ruff also exclude result archives. Never format saved evidence.
- Report local and organizer scores separately. API-equivalent prices are
  estimates, not Codex invoices. The closed-track cap applies to **each problem**;
  missing usage stays unknown even when best-effort estimates permit continuation.
  Label incomplete estimated costs and their assumptions; never present payload
  heuristics or a zero estimate for failed requests as reported usage or an invoice
  cap. Preserve every terminal inference counter across compaction. RCP permits
  at most five simultaneous requests
  across the key; this shared admission cap is the RCP throughput limiter when
  wall time no longer bounds runs. Respect it across batches and clients.
  Do not put credentials in results, logs, or Git.
- Use the native provider adapters and shared durable executor. The direct RCP
  chat client is retired. Leave native sampling defaults alone; do not invent a
  CLI temperature flag or claim that an unobserved gateway default equals 1.
- Never substitute another Claude model/effort after an authentication or model
  failure. Inspect the terminal result and actual model, not just the exit code.
  Claude's reported cost is a client-side API estimate, not an invoice. Keep
  unknown gateway prices unknown.
- Preserve reported cache-write durations and reasoning counters. Reasoning is
  a subset of output, never an extra output charge. Retain recovered tool denials
  without turning a successful native terminal response into a transport error.

## Check quality before handing off

Use `conda activate af` here, or a clean Python environment with
`python -m pip install -e '.[dev]'`.

```bash
make format   # Black and Ruff import ordering; inspect changes
make check    # Black --check and Ruff lint
make test     # pytest; paid remote tests excluded by default
```

For a focused fix, run the relevant tests first, then the full offline suite when
interfaces or shared behavior changed. Prefer tests of observable contracts:
reference reuse, score arithmetic, all-version gating, resume, provider routing,
tool boundaries, and a small end-to-end batch. Do not add tests that merely repeat
the implementation or use a paid model call as a default unit test.

Model batches start the full selected cohort directly, with no pilot gate.
Default to eight workers independently in each cleanup phase, five for Sol and
Qwen model search, and three for DeepSeek. Override with `--cleanup-workers`,
`--before-workers`, `--after-workers` and `--model-workers`; positive counts are
allowed while the shared provider admission limit still applies. Individual
incomplete outcomes or worker failures must not cancel other queued theorems.
Keep cached-reference and runtime preflight checks, and run `proof-harness audit`
on saved evidence. State what actually completed, the validation performed,
and any incomplete outcomes. Keep user-owned untracked files untouched.

The standard interface accepts an explicit `--starting-proofs` manifest/directory
or organizer-style JSONL on either track. Confirm it in the experiment plan.
Reusing prepared proofs saves local work but does not erase their provenance or
prior compute cost. Separate imported-state, pre-cleanup, model and post-cleanup
scores. Use a new output for changed inputs or settings.

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
