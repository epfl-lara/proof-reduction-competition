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
records. Our menu evaluates all entries at selected sites during discovery, then
scores materialized candidates within a separate trial cap. The structural passes
use first-improvement selection. This is a bounded adaptation, not a complete
reproduction; its acceptance objective also differs from LeanPolish's length-based
selection and specificity policy.

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

## Implemented portfolio and scope

The following is the completed main experiment order. Each folder's saved
results establish its measured contribution. Local references are
cached once per evaluator/environment fingerprint; organizer heartbeat values
remain separate. Candidate selection never mixes published reference heartbeats
with locally measured candidate heartbeats.

| Folder / method | Proposals | Selection policy |
| --- | --- | --- |
| `01_linter_deletion` / `lint` | Delete syntax spans nominated by unused/unreachable-tactic linters; preserve surrounding combinator syntax. | Joint proposal, then individual alternatives. |
| `02_explicit_simp` / `simp` | Materialize `simp?`, `simp_all?`, and `dsimp?` suggestions at existing calls. | Joint proposal, then individual alternatives. |
| `03_wrappers` / `wrappers` | Contract adjacent `have/let h := rhs; exact h`, including nested scopes. | Joint proposal, then first improving individual. |
| `04_local_facts` / `facts` | Delete local `have`/`let` bindings; prioritize names without later textual references. | Joint proposal, then first improving individual. |
| `05_fact_reuse` / `reuse` | Reuse earlier same-scope facts with matching explicit types or RHSs; contract simple identifier aliases. | First improvement. |
| `06_tactic_menu` / `menu` | Try the fixed closing-tactic menu at parsed `by` blocks and selected tactic leaves. | Best fully scored candidate in the current bounded batch. |
| `07_library_search` / `search` | Materialize explicit suggestions from `exact?`, `aesop?`, and `grind?`. | Best fully scored candidate in the current bounded batch. |
| `08_simp_minimization` / `simp_min` | Delete chunks or individual entries from `simp only`, `simp_all only`, and `dsimp only` lists. | First improvement. |
| `09_arithmetic_minimization` / `arith_min` | Delete hints from `linarith`/`nlinarith` lists. | First improvement. |
| `10_rewrite_minimization` / `rw_min` | Delete entries from `rw`/`rewrite` lists while retaining their order. | First improvement. |

[Structural proposals](../../src/proof_eval/structural.py) use compiler syntax spans,
not an elaborated dependency graph. Textual nonreference is only an ordering hint:
`omega`, `simp_all`, and typeclass search may consume a fact implicitly. Reuse and
alias replacement likewise require compilation to resolve context and shadowing.
The current implementation skips parameterized local definitions, anonymous or
pattern bindings, and bindings directly inside tactic combinators. Nested edits
can overlap; disjoint edits can still interact semantically.

The [fixed tactic menu](../../src/proof_eval/tactic_search.py) is `rfl`, `assumption`,
`trivial`, `contradiction`, `omega`, `ring`, `abel`, `norm_num`, `norm_cast`,
`positivity`, `linarith`, `nlinarith`, `tauto`, `decide`, `grind`, `simp`, `simp_all`,
`dsimp`, and `aesop` (19 entries). Each entry is
tried from the same saved goal state. Unsupported tactics and failures are logged.
Search-tactic suggestions must become ordinary proof code; ambiguous suggestions,
placeholders, and remaining query tactics are rejected. Discovery success alone
never certifies a replacement.

[List minimization](../../src/proof_eval/lemma_minimization.py) uses recognized AST
families and argument spans, preserving `only`, locations, tactic configuration,
and the order of retained entries. It proposes whole-list removal, progressively
smaller partitions, and singletons. Unused-simplifier-argument diagnostics affect
ordering only. Unsupported parser shapes are skipped; arbitrary tactic arguments,
lemma permutations, and mathematical generalization are outside this pass.

## Budgets, acceptance, and repeated sweeps

New portfolio stages use **6 rounds, 64 candidate trials, 6 discovery sites per
batch, and a 0.05 percentage-point minimum combined-score gain**, per problem and
method. Earlier stages retain their original recorded configurations. A discovery
entry has a 5,000-heartbeat bound; its whole probe process has a 120-second timeout.
These discovery bounds do not alter scoring instrumentation or cached references.

The [experiment engine](../../src/proof_eval/experiments.py) first measures a candidate
in the primary version. If even 100% compatibility cannot beat the incumbent by
the margin, it skips other versions. Otherwise it requests every required version
and accepts only an available, improved combined score. A length reduction alone
does not justify acceptance. Menu/search discovery tries the complete menu for
the selected batch; score selection considers all materialized alternatives that
fit the remaining trial cap. Other new methods use the first-improvement policies
above. These are different search budgets, not exhaustive optimization claims.

For menu/search, an empty or nonimproving batch advances to the next site slice
while rounds remain. Accepting an edit resets the site offset and reanalyzes the
new proof. Coverage, failures, limits, and candidate outcomes remain in trial logs.
Discovery failure or timeout stops the problem as unavailable rather than counting
it as evidence that the method cannot improve the proof.

[The portfolio runner](../../src/run_portfolio.py) then repeats all eight new methods,
followed by linter deletion and explicit simplification, in separate sweep folders.
It stops after a full bounded sweep changes no proof, reaches the declared sweep
cap (default two), or encounters unavailable discovery. Sequential gains depend on
earlier accepted edits; they are not independent ablations or a global fixed point.
The recorded run completed both sweeps and stopped at the sweep cap: the first
added 1.400308 pp and the second 0.136130 pp. The separate early-arithmetic branch
starts from stage 03 and is excluded from the main cumulative score.

[Stage runs](../../src/run_experiments.py) checkpoint pending candidates, selected
proofs, and site offsets. Repeating an identical command resumes unfinished work.
Completed `discovery_unavailable` records are preserved and are not automatically
retried; use a fresh output folder for a retry or changed implementation/budget.
The first library-search attempt exposed inline-proof indentation and `conv`
site-selection defects. Its [evidence and repair notes](failed_attempts/07_library_search_v1/REPAIR.md)
are preserved separately. Completed historical stages can be resumed by the
portfolio only after auditing their exact inputs, budgets, proof evidence and
current or hash-verified archived source; unfinished runs still require matching
implementation hashes. Later new stages use the repaired probe. Parallelism was
increased from four workers to eight for new stages; each configuration preserves
the worker count actually used, and `portfolio.json` records the change.
Reports compare selected proofs with both the preceding stage and the measured
original control. Warm-up gains do not predict the unreleased benchmark score.

The common interface for both tracks remains a full-declaration candidate and
structured evaluator feedback. Open-model training can later learn candidate
generation or proposal ranking. Whether to teach explicit tool use is a separate
matched-budget experiment; these measurements do not assume it helps. Keep any
model-assisted stage after the deterministic baseline so its additional contribution
is visible.
