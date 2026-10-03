# Frozen context coverage audit

Checked **2026-10-03**, using only the 15 saved input packs and all 225 exact request messages. No model outputs or scores from this experiment were consulted; no Lean processes or model requests were run for this audit. The prompts, bank, inputs, and runtime were unchanged.

For every theorem and arm, the three models receive identical system/user messages. All arms contain the same **complete incumbent declaration**, exact statement, score objective, reference denominators, required versions, and preceding-source excerpt. The four selected cards are identical across the three card-bearing arms. The goal annotations are identical across the three goal-bearing arms after removing cost-related fields. Thus the coverage differences below are in the frozen auxiliary context, not in omission of part of the incumbent proof.

## Selected strategy cards

Each card-bearing request receives four cards. Across 15 theorems, these 60 slots use **11 of the 18 bank cards**. Selection is lexical; a selected card is a hypothesis about a useful transformation, not proof that its conditions hold. A card absent from these requests is not tested by this ablation.

| ID | Theorem | Source | Selected card IDs, in request order |
| --- | --- | --- | --- |
| P01 | `CallElimCorrect.substOldPostSubset` | strata | `consolidate_simpa`, `collapse_apply_exact`, `restrict_simplification`, `reuse_available_lemma` |
| P02 | `CallElimCorrect.extractedOldExprInVars` | strata | `collapse_apply_exact`, `consolidate_simpa`, `reuse_available_lemma`, `restrict_simplification` |
| P03 | `Core.InitsUpdatesComm` | strata | `collapse_apply_exact`, `guide_elaboration`, `consolidate_simpa`, `inline_single_use` |
| P04 | `fundamental_theorem_of_variational_calculus'` | physlib | `guide_elaboration`, `collapse_apply_exact`, `inline_single_use`, `match_arithmetic_fragment` |
| P05 | `Electromagnetism.ElectromagneticPotential.time_deriv_time_deriv_electricField_of_isExtrema` | physlib | `collapse_apply_exact`, `consolidate_simpa`, `eta_reduce`, `guide_elaboration` |
| P06 | `FieldSpecification.WickAlgebra.ι_timeOrderF_superCommuteF_eq_time` | physlib | `guide_elaboration`, `share_local_work`, `eta_reduce`, `inline_single_use` |
| P07 | `Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress` | cslib | `collapse_apply_exact`, `guide_elaboration`, `inline_single_use`, `remove_unused_local` |
| P08 | `Cslib.SKI.parallelReduction_diamond` | cslib | `collapse_apply_exact`, `guide_elaboration`, `inline_single_use`, `consolidate_simpa` |
| P09 | `Cslib.CCS.bisimilarity_congr_choice` | cslib | `collapse_apply_exact`, `consolidate_simpa`, `eta_reduce`, `share_local_work` |
| P10 | `Binius.BinaryBasefold.fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius` | arklib | `guide_elaboration`, `compress_transitivity`, `inline_single_use`, `reuse_available_lemma` |
| P11 | `Binius.BinaryBasefold.fold_advances_evaluation_poly` | arklib | `guide_elaboration`, `inline_single_use`, `match_arithmetic_fragment`, `collapse_apply_exact` |
| P12 | `interleaved_affine_gaps_imply_tensor_gaps` | arklib | `guide_elaboration`, `consolidate_simpa`, `inline_single_use`, `remove_unused_local` |
| P13 | `putnam_1964_a4` | putnambench | `guide_elaboration`, `collapse_apply_exact`, `consolidate_simpa`, `inline_single_use` |
| P14 | `putnam_1964_b2` | putnambench | `guide_elaboration`, `inline_single_use`, `remove_unused_local`, `collapse_apply_exact` |
| P15 | `putnam_1995_a3` | putnambench | `match_arithmetic_fragment`, `share_local_work`, `collapse_apply_exact`, `consolidate_simpa` |

The most frequent cards are `collapse_apply_exact` (12 theorems), `guide_elaboration` (11), `inline_single_use` (10), and `consolidate_simpa` (9). The seven unselected cards are `remove_term_wrapper`, `restrict_arithmetic_hints`, `transfer_known_property`, `use_extensionality`, `replay_supplied_search`, `prune_rewrites`, and `specialized_function_property`. These counts describe this particular incumbent set and selector, not the relative merit of the strategies.

## Goal and original-tactic cost coverage

The extractor recorded **709 eligible syntax sites**, selected **88**, and observed goals at **87**. It measured incumbent-tactic costs at **54** selected sites. The selected-site ratio is 12.4%, but this is not a percentage of mathematical obligations covered: eligible sites include nested `by` blocks and tactic nodes, and their scopes can overlap. The limit is six selected sites per theorem; P09 has only four eligible sites.

In the table, “goal trunc.” counts sites whose saved goal text is marked truncated; “snippet trunc.” counts shortened tactic/block snippets. The full incumbent remains available independently. Tokens are the saved competition body-token count of that incumbent.

