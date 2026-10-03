# Strategy and proof-state context for one-shot editing

Research checked **2026-10-03**. The initial artifact is an [18-card strategy bank](../prompts/strategy_bank.json), written in our own words from the sources below. Each card records applicability conditions, an action, failure modes, source URLs, and an empty evidence list. These are suggestions to evaluate, not validated improvements or a ranking of tactics. No warm-up proof, selected winner, or external demonstration is embedded in the bank.

## What is actually available

Lean Refactor v2 describes 9,237 strategies, a learned retriever, version metadata, and compilation-cost estimates. Its strategy cost estimate is the median profiled **compilation-time speedup** across associated proof pairs; it is not a fixed heartbeat cost for a tactic. The paper also describes heartbeat experiments separately. Our cards retain the useful conditional-strategy structure without claiming to reproduce its bank or trained retrieval. [Paper, sections 3.1–3.3 and appendices B, K, N, O](https://arxiv.org/pdf/2605.20244v2).

I did not locate a downloadable complete strategy bank in the public resources inspected: the official repository's recursive tree and source files at `9c98a3a097e53724e35b2a2e7fe316c331efa20a`, its README, the paper's Hugging Face metadata, and the linked project page. The project page redirected to the arena. This is a bounded availability check, not a claim that no release exists elsewhere. The public code does expose planner/executor prompts and a Mathlib **lemma** retrieval path. No code or prompt text from that repository is copied here; its checked root had no license file. [Pinned repository](https://github.com/delta-lab-ai/lean-refactor/tree/9c98a3a097e53724e35b2a2e7fe316c331efa20a), [planner](https://github.com/delta-lab-ai/lean-refactor/blob/9c98a3a097e53724e35b2a2e7fe316c331efa20a/lean_refactor/data/prompts/planner-initial.md), [lemma finder](https://github.com/delta-lab-ai/lean-refactor/blob/9c98a3a097e53724e35b2a2e7fe316c331efa20a/lean_refactor/data/prompts/lean-finder.md).

| Source | Checked revision and license | Use here |
| --- | --- | --- |
| [Lean4 Skills](https://github.com/cameronfreer/lean4-skills/tree/b6243b85b9b0a0ddff5bb6773889044daf687f8e) | `b6243b85b9b0a0ddff5bb6773889044daf687f8e`, [MIT](https://github.com/cameronfreer/lean4-skills/blob/b6243b85b9b0a0ddff5bb6773889044daf687f8e/LICENSE) | Ideas about local proof construction, library reuse, transfer lemmas, and elaboration guidance. |
| [mathlib-quality](https://github.com/CBirkbeck/mathlib-quality/tree/b1c9439a258fab2b0397676489b3bada7911d4ac) | `b1c9439a258fab2b0397676489b3bada7911d4ac`, [MIT](https://github.com/CBirkbeck/mathlib-quality/blob/b1c9439a258fab2b0397676489b3bada7911d4ac/LICENSE) | Ideas about simplification, local sharing, specialized automation, and profiling. Its claimed PR-mining provenance was not independently audited. |
| [LeanPolish code](https://github.com/paulinebourigault/leanpolish/tree/70cda81a15cca1f805885df197361102f0123cbb) | `70cda81a15cca1f805885df197361102f0123cbb`, [Apache-2.0](https://github.com/paulinebourigault/leanpolish/blob/70cda81a15cca1f805885df197361102f0123cbb/LICENSE) | Future example retrieval and selector supervision; not loaded into the first bank. |
| [LeanPolish dataset](https://huggingface.co/datasets/leanpolish-anon/lean-proof-compression/tree/64422193ada0449e2a60d4486955e7319920ed69) | `64422193ada0449e2a60d4486955e7319920ed69`, dataset card declares Apache-2.0; upstream proof licenses remain relevant | Future examples after source overlap checks and target-environment validation. |

The source skills are reading material for this bank, not installed agent workflows. We deliberately discard their unconditional tactic priority ladders, fixed percentage claims, and labels such as risk-free. Recommendations favoring newer tactic syntax are conditional on the arena's pinned environment. We also exclude changes to theorem signatures, imports, definitions, global attributes, and top-level helpers. Only the original declaration's proof body may change; local helpers remain possible. [Arena rules saved in this repository](../RULES.md).

## Heartbeats belong to an execution, not a tactic name

Lean defines the low-level heartbeat counter in terms of small allocations in the current thread, for timeouts that are more deterministic across hardware. It is not elapsed time. [Lean 4.24.0 source](https://github.com/leanprover/lean4/blob/797c613eb9b6d4ec95db23e3e00af9ac6657f24b/src/Init/System/IO.lean). A concrete warning against transferring cost constants between versions comes from Lean 4.31: recording metavariable indices increased some heartbeat budgets by 20–50% without a matching runtime slowdown. [Release note for change #13030](https://lean-lang.org/doc/reference/latest/releases/v4.31.0/).

Consequently, a table saying that `simp` costs a fixed number of heartbeats would be misleading. Its work depends on the goal, local hypotheses, rules, instances, compiler/project revision, and options. The same applies to `exact`, whose argument may require expensive elaboration. The useful measurement is an original/replacement pair in the same environment with a clearly defined measurement boundary.

For model context, distinguish three evidence levels:

| Context | What it can establish | What it cannot establish |
| --- | --- | --- |
| Goal and local hypotheses before a tactic | What the current step must prove | Whether an unseen replacement compiles |
| Tactic-span cost on the current incumbent | Where that execution performed work | An additive prediction of the complete replacement's cost |
| Fresh full-declaration candidate measurement | The actual candidate's local length, heartbeat, and version results | Performance of the same strategy on another theorem |

Nested tactic spans can include their children's work, so summing all spans double-counts. Instrumented discovery, saved-state probing, and a fresh scoring process can also have different setup costs. Keep measured span costs labeled as diagnostic observations; use the existing evaluator and cached references for acceptance. Do not remeasure references just to produce prompt context.

Future evidence records should include the theorem/proof hash, environment fingerprint, measurement method, original and replacement token counts, original and replacement heartbeats, all version checks, failures/timeouts, and the resulting combined-score change. Aggregate only comparable records; retain failures and sample counts. Even a well-supported median is a conditional prior, not a promise to the model. The current cards leave `evidence` empty rather than filling it with unmeasured assertions.

The experiments now provide [five verified before/after examples](../results/one_shot/OBSERVED_TRANSFORMATIONS.md), with exact proof snapshots and measurement provenance. These are post-hoc warm-up observations for a future bank experiment, kept separate from the frozen input cards. Single-edit cleanup comparisons apply to their recorded states; whole-proof rewrites do not isolate the contribution of each change.

## First experiment: isolate cards, goals, and measured costs

The planned comparison has a 2×2 core plus a fifth cost-context arm, all using the same incumbent proofs:

| Arm | Additional context beyond the common proof, objective, and environment information |
| --- | --- |
| Base | None |
| Cards | A bounded lexical selection from the reviewed bank |
| Goals | A bounded selection of actual goals and local hypotheses |
| Cards + goals | Both additions |
| Cards + goals + costs | The same selected states, also labeled with observed incumbent tactic allocations |

Use the three requested models, temperature 0.3 and high reasoning, with one response per model/arm/problem and a 32,768-token output limit: 15 problems × 3 models × 5 arms = 225 requests. Pilot one base request per model and retain it for the matrix if its request is identical. Keep the parser, evaluator, reference cache, and acceptance policy fixed. Do not insert repairs, model tool calls, best-of-N sampling, or feedback from another arm. Save exact rendered messages and retrieval selections. More context consumes input tokens; report that cost even when the output budget is fixed.

The bank's lexical triggers are a deliberately simple first selector. A matching word only retrieves a possible strategy; the model must still assess its conditions. Start with a small number of cards, rather than all 18 on every proof. This count is an engineering budget, not a research-backed optimum. The same generation contract can serve both tracks because tool execution remains in the harness.

Report candidate pass rate, compatibility, per-axis scores, accepted improvement over the shared incumbent, token usage, latency, and truncation/API failures. A final submission may retain an incumbent where the single candidate fails or loses, but report raw candidate outcomes separately so fallback does not disguise failures. On 15 warm-up problems, treat differences as development evidence; do not call a prompt configuration universally better from a single stochastic draw. Preserve this first matrix before changing prompts.

`ntp-toolkit` and `jixia` are extraction/context infrastructure; an annotated goal stream such as LeanProbe is another way to make a local transformation concrete. The initial question is what **information** helps, so a small compatible extractor using the existing pinned environments is preferable to simultaneously changing the verifier, adding an agent tool protocol, and changing prompts. Compare external extractor integrations later using the same serialized context contract. The paper explicitly says it uses adapted versions of the two extractors; that is not a guarantee of drop-in support for every arena version. [Paper, section 3 footnote 2](https://arxiv.org/pdf/2605.20244v2).

## Correctness-only debugging

The next implemented step is [correctness-only debugging](../docs/VALIDITY_REPAIR.md):
retain the initial optimization proposal, then allow up to three compiler-error
corrections and stop at the first proof valid on all required versions. Candidate
performance is evaluated by the harness afterward and never returned to the
debugger. This separates the diagram's compile/debug cycle from score-guided
replanning. The [repair results](../results/one_shot/02_validity_repair/) preserve
their initial direct-output cells and additional request counts. Empty outputs
without a proposed declaration remain a separate failure mode.

The [combined deterministic experiment](../docs/COMBINED.md) then applies the
existing bounded optimizers to valid model proposals, including initially
inferior ones. An identical pass on each original incumbent provides the control
needed to distinguish the model branch's contribution from additional
deterministic work. This adds no model requests or performance feedback.

## External demonstrations come after the first ablation

LeanPolish's pinned dataset reports 33,402 accepted local edits and 65,596 rejected siblings, with verification under Lean/Mathlib 4.21.0. Its `training` split denotes accepted edits within a source configuration, including competition sources; it is not itself a clean holdout split for this arena. Begin a later example-retrieval experiment with `mathlib` and `goedel`, check theorem/file/statement overlap, and retain original source attribution. Recheck replacements in target environments before attaching arena measurement labels. The release's failure distributions also reflect candidate ordering and are not complete tactic menus. [Pinned dataset card](https://huggingface.co/datasets/leanpolish-anon/lean-proof-compression/blob/64422193ada0449e2a60d4486955e7319920ed69/README.md).

Whole-proof training material is available separately: the released construction statistics contain 6,852 shortened pairs and 856 unchanged pairs. Those are useful future retrieval or SFT inputs, but importing them now would mix demonstration quality, retrieval quality, and abstract-card effects in the first experiment. [Pinned construction statistics](https://github.com/paulinebourigault/leanpolish/blob/70cda81a15cca1f805885df197361102f0123cbb/experiments/wholeproof/results/build_stats.json), [construction and evaluation README](https://github.com/paulinebourigault/leanpolish/blob/70cda81a15cca1f805885df197361102f0123cbb/experiments/wholeproof/README.md).
