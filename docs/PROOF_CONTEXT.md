# Proof-state and tactic-cost context

The first model experiment observes the **exact supplied incumbent** before requesting one complete proof. It supplies a bounded set of goal states and, in a separate ablation, measurements of existing tactic calls. It never puts newly discovered replacements or results from another model arm into this context.

## What the harness can call

```python
from proof_eval.model_context import build_context

context = build_context(
    evaluator, row, incumbent_code,
    max_sites=6,
    measure_costs=True,
    max_goal_chars=1000,
    max_snippet_chars=300,
)
```

The returned JSON records the exact proof SHA-256, primary compiler version, environment fingerprint, implementation hash, budgets, and observation status. Each site has original Python character offsets, a source fragment, before-goals, truncation indicators, and optional local allocation counts. Offsets refer to the supplied declaration, including its statement. They do not refer to the temporary instrumented file.

The site order is frozen by the existing compiler-backed selector: interleave proof blocks and selected single-line tactic leaves, prioritizing longer automation calls. Selection uses source syntax, not measurements or candidate successes. It is a bounded sample, not a complete profile. `conv` leaves are excluded because they have a different tactic category. Unexecuted syntax can have `not_observed` status even when the whole observed proof elaborates successfully; its state remains null.

Defaults retain at most three goals and two invocations per site. Long goals preserve their `⊢` target while explicitly truncating hypotheses. A tactic run repeatedly by a combinator has `invocation_count`; the top-level site fields show the first invocation and the bounded `invocations` array retains additional observations. Consumers must retain truncation indicators rather than implying they saw the full state.

The separate `.proof-eval/model_context/` cache is keyed by the incumbent, pinned environment, implementation (including site selection and source construction), and all observation budgets. Extraction executes the original proof under synchronous elaboration. It does not prepare or remeasure any reference and does not change the scoring backend. Failed or timed-out contexts are explicit and are not cached as successful observations.

For a controlled goals-versus-costs comparison, build the measured context once and whitelist only coordinates, fragments, before-goals, and availability/truncation fields for the goal-only arm. Add the measured cost fields only to the cost arm. This holds the exact observed sites and states fixed.

## What a tactic heartbeat number means

There is no portable constant such as “`simp` costs 100 heartbeats.” A tactic's work depends on its goal, local hypotheses, lemma set, reducibility and instance search, imported environment, compiler version, and elaboration/cache state. Heartbeats count small allocations rather than elapsed time: the counter is thread-local, and the public `maxHeartbeats` unit is thousands of allocations. [Lean's `IO.getNumHeartbeats` definition](https://github.com/leanprover/lean4/blob/v4.25.0/src/Init/System/IO.lean#L536-L542), [the public heartbeat option](https://github.com/leanprover/lean4/blob/v4.25.0/src/Lean/CoreM.lean#L28-L30).

Our optional diagnostic measures `finish - start` around `evalTactic` for the **existing single tactic at that observed state**. Goal formatting occurs before the counted interval; JSON logging occurs afterward. Both the allocation count and its division by 1000 are recorded. No alternate tactic is tried. A leaf containing another selected observation is deliberately not measured, so nested observation work cannot be mislabeled as original-tactic work. Proof-block observations have goals but no block cost.

These measurements still include elaborator dispatch overhead and can be influenced by instrumentation and earlier elaboration caches. They do not sum to the competition's whole-proof score and do not predict the cost after the model changes earlier proof steps. A comparatively expensive original call is an optimization lead, not proof that any replacement improves the score. The ordinary full-declaration evaluator remains the acceptance gate across all listed versions.

## Which context tools to use next

Primary sources were checked on 2026-10-03. The integration choices below are recommendations for this repository, not claims that one tool was experimentally shown superior here.

| Tool | Primary capability | Recommended role |
|---|---|---|
| [ntp-toolkit](https://github.com/cmu-l3/ntp-toolkit) | Repository extraction of tactic states, proof prefixes, premises, declarations, full proofs, and proof-state comments. | Use when building a larger training/retrieval corpus; unnecessary setup for the initial fifteen already-built inputs. |
| [jixia](https://github.com/frenzymath/jixia) | Plugins for declarations, symbols/reference graphs, elaboration/tactics, per-line states, and ASTs. Its executable must match the target Lean version exactly. | Useful for dependency-aware retrieval and offline indexing; budget separate builds for the competition toolchains before adopting it broadly. |
| [LeanProbe](https://github.com/epfl-lara/LeanProbe) | Warm LeanInteract-backed checking and goal/tactic interaction; bounded goal and diagnostic comments in `feedback_lean`. | A good future interactive-loop frontend. Keep its fast feedback distinct from fresh-process competition scoring. |
| [LeanInteract](https://github.com/augustepoiroux/LeanInteract) | Python communication with Lean REPL, including command/tactic responses. | The existing optional interactive layer; reuse when adding multi-attempt feedback rather than requiring model-specific tool contracts now. |

The specific annotation idea is directly supported by [ntp-toolkit's `state_comments` and `training_data` exports](https://github.com/cmu-l3/ntp-toolkit/blob/main/README.md), [jixia's line and elaboration plugins](https://github.com/frenzymath/jixia/blob/main/README.md), and [LeanProbe's `feedback_lean` implementation](https://github.com/epfl-lara/LeanProbe/blob/main/src/lean_probe/payloads.py). This first experiment obtains a small equivalent kind of feedback through the pinned compiler and the syntax facilities already tested in our deterministic harness. It does not install those three extraction tools or claim to compare their implementations.

The next tooling choice should follow the ablation: if goal annotations help, expand coverage or adopt richer info-tree extraction; if cost annotations help, investigate repeatability and representative-site selection; if neither helps, do not add their full setup to every inference request by default.

## Validation before model calls

Five context tests passed, including real Lean v4.25.0 checks of nested `by` blocks and Unicode coordinates, unchanged before-goals between measured and unmeasured extraction, cost scaling, cache reuse/invalidation, unavailable results, and no reference preparation. The preflight on all fifteen deterministic incumbents succeeded under each row's primary version: 88 selected sites, 87 observed goal sites, and 54 measured original tactic leaves. One site in `CallElimCorrect.extractedOldExprInVars` was not observed and remains null. Every rendered observed goal retained its target marker.

Reproduce the focused checks with:

```bash
python -m pytest -q tests/test_model_context.py
```

These checks establish that the context producer works on this cohort. They do not establish that supplying this context improves model proofs; that is the purpose of the separate one-shot ablation.
