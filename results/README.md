# Model-free warm-up experiments

Each numbered directory adds one optimization to the previous stage. Preserve
the original benchmark, all rejected attempts, the selected full declarations,
and the exact configuration. A shorter proof alone is not a successful result.

| Stage | Question | Evidence |
| --- | --- | --- |
| [00_reference_baseline](00_reference_baseline/) | Can we reproduce every original in the pinned environments? | Reference lengths, locally cached heartbeats, version coverage and environment fingerprints. |
| [01_linter_deletion](01_linter_deletion/) | What do Lean's unused/unreachable-tactic linters buy us? | Repeated deletion proposals, full declaration checks, selected proofs and scores. |
| [02_explicit_simp](02_explicit_simp/) | Does an explicit simplifier lemma set improve the arena score? | `simp?` suggestions materialized as ordinary tactics, compared with stage 01. |

The experiment reports distinguish **measured results** from the **next experiment**.
See [METHODS.md](METHODS.md) for the research basis and decision order. Directories
are stages, not separate model tracks: both tracks can use the same deterministic
preprocessor and evaluator.

## Measured outcome

| Stage | Mean token reduction | Mean heartbeat reduction | Compatibility | Combined | Gain from previous stage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Unchanged control | 0.000% | -0.011% | 100% | 33.330% | — |
| Linter deletion | 0.978% | -0.006% | 100% | 33.658% | +0.328 pp |
| Explicit simplifier lemmas | -1.716% | 13.015% | 100% | **37.100%** | **+3.442 pp** |

All **15 problems and 36 version checks** are included. Total gain: **3.770 pp**.
See [comparison.csv](comparison.csv) for every problem and [comparison.json](comparison.json)
for full-precision stage/source aggregates. These are local measurements. The
selected proofs have lower elaboration cost and slightly greater average token
length; choosing only the shortest candidates would miss that gain.

Next: independently test unused local facts and `have ...; exact ...` contraction
on stage 02, with the same denominators and acceptance rule. This next stage is
specified in its report and has not yet been run.

## Objective and acceptance

For a problem, use the supplied reference token count `L0` and the cached local
primary-version heartbeat count `H0`:

```
L = 100 * (1 - candidate_tokens / L0)
H = 100 * (1 - candidate_heartbeats / H0)
C = 100 * passing_listed_versions / listed_versions
S = (L + H + C) / 3
```

The unchanged, fully compatible reference starts near **33.333%**, because its
compatibility component is already 100%. Report changes in percentage points
relative to that control and relative to the preceding stage. Average *per-problem
percentages*, not ratios of summed tokens or heartbeats. Full-benchmark means use
all 15 rows. If required evaluations are missing, the full mean is `null`; a
measured-subset mean has an explicit denominator.

An edit must compile on the primary version and increase the fully checked `S`
by more than **0.05 percentage points**. This declared margin discourages selection
on tiny heartbeat fluctuations; it is not an arena rule or a statistical confidence
interval. A primary check with `(L + H + 100) / 3` too low cannot beat the incumbent,
so we skip its remaining versions. The bound is never reported as a final score.
Longer proofs and compatibility tradeoffs are judged by the same objective.

## Reproduce

From the repository root, in the Python environment where this package is installed:

```bash
# Explicit downloads/builds; isolated projects, exact benchmark commits.
python src/setup_benchmark.py --workers 1

# Reuses matching reference measurements. It does not refresh them by default.
python src/process_benchmark.py \
  --output results/00_reference_baseline/reference_values.jsonl

python src/run_deterministic.py --method lint \
  --output results/reproduction/01_linter_deletion
python src/run_deterministic.py --method simp \
  --input results/reproduction/01_linter_deletion/candidates.jsonl \
  --output results/reproduction/02_explicit_simp
```

Use a **new output directory** when changing code, budgets, environment configuration,
or input proofs. An existing directory resumes completed problems only when its
configuration matches. Intermediate compiler checks also reuse the evaluator cache.
`--name` supports a pilot while retaining unchanged fallback proofs for the other
rows. Completed records have per-problem timing, stop reason and scores. A trial
or round limit is a budget stop, not a claim of reaching a fixed point.

Every stage contains `config.json`, `summary.json`, `candidates.jsonl`, per-problem
records and JSONL trial logs. Trials contain the exact proposed declaration and
compiler outcomes, including failures. These are search-policy-dependent records,
not yet a balanced SFT/GRPO dataset. No models, paid APIs, training runs or arena
submissions are involved.
