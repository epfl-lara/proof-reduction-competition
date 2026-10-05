# Model configuration and cost comparison

Compare **GPT-6.1 Sol/max** and **GPT-6 Astra/high**, 15 warm-up problems each,
using the revised score-feedback harness with deterministic cleanup at the
beginning and end. The first problem runs for both models before the controller
expands to all 30 cells. It checks tool use, final cleanup, complete usage, and
the saved-evidence audit; pilot cells are reused without resampling.

The prompts, strategy cards, source/goal/check tools, cached original reference
measurements, version checks, and selection margin match stage 03. Reuse the
better all-version-valid original/D0 proof as the initial deterministic step;
do not measure the reference or rebuild D0. Apply the same ten-method portfolio
once after model search. Keep the best proof passing every version with a gain
above 0.05 percentage points. No deterministic tool is exposed during search.

In-loop cleanup is retired from the runner, transport, tool dispatcher and
workspace client. Its completed stage-04 evidence and implementation snapshots
remain available for audits. Refactoring is paused until model selection.

Compare new complete conditions with stage-03 Astra/max (88.043179%), Astra/low
(79.118309%) and Luna/max (68.264239%). The score-only Astra/max reference is
88.384406%. There are no same-model historical controls for the new conditions;
those fields stay null. Independent generations are not budget-matched or
held-out evidence. Full means require all 15 cells to complete.

## Cost estimation before measurements

The Python API is [`proof_eval.costs`](../../../src/proof_eval/costs.py).
Run the existing runner in estimate-only mode; this reads saved usage and makes
no model calls or Lean measurements:

```bash
conda activate af
python src/run_agent_harness.py --estimate-only
```

It writes [cost_estimate.json](cost_estimate.json) before preparing the experiment.
Each of the three complete stage-03 conditions supplies a separate usage
scenario repriced for each target model. These are scenarios, not predicted
target token counts or reasoning-effort multipliers. The snapshot pins the
source result hashes and the rate card checked on 2026-10-04.

```python
from proof_eval.costs import CostConfig, estimate_codex_cost, estimate_configuration

config = CostConfig("gpt-6.1-sol", "max")
cost = estimate_codex_cost(config, generation["codex_usage"])
projection = estimate_configuration(config, saved_results_for_one_condition)
```

`estimate_codex_cost` accepts Codex counters `input_tokens`,
`cached_input_tokens`, `cache_write_input_tokens`, `output_tokens`, and
`reasoning_output_tokens`. Ordinary input is input minus reads and writes.
Reasoning is already included in output and is not charged twice. Missing or
inconsistent usage cannot be priced as zero. `generations_cost` adds all attempts,
including discarded proposals, and marks the total unknown if any usage is missing.

| Model | Input / 1M | Cached reads / 1M | Cache writes / 1M | Output / 1M |
| --- | ---: | ---: | ---: | ---: |
| GPT-6.1 Sol | $2 | $0.10 | $2.50 | $10 |
| GPT-6 Astra | $10 | $1 | $12.50 | $50 |
| GPT-6 Luna | $0.10 | $0.01 | $0.125 | $0.50 |

Sources: [Sol 6.1](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[Astra](https://developers.openai.com/api/docs/models/gpt-6-astra),
[Luna](https://developers.openai.com/api/docs/models/gpt-6-luna).

The default estimate assumes Standard service, short context for each underlying
request, and no regional premium. Fast is 2x; Flex/Batch are 0.5x in the estimator,
not newly enabled execution backends. Requests above 272K input tokens apply 2x
input/cache and 1.5x output. Use `scope="request"` to infer that band for one
request; aggregated CLI totals must not trigger the surcharge merely because
many short requests sum above 272K. API output includes cache-write and
all-long-context sensitivity estimates. Regional processing is an explicit
optional 10% multiplier.

The experiments retain existing Codex login and CLI execution settings. These
are **public API-equivalent estimates, not Codex invoices**. Aggregate CLI usage
does not certify the underlying request tiers or context lengths, and a future
API replay may have different cache writes/hits. Actual subscription billing,
supervising-agent tokens, and local Lean CPU cost are outside this estimate.
No paid hosted tools are enabled in these proof-search calls.

The competition cap is **$3 per problem**, including all retries and discarded
candidates. Report total, mean, p90, maximum and names exceeding $3, plus unknown
usage counts. A cheap mean is insufficient. This study keeps the existing
unrestricted score-search stopping rule for comparability; it measures cost,
not hard-enforced compliance. A competition budget controller is a subsequent
step after selecting the model configuration.

Initial scenarios: repricing Astra/max's completed traces at Sol 6.1 rates yields
$0.729594/problem, maximum $1.069493. Repricing Luna/max's longer traces at Sol
rates yields $1.316902/problem, maximum $3.384100 (one over $3). Astra/high has no
measured usage yet: Astra/low and Astra/max traces provide separate scenarios
of $0.929707 and $5.151091/problem, not bounds or an interpolation forecast.

## Run and inspect

```bash
python src/continue_agent_harness.py --suite models --workers 10
python src/summarize_agent_harness.py --watch --suite models
python src/audit_agent_harness.py results/harness/05_model_config
```

The runner now defaults to `score_edges` and this output cohort. Override
conditions with repeated `--condition MODEL:EFFORT` and use a new `--output`
directory when changing a frozen study. The controller defaults to the models
suite, runs the two-model pilot, audits it, then runs the remaining cells with
up to ten concurrent Codex processes. Reports refresh every 30 seconds; costs
use terminal usage only. Partial conditions have no full score mean. The report
exports submission JSONL once each 15-problem condition is complete.

Started model requests are never silently resampled. Interrupted requests retain
their evidence and stay incomplete until diagnosed. Runtime code, CLI identity,
prompts, cached references and pricing assumptions are pinned before launch.
