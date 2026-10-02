# Model-free warm-up experiments

Each numbered main-stage directory adds one optimization to the previous stage;
separate branches explicitly identify their input. Preserve
the original benchmark, all rejected attempts, the selected full declarations,
and the exact configuration. A shorter proof alone is not a successful result.

| Stage | Question | Evidence |
| --- | --- | --- |
| [00_reference_baseline](00_reference_baseline/) | Can we reproduce every original in the pinned environments? | Reference lengths, locally cached heartbeats, version coverage and environment fingerprints. |
| [01_linter_deletion](01_linter_deletion/) | What do Lean's unused/unreachable-tactic linters buy us? | Repeated deletion proposals, full declaration checks, selected proofs and scores. |
| [02_explicit_simp](02_explicit_simp/) | Does an explicit simplifier lemma set improve the arena score? | `simp?` suggestions materialized as ordinary tactics, compared with stage 01. |
| [03_wrappers](03_wrappers/) | Can local return wrappers be contracted? | Parsed edits, accepted transitions, and all-version scores. |
| [04_local_facts](04_local_facts/) | Which local facts can be deleted? | Compiler-tested deletions, including rejected proposals. |
| [05_fact_reuse](05_fact_reuse/) | Can earlier local facts replace repeated work? | Type/RHS matching and alias contraction proposals. |
| [06_tactic_menu](06_tactic_menu/) | Which fixed solver replacements improve the combined score? | Nineteen tactics tried in restored goal states, followed by full candidate checks. |
| [07_library_search](07_library_search/) | Do materialized library-search suggestions add further gains? | Explicit `exact?`/`aesop?`/`grind?` suggestions checked as standalone candidates. |
| [08_simp_minimization](08_simp_minimization/) | Which explicit simplifier lemmas can be removed? | Compiler-tested chunk and individual argument deletions. |
| [09_arithmetic_minimization](09_arithmetic_minimization/) | Can arithmetic solvers use fewer explicit hints? | `linarith` / `nlinarith` hint minimization with tactic controls preserved. |
| [10_rewrite_minimization](10_rewrite_minimization/) | Which rewrite steps are redundant? | Ordered `rw` / `rewrite` argument minimization. |
| [11_repeated_sweeps](11_repeated_sweeps/) | Do later changes unlock earlier methods? | Separate folders for every method in each bounded sweep. |
| [12_early_arithmetic_probe](12_early_arithmetic_probe/NOTES.md) — separate branch | Was cheap arithmetic-hint removal available earlier? | One candidate adds +0.467 pp from stage 03; excluded from cumulative main gains. |

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
| Wrapper contraction | 0.148% | 13.395% | 100% | 37.847% | +0.748 pp |
| Local-fact deletion | 3.594% | 15.140% | 100% | 39.578% | +1.731 pp |
| Local-fact reuse | 4.154% | 15.399% | 100% | **39.851%** | +0.273 pp |
| Fixed solver menu | 9.421% | 19.258% | 100% | **42.893%** | +3.042 pp |
| Materialized library search | 9.402% | 21.860% | 100% | **43.754%** | +0.861 pp |
| Simplifier-list minimization | 10.069% | 22.382% | 100% | 44.150% | +0.396 pp |
| Arithmetic-hint minimization | 10.171% | 23.676% | 100% | 44.616% | +0.465 pp |
| Rewrite-list minimization | 10.243% | 23.892% | 100% | **44.712%** | +0.096 pp |
| First repeated sweep (all ten methods) | 12.079% | 26.257% | 100% | **46.112%** | +1.400 pp |
| Second repeated sweep (all ten methods) | 12.187% | 26.557% | 100% | **46.248%** | +0.136 pp |

All ten methods and two repeated sweeps are complete on **15 problems**, with
**36/36 version checks passing** for every stage's selected proofs. The final
score gains **12.919 pp** over the measured original control and **9.148 pp** over
the previous stage-02 baseline. These are local measurements against unchanged
cached references. Choosing only the shortest candidates would miss substantial
heartbeat-driven gains.

Read [FINDINGS.md](FINDINGS.md) for concrete examples, costs, source-level results,
and the next isolated experiment. The main artifacts are:

- [Selected full declarations](selected_candidates.jsonl) and their
  [provenance and scores](selected_candidates_manifest.json).
- [Complete comparison JSON](deterministic_comparison.json),
  [stage-comparison CSV](deterministic_comparison.csv), and
  [score-progress plot](score_progress.svg).
- [Final audit](validation/final_audit.json) of all 30 main stages, including
  proof hashes, score arithmetic, accepted edits, implementation hashes, and the
  36 unchanged cached references; [validation details](validation/README.md).
- [Portfolio manifest](portfolio.json), [methods and limits](METHODS.md), and
  the original [first-two-stage comparison](comparison.json).

The run stopped at its declared **two-sweep cap**, with a positive second-sweep
gain. Some discovery sites and candidate alternatives remain unexplored. This
is a completed bounded experiment, not a global optimum or an exhaustive search.
The separate [early arithmetic probe](12_early_arithmetic_probe/NOTES.md) is
excluded from the cumulative main score.

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
  --output results/reproduction/00_reference_baseline/reference_values.jsonl

python src/run_deterministic.py --method lint \
  --output results/reproduction/01_linter_deletion
python src/run_deterministic.py --method simp \
  --input results/reproduction/01_linter_deletion/candidates.jsonl \
  --output results/reproduction/02_explicit_simp

# Continue the eight new methods, then two bounded sweeps of all ten methods.
python src/run_portfolio.py \
  --input results/reproduction/02_explicit_simp/candidates.jsonl \
  --output-root results/reproduction --workers 8 --max-sweeps 2

# Run one method separately, using the same reference cache and acceptance rule.
python src/run_experiments.py --method arith_min \
  --input results/08_simp_minimization/candidates.jsonl \
  --output results/reproduction/arithmetic_only --workers 8
```

The portfolio uses the reference export under its input root to audit completed
stages. On this machine, the processing command reuses the existing cached
measurements. A fresh machine prepares its missing local references once; keep
that export in the separate reproduction root. The committed experiment evidence
is preserved. The local environment map and cache must match the measurements:
the portable reference export alone does not replace installed Lean projects or
the evaluator cache.

Use a **new output directory** when changing code, budgets, environment configuration,
or input proofs. An existing directory resumes completed problems only when its
configuration matches. Intermediate compiler checks also reuse the evaluator cache.
The original `run_deterministic.py` runner's `--name` supports a pilot while
retaining unchanged fallback proofs for the other rows. Completed records have
per-problem timing, stop reason and scores. A trial
or round limit is a budget stop, not a claim of reaching a fixed point.

The original reports in `comparison.json` / `comparison.csv` remain unchanged.
The extended comparison uses `deterministic_comparison.json` /
`deterministic_comparison.csv`. Generate its plot with
`python src/plot_experiments.py`. Independently audit saved proof hashes, scores,
version coverage, accepted edits, and unchanged cached references with
`python src/audit_experiments.py --stages STAGE_DIR... --check-code --check-cache`.
The audit reads evidence and cache records; it does not rerun Lean or remeasure
references. Historical discovery source is preserved in hash-addressed
[implementation snapshots](validation/implementation_snapshots/).

Every stage contains `config.json`, `summary.json`, `candidates.jsonl`, per-problem
records and JSONL trial logs. Trials contain the exact proposed declaration and
compiler outcomes, including failures. These are search-policy-dependent records,
not yet a balanced SFT/GRPO dataset. No models, paid APIs, training runs or arena
submissions are involved.