| ID | Incumbent tokens | Selected / eligible sites | Observed goal sites | Cost-measured sites | Goal trunc. | Snippet trunc. | Source excerpt chars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P01 | 303 | 6 / 46 | 6 | 5 | 5 | 1 | 6,000 |
| P02 | 232 | 6 / 24 | 5 | 4 | 1 | 1 | 6,000 |
| P03 | 222 | 6 / 18 | 6 | 5 | 0 | 1 | 6,000 |
| P04 | 809 | 6 / 37 | 6 | 3 | 4 | 3 | 3,087 |
| P05 | 1366 | 6 / 37 | 6 | 3 | 2 | 2 | 6,000 |
| P06 | 1270 | 6 / 27 | 6 | 3 | 3 | 2 | 6,000 |
| P07 | 398 | 6 / 20 | 6 | 5 | 0 | 1 | 2,557 |
| P08 | 408 | 6 / 18 | 6 | 5 | 0 | 1 | 4,694 |
| P09 | 251 | 4 / 4 | 4 | 3 | 0 | 1 | 6,000 |
| P10 | 1335 | 6 / 115 | 6 | 3 | 6 | 3 | 6,000 |
| P11 | 1648 | 6 / 133 | 6 | 3 | 6 | 3 | 6,000 |
| P12 | 1139 | 6 / 29 | 6 | 3 | 5 | 2 | 6,000 |
| P13 | 1193 | 6 / 62 | 6 | 3 | 1 | 3 | 91 |
| P14 | 348 | 6 / 31 | 6 | 3 | 0 | 1 | 107 |
| P15 | 2893 | 6 / 108 | 6 | 3 | 0 | 3 | 99 |

There are **33 goal-truncated sites** and **28 snippet-truncated sites**. The saved options cap each displayed goal at 1,000 characters, each snippet at 300 characters, goals per invocation at three, and stored invocations per site at two. Two sites report invocation truncation (P08 and P14): 93 observed invocations are counted across all sites, while 89 invocation records are retained. Site-level first-observation summaries and their invocation records should not be counted as independent observations.

The sole unobserved selected site is P02, site 2, the `simp_all` span at character offsets 317–325. Its goals and costs are absent; the artifact does not establish why it was unobserved. The cost-unmeasured total is 34 sites: 33 `by_block` sites and this unobserved tactic site. Missing costs are not zero-cost observations. Measured allocations describe the original tactic in its instrumented state, not the prospective replacement or a portable cost of that tactic name.

All goal/cost annotations come from the **primary version** stored in the input pack. The requests list every required version, but do not include a separate goal stream for each version. Cross-version success therefore remains a property for the evaluator to check.

## Where the context is narrow

- **ArkLib has the tightest observed coverage.** Its three proofs have 18 selected sites out of 277 eligible sites, and 17 of those 18 goal displays are truncated. P10 has six of 115 sites; P11 has six of 133. These are concrete reasons to interpret the goal arm as a small sample of proof states, rather than a full annotation of these declarations.
- **Long competition proofs are also sampled.** P15 has 2,893 incumbent tokens and six of 108 sites selected. Its displayed goals are not truncated, but most eligible locations are unannotated.
- **Source excerpts have a separate limitation.** Nine proofs (P01–P03, P05–P06, P09–P12) reach the 6,000-character preceding-source bound. Their saved excerpts visibly start inside existing declarations or proofs: P01 begins with `a ++ b).Subset c := by`, P05 with an indented `apply ContDiff.comp`, and P10 with `) := by`. The excerpt alone therefore does not supply a complete leading context for those files.
- **An excerpt is not dependency retrieval.** No request field supplies a complete index of referenced declaration signatures or definition bodies. Earlier declarations outside the excerpt and imported module contents are not expanded. Even the shorter excerpts that start at the file header expose import names, not all imported APIs. Actual local hypotheses/goals improve visibility at selected sites, but do not replace the omitted global dependency information.

These facts establish limits on the context supplied. They do **not** establish that the model needs every omitted declaration, that an omitted site contains an improvement, or that any particular output failure was caused by missing context. Any later comparison of more sites, fuller dependencies, or different card retrieval should be a separately frozen experiment, rather than a change to this running matrix.

## Serialized context size

Character counts below are for the exact user message, including JSON structure and escaped content; they are not model token counts. System messages are identical. Provider token usage belongs in the outcome report.

| Arm | Mean user-message chars | Minimum | Maximum |
| --- | ---: | ---: | ---: |
| `plain` | 10,816.7 | 2,848 | 18,491 |
| `cards` | 12,792.0 | 4,781 | 20,517 |
| `goals` | 24,095.9 | 11,932 | 36,159 |
| `cards_goals` | 26,071.1 | 13,865 | 38,185 |
| `cards_goals_costs` | 27,255.5 | 15,155 | 39,381 |

Cards add about **1,975 characters** per user message on average. Goals add about **13,279** over `plain`; adding cost fields to `cards_goals` adds about **1,184**. This measures the actual context burden of the present serialization; it does not establish an optimal context size.

## Audit anchors

- [`config.json`](config.json), SHA-256 `5240120b9e4c1c443e179c0eec6f91127375648bfdf99d3aeef68070d084f71f`.
- [`input_hashes.json`](input_hashes.json), SHA-256 `2992c13b65c6f62827feeebf37f94603c62a48558b1907c6e1f8c874371944dd`.
- [`cell_index.json`](cell_index.json), SHA-256 `0706ec67cd1c358055e27f3ddd3d180a2127e9281dadd2632764989f5b021821`.
- [Saved input packs](inputs/) contain site offsets, primary version, proof/environment fingerprints, truncation flags, and context options. Exact messages are in the indexed `cells/<request_sha256>/request.json` files.
