# Runtime architecture

The maintained runtime is one installable package. CLI commands call library
APIs; no library imports an experiment driver. Historical studies stay in
`results/`; their retired source can be recovered from checkpoint `bfb2ade6`.

| Package | Responsibility | Main API |
| --- | --- | --- |
| `verification` | Pinned Lean compilation, token counts, cached references, goal observations | `Evaluator`, `check_references` |
| `optimization` | Parsed proof edits, tactic discovery, minimization, bounded cleanup, generic deterministic batches | `Budget`, `optimize`, `cleanup_proof`, `BatchConfig`, `run_batch` |
| `providers` | Codex transport/isolation, RCP client, terminal usage, price estimates | `codex.generate`, `RCPClient`, `CostConfig` |
| `harness` | Prompt/context policy, tool sessions, one-theorem search, batch coordination and reports | `ProofSession`, `ProofToolService`, `RunConfig`, `run` |
| `benchmark` | Explicit project setup and one-time reference processing | `process_benchmark` |
| `evidence` | Atomic artifacts, stable hashes and saved-evidence audits | `write_json`, `fingerprint`, `audit` |
| `interfaces` | Thin CLI and localhost HTTP evaluation interfaces | `proof-eval` |

`harness/search.py` owns one theorem's model request and final cleanup.
`harness/runner.py` owns concurrency and the complete declared cohort.
`harness/agent.py` supplies prompt policy and the tool service to the general
Codex transport. Provider code does not import the harness or decide which proof
wins. The host-owned `ProofSession` makes that decision from evaluator results.
RCP remains a separate chat transport; the current live tool-agent runner uses
Codex. A custom agent implementation can be passed as `run_cell(..., generator=...)`.

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

Codex transport accepts exact `model`, `effort`, prompt messages, tool
instructions, a session, a tool-service factory, and pinned CLI identity.
`harness.agent.generate` supplies that wiring for search. Requests, started
markers, CLI events and terminal responses are durable. An interrupted started
request is recorded as indeterminate and is never silently sampled again.
Codex's CLI does not provide this experiment with a hard output-token cap or
temperature control. The active configurations are Sol 6.1/max and Astra/max.

```python
from proof_eval import RCPClient
from proof_eval.providers.costs import CostConfig, estimate_codex_cost

client = RCPClient(env_path=".env")  # Explicit construction reads credentials.
# client.create_chat_completion(...) dispatches an RCP request only when called.
cost = estimate_codex_cost(CostConfig("gpt-6.1-sol", "max"), saved_codex_usage)
```

`estimate_configuration()` reprices complete saved traces as a scenario.
`generations_cost()` includes every attempt; missing usage remains unknown.
`proof-harness estimate` records scenarios before any model or Lean calls.
Standard/short-context API-equivalent pricing is not a Codex invoice. The $3
competition limit applies per problem. Current comparison runs report costs
without imposing a stopping budget.

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
| `src/rcp.py` | `rcp-chat`, or public `RCPClient` |

Other one-shot, repair, per-model and analysis drivers are retired. Their saved
results remain readable; recover their code from `bfb2ade6` when historical
reproduction is specifically needed. There is no live legacy scripts directory.

`make format`, `make check`, and `make test` use pinned Black/Ruff and the offline
pytest suite. GitHub Actions runs the same checks. Lean/Codex local integration
tests skip explicitly when dependencies are absent; tests using the installed
Codex route requests to a localhost fake server. Remote paid tests are marked
`live` and excluded by default. Run them only explicitly with `pytest -m live`.
