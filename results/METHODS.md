# Deterministic optimization: evidence and experiment order

Research checked October 2, 2026. The aim is an incremental baseline on the **15
supplied warm-up declarations**, with no generated mathematical arguments or manual
per-problem rewrites. This is a measured starting point, not a claim of finding the
best possible model-free proof.

## What the sources actually support

[Lean Refactor v1](https://arxiv.org/html/2605.20244v1), the version requested by the
user, motivates measuring length, compilation cost and compatibility separately.
Its strategy retrieval and semantic rewrites involve models; those compression
numbers are not a deterministic baseline. Its displayed iterative algorithm keeps
successful shorter candidates, even though retrieval can be conditioned on other
objectives. Here the acceptance rule must instead use the arena's arithmetic mean.
Examples that replace extensive case analysis with a mathematical identity are
useful future proposals, but do not establish a universally applicable source edit.

[LeanPolish](https://arxiv.org/html/2609.38384v1), sections 3 and 5, is a more direct
model-free reference: compiler-checked local tactic replacement, unused-fact and
unreachable-code deletion, local-fact factoring, and repeated passes. It finds that
iterating its symbolic baseline can exceed its neural hybrids on one proof source;
this supports measuring the deterministic loop before attributing gains to training.
Its complete-menu analysis also exposes ordering bias in first-success training
records. Our batched-edit/fallback search is **not** its complete-menu reproduction,
and the saved attempts must retain that distinction. Its specificity policy and
length-based selection serve a different objective from the arena score.

The [Lean tactic reference](https://lean-lang.org/doc/reference/latest/Tactic-Proofs/Tactic-Reference/)
documents `simp?`, `simp_all?` and `dsimp?` as sources of explicit `only` lemma sets,
which can reduce simplifier work. It recommends incorporating the result of library
search (`exact?`, `rw?`) rather than leaving search tactics in a finished proof.
An explicit lemma list can be longer; it belongs in an experiment because heartbeat
savings may outweigh the token cost. Suggestions are proposals, not compatibility
certificates: recheck them in every listed environment.

Mathlib's [unused-tactic linter documentation](https://leanprover-community.github.io/mathlib4_docs/Mathlib/Tactic/Linter/UnusedTactic.html)
describes checks for tactics that do not change goals, but notes coverage limitations
and interaction with scoped `set_option`. Accordingly, analysis runs separately
from heartbeat instrumentation, and linter-nominated deletions are recompiled.
The local source context, namespace, notation and available tactics are preserved;
we do not add Mathlib to projects that do not already import it.

## Experiments to execute in order

1. **Reference control.** Build pinned contexts, fix evaluator integration defects,
   record coverage, and cache local originals once per evaluator/environment
   fingerprint. Preserve the organizer's heartbeat values separately. Never select
   on published-reference/local-candidate heartbeat ratios.
2. **Unused/unreachable-tactic deletion.** Collect exact Lean syntax spans and
   diagnostics; handle surrounding `try`, parentheses and `<;>` syntax. Try joint
   deletion, then individual edits if joint deletion fails or regresses. Reanalyze
   after acceptance. This establishes whether cheap compiler feedback is useful.
3. **Explicit simplifier lemmas.** Obtain suggestions for existing simplifier calls
   in one instrumented pass, materialize ordinary tactics, then measure. Judge
   longer candidates normally. Keep failed cross-version suggestions in the log.
4. **Unused facts and wrapper contraction — next ablation.** Remove unused `have`
   blocks using elaborated dependencies, and contract `have h : T := by ...; exact h`
   where the scope permits it. Automation may use a fact without naming it, so a
   textual name-count heuristic cannot certify a deletion. Test this after the
   first two stages rather than mixing their gains together.
5. **Bounded local tactic menu — next ablation.** At captured goal-closing sites,
   try `rfl`, `assumption`, `contradiction`, and applicable arithmetic procedures
   such as `omega`, `ring`, `norm_num`, `linarith`. Extend with materialized `exact?`
   and `aesop?` suggestions where available. Use identical per-site budgets and
   record every menu entry, including skips and failures, before choosing by score.
6. **Lemma-list minimization and repeated sweeps.** Delta-debug explicit `simp only`
   lists and arithmetic hint lists; repeat independent passes until a declared
   budget or no-improvement condition. Report marginal gain and CPU cost per sweep.
   Only then consider factoring repeated facts or domain-specific rewrites.

## What determines the next step

If deletion has little gain but explicit simplification reduces heartbeats, target
expensive remaining tactic sites before broad whole-proof search. If most gains
are from unused local facts, build the dependency-based deletion pass next. If
version failures dominate, distinguish unavailable tactics from renamed lemmas and
try version-stable alternatives. Do not turn warm-up averages into an expected
score on the unreleased benchmark.

The common interface for both tracks remains a full-declaration candidate and
structured evaluator feedback. Open-model training can later learn candidate
generation or proposal ranking. Whether to teach explicit tool use is a separate
matched-budget experiment; these measurements do not assume it helps. Keep any
model-assisted stage after the deterministic baseline so its additional contribution
is visible.
