# Proof Reduction Competition

Workspace for participating in [Lean Refactor Arena](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena), part of the AI for Verifiable Coding workshop at NeurIPS 2026.

The task is to refactor existing Lean 4 proofs while preserving their statements, improving proof length, elaboration cost, and compatibility across the listed toolchains. Closed-source and open-source LLM entries compete in separate tracks.

## Repository contents

- [RULES.md](RULES.md): competition rules and submission requirements, checked on October 2, 2026, with pinned source links.
- [data/benchmark_data_warmup.jsonl](data/benchmark_data_warmup.jsonl): the original, unmodified warm-up benchmark.
- [data/benchmark_heartbeats.jsonl](data/benchmark_heartbeats.jsonl): the organizer's published reference heartbeat counts, preserved separately from local measurements.
- [src/proof_eval](src/proof_eval): Python, CLI, and localhost HTTP evaluation API, including training reward adapters.
- [related_work](related_work/README.md): verified literature, downloadable papers, model feasibility, and the proposed harness/SFT/GRPO plan for both tracks.
- [results](results/README.md): staged, model-free warm-up experiments, exact candidates, rejected attempts, and measured score changes.
- [.gitignore](.gitignore): Python environments, caches, build artifacts, Lean/Lake build outputs, and local credentials.

Each benchmark row specifies its own evaluation versions. The evaluator uses explicitly configured, prebuilt Lean projects at those exact revisions; there is no single repository-wide Lean toolchain. Its Python package has no external runtime dependencies and invokes Lean through Lake.

## Initial benchmark

The warm-up dataset contains **15 declarations**, with three each from Strata, PhysLib, CSLib, ArkLib, and PutnamBench. It totals 17,595 reference proof tokens as reported by the dataset. LeanPool is listed among the competition's sources but has no rows in this warm-up file.

The local file was verified byte-for-byte against the organizer's dataset at Space revision `d9e46ee13c822925fb3031b0a0eac53b51631198`:

