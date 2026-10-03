# One-shot context ablation

The harness owns context extraction, generation, verification and score selection.
The model receives one system/user prompt and returns one complete declaration.
It has no tools, feedback turn or execution loop in this experiment. This same
contract can later serve frozen closed models or open models trained to edit
proofs; these runs do not train either model family.

The [system prompt](../prompts/one_shot_system.md) optimizes the competition's
combined score. The [18-card bank](../prompts/strategy_bank.json) contains conditional
transformations with source provenance and failure modes. Retrieval matches only
the current incumbent's source text and selects at most four cards; it does not
use model outcomes or retrieve benchmark winners. This initial selector uses
source triggers, not semantic goal retrieval or a trained retriever.

The [goal observer](PROOF_CONTEXT.md) runs once on each fixed incumbent. Goal-only
arms strip measured cost fields from that same extraction. The measured arm adds
only the allocations of the original tactic; it does not try candidate tactics or
embed replacement suggestions. Every arm also receives the same last 6,000
characters of source context preceding the target, which may start mid-definition
and is explicitly labeled read-only. The target's full incumbent is untruncated.

## Run

From the repository root in the `af` environment, with RCP configured in `.env`:

```bash
# Inspect preparation without requesting model generations.
python src/run_one_shot.py \
  --output results/one_shot/01_context_ablation --prepare-only

# Three retained pilot cells: first problem, plain arm, all three models.
python src/run_one_shot.py \
  --output results/one_shot/01_context_ablation --max-calls 3 --per-model 1

# Resume all remaining cells, one in-flight request per model.
python src/run_one_shot.py \
  --output results/one_shot/01_context_ablation --per-model 1
```

This API key allows **five requests total**, including overlapping generation
and repair workers. `--per-model` limits each runner independently; it does not
enforce that shared bound. The original experiment started with two generation
requests per model before the limit was clarified. The later Qwen3.8 cohort uses
the [shared admission wrapper and launch protocol](../results/one_shot/05_qwen38_extension/PROTOCOL.md),
which also reserves slots for the unfinished original repair workers. Use those
wrapped commands for the extension; do not launch additional unwrapped requests.

`--dataset`, `--input`, `--environments`, `--cache`, `--bank`, `--system`, `--models`,
`--arms` and repeated `--name` configure a new experiment. The defaults select
the complete warm-up dataset and its saved deterministic incumbents. Names select
the denominator for that experiment; partial results do not pretend to be a
full-benchmark score. Input proofs must still contain every dataset ID exactly once.

The frozen generation policy uses temperature 0.3, thinking enabled and high
reasoning requested, a 32,768-token output cap, and a 1,800-second socket timeout.
These generation tokens include reasoning as counted by the provider. The timeout
is not an exact total wall-time limit. Request concurrency can change across
resume; prompt, dataset, environment, reference values, source hashes and generation
policy must not. Interrupted requests have durable started markers and are never
automatically resampled. A saved response can still be evaluated after interruption.

The runner uses the existing `proof_eval.rcp.RCPClient`; it does not alter or log
credentials. It preserves exact final response content, provider token usage,
finish reason, model identity, response ID and elapsed request time. It records
the length of returned reasoning text, not that text itself. There is no use of
reasoning as fallback proof code.

## Evaluation and reporting

Only a raw full declaration or a single fenced Lean block is accepted. Extraction
removes outer whitespace/fences only. Truncated generations, multiple blocks,
surrounding prose and prohibited query tactics fail the output contract. The
ordinary evaluator then checks exact statements, valid declarations, the kernel
trust boundary, every required version and the three competition metrics.

Each cell stores `request.json`, `request_started.json`, `generation.json` and
`result.json`. The result keeps the raw candidate evaluation and the independently
selected incumbent/candidate. Generated candidates are never fed to another cell.
`summary.json` and `conditions/` update as results arrive. A finished run means all
planned cells have terminal records, not that every provider returned a proof.

Use [report_one_shot.py](../src/report_one_shot.py) to build the readable comparisons.
The [evidence auditor](../src/audit_one_shot.py) checks this warm-up experiment's
frozen inputs, requests, references and saved score decisions without running Lean.
The [failure analyzer](../src/analyze_one_shot_failures.py) keeps evaluator statuses
separate from heuristic diagnostic categories and reports provider token counts,
including reasoning exhaustion and unchanged returned incumbents.

```bash
python src/report_one_shot.py --input results/one_shot/01_context_ablation
python src/analyze_one_shot_failures.py --input results/one_shot/01_context_ablation
python src/audit_one_shot.py --input results/one_shot/01_context_ablation --complete
```

Reports support partial snapshots. Omit `--complete` for an audit while generation
is still running. The auditor currently uses the repository's warm-up paths and
local environment configuration; it does not provision them on another machine.

Interpret differences as an initial development experiment: one stochastic draw
per cell and fifteen warm-up problems cannot establish a generally superior
model or prompt. Extra context also costs input tokens; compare prompt/completion
usage and latency alongside quality. Costs from context preparation are separate
from generation and final verification.

The reference measurements and scoring backend are unchanged. Run offline tests
without the RCP client's pre-existing live smoke class:

```bash
python -m pytest -q -k 'not TestRCPLiveIntegration'
```

That exclusion prevents unrelated generation requests from contaminating the
experiment's call accounting.
