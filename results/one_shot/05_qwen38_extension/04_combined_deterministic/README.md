# Deterministic cleanup after model proposals

**incomplete**: 47/75 cells have complete cleanup; 15/15 deterministic controls are complete. The archived deterministic incumbent score is **46.248122%**.

D0 is the archived deterministic incumbent. D1 applies the new bounded cleanup to D0. F is the first all-version-valid model proposal after correctness repair, even when its score was rejected. L is stage 03's incumbent-selected result. H selects the highest-scoring eligible proof from the control, the preserved earlier selection, and the cleaned proposal. D0 remains the fallback; exact ties prefer D1. Eligibility for new improvements is measured against D0 with the 0.05-point margin, not a second sequential margin against L.

All selected transitions must pass every required version. No deterministic results or scores are sent to the model, and this stage makes no new model calls. Each unique cleanup uses one ordered pass of ten methods, with three rounds, 32 trials, and six discovery sites per method; it does not search to a fixed point.

## Complete-condition score comparison

All means remain blank until every theorem in that condition and every control is complete. H − D1 is the value of the model branch beyond the extra deterministic control. H − L is the additional gain from cleanup and control fallback. Identical per-job budgets do not make these equal-total-compute comparisons.

| Model | Arm | Complete / expected | D1 | L | H | H − D1 pp | H − L pp | Above D1 | Rejected F rescued above D1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3.8-27B | plain | 10/15 | — | — | — | — | — | 0 | 0 |
| Qwen3.8-27B | cards | 10/15 | — | — | — | — | — | 0 | 0 |
| Qwen3.8-27B | goals | 9/15 | — | — | — | — | — | 0 | 0 |
| Qwen3.8-27B | cards_goals | 9/15 | — | — | — | — | — | 0 | 0 |
| Qwen3.8-27B | cards_goals_costs | 9/15 | — | — | — | — | — | 0 | 0 |

Counts concern completed cleanup rows; they can be partial while means remain blank. A score-rejected F cleaned above D0 is recorded separately from one that actually beats D1. Returning the unchanged incumbent is not a model rescue. Per-axis scores and selected version checks are in the JSON.

## Unique work versus reused branches

There are 15 logical control cleanups. Recorded cells reuse those results 47 times; those uses are not extra compiler jobs. Recorded model branches reference cleanup jobs 0 times. The combined references cover 15 unique jobs, with 0 shared references beyond those distinct jobs.

Registered physical jobs: 15; terminal jobs: 15; complete: 15; incomplete discovery: 0. The job registry includes 0 proposal origins, including pending cells. The following counters sum each terminal physical job once. Work in unfinished jobs is not estimated; cache hits within a physical job are distinct from reusing that entire job.

| Recorded physical-work counter | Total |
| --- | ---: |
| `accepted_transitions` | 0 |
| `analysis_requests` | 305 |
| `attempts` | 961 |
| `cache_hits` | 683 |
| `elapsed_seconds` | 2132.508 |
| `lean_candidate_checks` | 277 |

Optimizer counters exclude the job's initial and final whole-proof validation calls, which can hit the evaluator cache. The job records preserve that accounting; no extra compiler-process count is inferred. Saved durations can overlap and are not end-to-end wall time. Earlier initial and repair requests share model services and may encounter queue blocking; this experiment does not support model latency rankings.

## Evidence and exports

[per_problem.csv](per_problem.csv) preserves D0, D1, L, F, cleaned F, H, branch identities, and rescue flags. [source_results.csv](source_results.csv) shows source-level gains after full conditions complete. [pairwise.csv](pairwise.csv) records paired context contrasts; the JSON includes the same 2×2 card/goal effects and interaction as earlier stages, with cost context isolated by `cards_goals_costs − cards_goals`. These are descriptive one-draw comparisons, not significance tests. [report.json](report.json) also records all completion denominators, physical-work accounting, registered job origins, and input/result hashes.

Only complete conditions receive separate submission JSONL files and manifests. No pooled best-of-arms selection is made.

## Limits

- This exploratory extension was chosen after partial model results were observed; it is not an independent preregistered confirmation.
- H minus D1 compares the added model branch against the extra deterministic control; H minus L includes cleanup and control fallback.
- Control plus proposal cleanup can perform more total computation than the control alone; identical per-job budgets do not equalize total compute.
- No new model calls occur in this stage. Earlier model calls overlap with correctness repairs and can encounter queue blocking; no latency ranking is justified.
- One stochastic optimization proposal per cell and fifteen development problems do not establish a universally best model or context.
- Deterministic search is bounded, not exhaustive; incomplete discovery is not proof that no improvement exists.
- Full condition means and exports require all configured theorems and all controls to complete. No cross-model or cross-arm pooling is performed.
- The reporter reads recorded Lean checks and cached-reference scores without new compilation or reference measurement.

Rebuild the report from saved evidence:

```bash
python src/report_combined_matrix.py --input results/one_shot/04_combined_deterministic
```