- [Pinned upstream dataset](https://huggingface.co/spaces/delta-lab-ai/lean-refactor-arena/blob/d9e46ee13c822925fb3031b0a0eac53b51631198/benchmark_data_warmup.jsonl)
- Size: 113,826 bytes.
- SHA-256: `6209680cf00cde0765b77b24834cd72c64dd585b2f7e3f2a58209980ab59a804`.

Each JSONL row includes:

| Field | Meaning |
| --- | --- |
| `name` | Unique benchmark ID to use in a submission. |
| `source` | Source corpus. |
| `statement` | Fixed declaration statement, without `:=` and the proof body. |
| `src` | Original complete declaration, including its proof. |
| `proof_length`, `num_lines` | Reference proof token count and declaration line count. |
| `header` | Imports and options for standalone rows; empty for project-resident rows. |
| `file_path`, `url` | Source file and repository for project-resident rows. |
| `start_line`, `end_line` | Declaration location, when present. |
| `version_info` | Evaluation toolchain labels paired with pinned repository commits. |

For project-resident declarations, evaluation takes place inside the source repository at the specified revisions. For PutnamBench, the row supplies a standalone header and `version_info` identifies Mathlib release revisions. The benchmark file does not include reference heartbeat counts; the organizer stores those separately.

## Participation

1. Read [RULES.md](RULES.md) and choose a track.
2. Use the exact statement from each row and replace only its proof body. Validate in the row's repository context and listed versions.
3. Produce a UTF-8 JSONL file with a `name` and a `proof` string per submitted declaration. `proof` must contain the complete declaration, not just the tactics.
4. Upload proofs in the arena's Submit tab. Keep the submission key issued on the first successful upload outside Git.
5. For the full benchmark, submit the reproduction code archive in the arena and the technical report on OpenReview by the deadline.

The full benchmark is scheduled for **November 1, 2026**, and proofs, code, and reports are due **November 8, 2026**. See the saved rules and live competition page for updates.

## Local evaluation API

Install in the intended Python environment, from this repository:

```bash
conda activate af
python -m pip install -e .
proof-eval environments
```

Copy [environments.example.json](environments.example.json) to `environments.local.json` and set the paths of prebuilt projects. Each entry identifies a source corpus and version. Project-resident rows require the source repository at the row's exact commit; PutnamBench entries require a project with Mathlib pinned to the row's commit. The evaluator checks toolchains, repository revisions, and dependency manifests and refuses unavailable or changed environments. It never downloads dependencies or changes repository revisions during an evaluation.

The warm-up set has 15 distinct source/version environments and 36 theorem/version checks. One configured version is sufficient for local proof search; all of a theorem's listed versions must be checked to report its compatibility and combined score. `proof-eval environments` lists the required commits and configured paths. Unconfigured environments remain explicitly unavailable.

To provision the warm-up environments explicitly, run `python src/setup_benchmark.py`.
It downloads the pinned toolchains and repositories, obtains Mathlib build caches,
builds the required source modules, and registers successful builds in the local
configuration. `--source strata` or `--version v4.26.0` limits setup. Projects and
logs live under `.proof-eval-projects/`; this can require substantial disk space.
Evaluation itself continues to use only configured projects.

For deterministic optimization, use [src/run_deterministic.py](src/run_deterministic.py).
The [experiment guide](results/README.md) gives the stage order, commands, objective,
budgets, and artifact format. It retains the original proof unless a fully checked
candidate improves the competition's combined score.

### Python and reward functions

```python
from pathlib import Path
from proof_eval import Evaluator

evaluator = Evaluator()  # paths default to this repository's data and local config
name = "putnam_1964_a4"

# Setup step: measure the original proof once. Repeated calls reuse the cache.
evaluator.prepare_reference(name, versions="primary")

# Agent loop: evaluate a full declaration, without re-measuring the reference.
code = Path("candidate.lean").read_text()
result = evaluator.evaluate(name, code, versions="primary")
print(result["scores"])
print(result["per_version"])

# A reward function for a search or training loop; percentage scaled by 1/100.
reward = evaluator.reward(name, code, metric="heartbeat", versions="primary")

# When every listed environment is ready:
# evaluator.prepare_reference(name)  # all listed versions, cached independently
# result = evaluator.evaluate(name, code)
# reward = evaluator.reward(name, code)  # combined score / 100
```

`input_kind="body"` accepts a proof body such as `by ...` and attaches the exact benchmark statement. The default `"declaration"` accepts the complete declaration and requires the exact statement. Statements can contain `:=` themselves, so proof extraction uses the dataset's statement boundary.

`versions="primary"` selects the first version in that row's `version_info`; `"all"` is the default, and a list of listed version labels is also accepted. The first version is our explicit local primary for length/heartbeat scoring; it is not a claim about the private arena worker's default. Select a set containing the primary version to obtain top-level length/heartbeat rewards.

`reward_batch(names, codes, **kwargs)` supplies the same interface to a trainer. A GRPO reward function can extract completion code, retain the benchmark ID for each completion, and pass those lists to this method. Arguments such as `metric="length"` or `metric="heartbeat"` with `versions="primary"` support cheaper feedback during search. Compatibility and combined rewards require all listed versions.

Invalid proofs receive `0.0` by default. Negative reductions are preserved, and rewards are not clipped; callers can set `invalid_reward` explicitly when choosing a training reward policy. Missing environments, missing baselines, and incomplete version coverage raise `EvaluationNotReady` for the requested reward rather than being mislabeled as poor model outputs. A candidate timeout counts as failure under the configured, fingerprinted timeout policy; timeouts are not cached.

### Process the benchmark reference values

[src/process_benchmark.py](src/process_benchmark.py) processes the initial dataset and exports one JSONL row per problem:

```bash
python src/process_benchmark.py --output .proof-eval/benchmark_values.jsonl

# A smaller first run, using the problem's primary version:
python src/process_benchmark.py --name putnam_1964_a4 --versions primary \
  --output .proof-eval/putnam_1964_a4_values.jsonl
```

The export includes the supplied reference token count, published heartbeat count, exact version commits, cached local heartbeat measurements, and measurement provenance. It retains problems with unavailable environments and records their status and diagnostics; absent measurements are `null`. It checkpoints the output atomically as problems finish. Re-running the script reuses the same baseline cache as the API, so an interrupted run does not lose completed measurements. Only an explicit `--refresh` requests re-measurement.

The default processes every problem and every listed version. `--name` may be repeated; `--versions primary` is useful for preparing fast local rewards. Exit code 0 means every requested local measurement is ready; exit code 2 means the JSONL was produced but contains unavailable or failed measurements. Dataset token counts and the published heartbeat file are preserved unchanged.

### CLI and HTTP

```bash
# Explicit setup, then repeated candidate checks:
proof-eval prepare putnam_1964_a4 --versions primary
proof-eval reference putnam_1964_a4 --versions primary
proof-eval evaluate putnam_1964_a4 --versions primary --code-file candidate.lean
proof-eval reward putnam_1964_a4 --versions primary --metric heartbeat --code-file candidate.lean

# JSON over localhost for an agent running in another process:
proof-eval serve --port 8765 --workers 2
```

Global options (`--dataset`, `--heartbeats`, `--environments`, `--cache`, `--timeout`) go before the subcommand. Code can also arrive on stdin; use `--body` for body-only input. CLI results are JSON. A completed evaluation of an invalid proof is a normal result with `status="invalid"`, not a CLI transport error.

The HTTP service binds to `127.0.0.1`. `POST /evaluate` accepts a JSON object with `name`, `code`, optional `input_kind`, and optional `versions`; its result is identical to `Evaluator.evaluate`. `POST /reward` additionally accepts `metric` and `invalid_reward`, returning `{"reward": ...}`. `GET /reference?name=...&versions=primary`, `GET /environments`, and `GET /health` are available. Baseline preparation remains an explicit Python/CLI setup operation. An unavailable reward returns HTTP 409; a busy service returns 429.

For example, from another Python process:

```python
import json
from pathlib import Path
from urllib.request import Request, urlopen

payload = {
    "name": "putnam_1964_a4",
    "code": Path("candidate.lean").read_text(),
    "versions": "primary",
}
request = Request(
    "http://127.0.0.1:8765/evaluate",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
with urlopen(request, timeout=180) as response:
    result = json.load(response)
```

### Measurements and reproducibility

The API reports `length_reduction_pct`, `heartbeat_reduction_pct`, `compatibility_pct`, and `combined_pct`. Each reduction is `100 * (1 - candidate / reference)`. Compatibility is the fraction of all listed versions that pass, and the combined score averages the three percentages. Failed primary proofs score zero. A partial or unavailable check leaves unsupported scores as JSON `null`, with diagnostics. Local scores retain full precision for learning; the arena rounds its displayed values.

- **Length:** use the dataset's stored `proof_length` as the reference. Candidate tokenization follows the organizers' [public lexer](https://github.com/delta-lab-ai/lean-refactor/blob/9c98a3a097e53724e35b2a2e7fe316c331efa20a/lean_refactor/cc_agent/scripts/proof_utils.py); all 15 reference counts are covered by regression tests. Comments use a nested, literal-aware scanner.
- **Heartbeats:** compile the reference once locally, then compare candidates with that cached local value. The evaluator measures a synchronous declaration elaboration using `IO.getNumHeartbeats`, with `Elab.async=false` and `maxHeartbeats=0` inside its wrapper. Imports and setup precede the measurement. Raw counts are retained; `heartbeats` is raw allocations divided by 1,000. An external timeout bounds the entire Lean process. Both reference and candidate use this identical wrapper, even for projects without Mathlib.
- **Correctness:** Lean must consume exactly one candidate declaration, introduce the expected theorem, and finish without errors. The theorem must not depend transitively on `sorryAx`. The original theorem is replaced in its source context, preventing self-reference to an already imported solution. A conservative local filter also rejects command injection and metric-changing options; its rejection reason is returned.
- **Cache:** `.proof-eval/` stores local baselines and candidate results, keyed by the benchmark row, pinned environment, measurement implementation, host/architecture, and timeout. Per-key locks and atomic writes allow multiple local processes to reuse it. Changed inputs invalidate reuse. Only explicit `prepare_reference(..., refresh=True)` or `prepare --refresh` re-measures a cached reference. Build artifacts are trusted prebuilt inputs; the evaluator verifies source pins, not how every existing `.olean` was produced.

Heartbeats count allocation work, so they are more stable across hardware than elapsed time, but compiler versions, context, settings, and small runtime differences still matter. Local reference/candidate ratios provide the harness feedback; these are not asserted to reproduce the arena worker's exact counts. Published values are returned as `published_heartbeats` for provenance and never mixed into local heartbeat rewards. See [Lean's heartbeat documentation](https://lean-lang.org/doc/reference/latest/IO/Timing/).

The published heartbeat file is pinned to the same Space revision as the benchmark. Its SHA-256 is `f342873a128281f858b9514ca4f3079dac8703515ff8a5510d5edffeecc0b6cb`.

### Validation

```bash
python -m unittest discover -s tests -v
```

The tests cover tokenizer agreement, unchanged statements, malformed and forbidden code, baseline and candidate cache reuse, environment invalidation, incomplete compatibility, reward semantics, HTTP transport, and isolated Lean compilation. Lean integration tests require the toolchain indicated in the test fixture; otherwise they skip explicitly.
