# Working in this repository

This repository optimizes Lean proofs for Lean Refactor Arena. Read `README.md`
and `docs/ARCHITECTURE.md` before changing the runtime. The active model conditions
are **gpt-6.1-sol/max** and **gpt-6-astra/max**. The default search uses the revised
prompt, score feedback, and deterministic cleanup at the beginning and end.
There is one canonical prompt in `prompts/refactor_system.md`, with the revised
V2 five-card context in `prompts/strategy_bank.json`. Provider probes use native
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

- Never remeasure original proofs implicitly. Preparation is a separate, explicit
  action; search and reward functions only read cached reference measurements.
- Keep the dataset's original token denominator. Measure candidates using fresh
  pinned `lake env lean`, synchronous `Elab.async=false`, and the existing
  `IO.getNumHeartbeats` wrapper. Timing and `--profile` are not heartbeats.
- `verification/backend.py` is intentionally byte-frozen: its source hash is part
  of existing reference fingerprints. Black excludes that single file; Ruff
  still checks correctness rules. A backend change needs an explicit measurement
  version and a separately prepared cache, never silent cache substitution.
- Keep the best proof passing **every required version**, with the configured
  0.05 percentage-point improvement margin. Preserve a better raw proof if final
  deterministic cleanup regresses. In-loop deterministic cleanup is retired.
- Keep prompts, model settings, model-to-track classification in
  `providers/registry.py`, source projects, denominators, and cohort size fixed
  for matched experiments. Routing additions must declare their track separately
  in `MODEL_TRACKS`; classification changes require a new output directory.
  Do not feed another condition's solutions to a model. Report full-cohort means
  only when the full declared cohort is complete.
- Model requests need durable started markers, host-owned evidence, output locks,
  and no automatic resampling of an indeterminate request. Preserve partial work.
  Observed terminal transient transport failures may use bounded, recorded
  recovery from the best verified proof under the same selected problem budget.
  Preserve every failed attempt; cost tracking stops when cumulative usage
  becomes unknown.
  Codex may use tools; the host checks proofs and owns the ledger. Do not let model
  processes write the pinned source projects or host evidence.
  Default host bounds are 20 optimization restarts and two terminal transport
  recoveries: at most 23 admitted attempts per problem, including the initial
  attempt. Configure them separately with `max_budget_restarts` and
  `max_transport_restarts`; native HTTP/stream retries stay inside their session.
- New runs automatically select one track budget: open models use a 3420-second
  (57-minute) whole-problem deadline including host tools and final cleanup;
  closed models use a $3 per-problem API-equivalent cost budget with no implicit
  wall-time limit. A numeric timeout explicitly adds a watchdog to cost tracking.
  Preserve the best fully checked proof when the selected budget is exhausted;
  distinguish a controlled budget stop (deadline or cost limit) from a missing
  native final or transport error. Resuming never replenishes a budget.
  Default to an isolated current runtime copy for closed-track runs. Their pinned
  files remain frozen until every cell is terminal, which can take hours or days
  without a wall-time limit. Use an isolated copy for other runs whenever
  development must continue.
  The 30-second cleanup reserve applies only when a wall deadline is configured,
  including an explicit cost-track watchdog. It is inert for cost-only runs.
  Final cleanup uses deterministic transformations and Lean, makes no model
  requests and spends no model dollars; it starts after model search stops.
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
  missing usage stays unknown. RCP permits at most five simultaneous requests
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

Before scaling a model experiment, run `proof-harness run --pilot ...`; it audits
one theorem per selected condition before continuing. Run `proof-harness audit`
on completed evidence. State what actually completed, the validation performed,
and any incomplete outcomes. Keep user-owned untracked files untouched.
