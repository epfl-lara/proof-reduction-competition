# Proof Reduction Competition

Lean proof optimization for [Lean Refactor Arena](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena). The active model configurations are **Sol 6.1/max** and **Astra/max**. The default harness uses the revised prompt, source/goal tools, measured score feedback, and deterministic cleanup at the beginning and end.

The warm-up benchmark contains 15 declarations and 36 required version checks. We score candidates against the original dataset token counts and cached local heartbeat measurements. The combined objective is the mean of length reduction, heartbeat reduction and compatibility. Local measurements and organizer scores are reported separately.

## Start here

```bash
conda activate af
python -m pip install -e '.[dev]'
make check
make test
```

The package has no third-party runtime dependencies. Lean evaluation needs the pinned, prebuilt projects listed in the local environment map. The existing warm-up references are already prepared; search never remeasures them.

```bash
# Price scenarios from saved traces; no model or Lean calls.
proof-harness estimate --condition gpt-6.1-sol:max \
  --output results/harness/my_sol_run

# Audit one theorem first, then run all 15. Repeating reuses completed cells.
proof-harness run --condition gpt-6.1-sol:max --pilot --workers 10 \
  --output results/harness/my_sol_run

# Saved evidence only.
proof-harness report --output results/harness/my_sol_run
proof-harness audit --output results/harness/my_sol_run
```

Omit `--condition` to run both active models, or specify `gpt-6-astra:max` for the SOTA condition. Score search has no imposed total token, attempt or wall-time cap. Costs are reported per problem using recorded usage and explicit API-equivalent assumptions; the competition's $3 cap is not enforced by these comparison runs.

There is one active task policy: [refactor_system.md](prompts/refactor_system.md)
and its five-card [strategy bank](prompts/strategy_bank.json), preserving the
revised V2 contents used for the recent Sol runs. There is no prompt-version or
search-mode selector. All providers use score feedback and cleanup at the edges.

Native Lemex and Claude Code run the same task with their own shell/edit tools:

```bash
# DeepSeek: existing .env gateway key is passed only to the Lemex child.
proof-harness run --provider lemex --pilot --workers 5 \
  --output results/harness/my_deepseek_run

# Sign in with `claude auth login` first. Exact Opus 5.5/max, no fallback.
proof-harness run --provider claude --pilot --workers 5 \
  --output results/harness/my_opus_run
```

Lemex defaults to `deepseek-ai/DeepSeek-V4.1-Flash/high`. The direct RCP chat
client and its temperature/output-cap settings are retired. Native Lemex sends
no temperature override; the gateway's effective default is not exposed by the
CLI. Claude uses `claude-opus-5-5/max`, with normal project configuration and
authentication discovery. Each provider has separate output and usage evidence.
Claude's reported API-equivalent cost includes its actual cache durations and
any auxiliary models. Complete usage from failed calls is also retained. The
exact DeepSeek gateway price remains unknown.

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
    workers=10,
    pilot=True,
))
```

`proof-eval` also provides a JSON CLI and localhost HTTP API:

```bash
proof-eval evaluate putnam_1964_a4 --code-file candidate.lean
proof-eval serve --port 8765 --workers 2
```

The generic deterministic API accepts a new competition batch with explicit paths and prepared references. See [docs/DETERMINISTIC_BATCH.md](docs/DETERMINISTIC_BATCH.md). `proof-benchmark` processes references once; `proof-setup` builds the pinned source projects. These are explicit setup actions, separate from search.

## Data, rules and results

- [RULES.md](RULES.md): saved competition rules and pinned upstream links.
- [data/benchmark_data_warmup.jsonl](data/benchmark_data_warmup.jsonl): unmodified warm-up data; SHA-256 `6209680cf00cde0765b77b24834cd72c64dd585b2f7e3f2a58209980ab59a804`.
- [data/benchmark_heartbeats.jsonl](data/benchmark_heartbeats.jsonl): organizer heartbeat references, preserved separately from local ratios.
- [problems](problems/README.md): all 15 initial, deterministic and best proof examples with provenance.
- [results](results/README.md): experiment index, including [deterministic](results/deterministic/README.md) and [model harness studies](results/harness/README.md).
- [Sol configuration results and submission](results/harness/05_model_config/README.md): the pre-refactor Sol/max result was 87.342215% combined with 100% compatibility.
- [Refactor validation and fresh Sol replicate](results/harness/06_refactor_regression/COMPARISON.md): 86.575834% combined, 100% compatibility, 36/36 passing versions; the earlier stronger submission is preserved.
- [Native provider pilots](results/harness/07_native_agents/README.md): Opus completed one problem; DeepSeek retained an improved proof after a transport failure. Both cohorts are incomplete.
- [related_work](related_work/README.md): literature, papers and research proposals.
- [prompts](prompts): the one active revised task policy and strategy bank.

Historical study drivers and their dedicated tests were retired during the package cleanup. Their result evidence remains unchanged, and their original sources are saved in Git checkpoint `bfb2ade6` and content-addressed audit snapshots. Current experiments use the maintained APIs and commands above.
