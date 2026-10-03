# Proof changes behind Astra's score

These cases compare the **original seed → Astra/max original arm**, so none
of the reported improvements require deterministic transforms. Token counts
use the competition-compatible source counter. Heartbeats use the saved local
evaluator's units and primary version; all final declarations passed all their
listed versions. The conclusions describe visible source edits and tool use.

## 1. Remove an induction by composing existing lemmas

`Core.InitsUpdatesComm`: **224 → 92 tokens; 4,253.479 → 287.368 heartbeats**.

The original inducts over updates and repeatedly simplifies stores, constructs
an intermediate state and invokes single-state commutation. Astra uses the
existing representation theorems to express both operations as `updatedStates`,
then applies the existing commutation theorem directly:

```lean
  rw [InitStatesUpdated Hinit, UpdateStatesUpdated Hup]
  unfold updatedStates
  rw [updatedStatesComm]
```

The remaining obligations use length, definedness and disjointness facts
already available in the project. Source lookups found those facts and
`List.unzip_zip`, with alternate-version signature checks before the single
successful validity call. This is library composition, not simply a shorter
spelling of the original induction.

Astra/low also finds a strong solution here (90 tokens, 314.653 heartbeats),
slightly beating max on the combined score. Luna/max keeps 214 tokens despite
reducing heartbeats to 402.975. Luna/high stays close to the original.

[Original](cases/03_InitsUpdatesComm/original.lean) ·
[Astra proof](cases/03_InitsUpdatesComm/astra_max_original.lean) ·
[Diff](cases/03_InitsUpdatesComm/astra_max_original.diff) ·
[Commands](cases/03_InitsUpdatesComm/astra_max_original_trace.json)

## 2. Spend more tokens to remove expensive search

`Fsub.Typing.progress`: **408 → 443 tokens; 59,833.580 → 577.335 heartbeats**.

Astra replaces repeated `grind` branches with explicit value/reduction
constructors, canonical-form lemmas and well-formedness projections. For
example, the application case supplies exactly the witnesses required:

```lean
    rcases ih_l rfl with vl | ⟨s, h⟩
    · rcases ih_r rfl with vr | ⟨s, h⟩
      · obtain ⟨σ, b, rfl⟩ := l.canonical_form_abs vl
        exact ⟨_, .abs vl.lc vr⟩
      · exact ⟨_, .appᵣ vl h⟩
    · exact ⟨_, .appₗ r.wf.2.1 h⟩
```

It inspects `Typing`, `Reduction`, local-closure and value definitions,
including cross-version diffs. The proof passes its one internal check.
Astra/low instead reaches 360 tokens while retaining 59,118.127 heartbeats.
Luna/max also makes a structural improvement but uses 519 tokens and
1,028.802 heartbeats; Luna/high's selected proof is the original.

The max score is 63.485556% versus low's 37.653481%. A shortest-source-only
instruction would miss why the longer result is better for the competition.

[Original](cases/07_progress/original.lean) ·
[Astra proof](cases/07_progress/astra_max_original.lean) ·
[Low proof](cases/07_progress/astra_low_original.lean) ·
[Commands](cases/07_progress/astra_max_original_trace.json)

## 3. Induct on evidence carrying the invariant

`CallElimCorrect.extractedOldExprInVars`:
**222 → 144 tokens; 2,697.873 → 417.131 heartbeats**.

The original inducts on the expression, then separately unpacks normalization
and proves subset facts. Astra instead inducts on the `NormalizedOldExpr`
derivation. Many cases become reflexivity, an empty-list inclusion, or direct
use of an induction hypothesis. A local `app` lemma composes append-subset
facts once for all relevant branches. Luna/max also changes the induction
object, but repeats more membership/disjunction reasoning.

This is also the strongest counterexample to always feeding a shorter seed.
The D0-seeded Astra proposal uses only **54 tokens**, but **2,454.356 heartbeats**,
scoring 61.567312%. Cleanup raises that to 62.002346%, still well below the
original-arm 73.224553%. Different generations are involved; the observation
does not establish that D0 itself caused the worse choice.

[Original](cases/02_extractedOldExprInVars/original.lean) ·
[Astra proof](cases/02_extractedOldExprInVars/astra_max_original.lean) ·
[Seeded model proof](cases/02_extractedOldExprInVars/astra_max_deterministic_model.lean)

## 4. Replace detailed analysis with a stronger positivity API

`fundamental_theorem_of_variational_calculus'`:
**851 → 227 tokens; 11,951.837 → 2,078.781 heartbeats**.

The original builds a detailed neighborhood bound through norms,
`WithLp`, Cauchy–Schwarz and support/measure arguments. Astra observes that
`x ↦ ⟪f x, f x₀⟫` is continuous and positive at a nonzero point. It obtains
a positive neighborhood, chooses `ContDiffBump`, and applies
`integral_pos_of_integrable_nonneg_nonzero` to contradict the hypothesis.
Its commands search the bump-function and integral-positivity interfaces.

Astra/low finds the same kind of replacement (317 tokens, 2,674.841 heartbeats).
Luna/max largely retains the original architecture (765 tokens, 11,672.169
heartbeats). This helps explain the 85.31% versus 37.48% scores.

[Original](cases/04_fundamental_theorem_of_variational_calculus/original.lean) ·
[Astra proof](cases/04_fundamental_theorem_of_variational_calculus/astra_max_original.lean) ·
[Luna proof](cases/04_fundamental_theorem_of_variational_calculus/luna_max_original.lean) ·
[Commands](cases/04_fundamental_theorem_of_variational_calculus/astra_max_original_trace.json)

## 5. Factor the mathematical identity before doing arithmetic

`putnam_1995_a3`: **4,085 → 292 tokens; 17,957.759 → 3,228.975 heartbeats**.

A local lemma expresses a one-digit replacement as the original number plus
`(b i - a i) * 10 ^ i.1`. Astra uses it for both relations, sums the divisibility
facts with `Finset.dvd_sum`, and obtains a divisibility constraint on the sum
of the two numbers. It then cancels the power of ten using:

```lean
  have hc : IsCoprime (7 : ℤ) 10 := ⟨3, -2, by decide⟩
  apply (hc.pow_right (n := i.1)).dvd_of_dvd_mul_right
```

The final arithmetic is bounded `ring`/`omega`, replacing duplicated long
derivations. The trace searches coprimality, cancellation, finite-sum and
sum-if APIs. Astra/low also performs well (446 tokens), while Luna/max retains
1,471 tokens and 10,189.578 heartbeats after an outer repair. Luna/high's
selected proof is the original.

[Original](cases/15_putnam_1995_a3/original.lean) ·
[Astra proof](cases/15_putnam_1995_a3/astra_max_original.lean) ·
[Commands](cases/15_putnam_1995_a3/astra_max_original_trace.json)

## 6. A case where cleanup does help

`CallElimCorrect.substOldPostSubset`: the original-arm model factors repeated
subset reasoning into `join`, reducing **313 → 223 tokens** and
**5,175.792 → 1,786.680 heartbeats**, for 64.744686%.

The independent D0-seeded model also introduces `join` and reaches 192 tokens
and 70.836929%. Cleanup reduces it to 143 tokens and **74.487866%**, a real
within-proposal gain of **3.650937 points**. This one case supplies 0.243396
points of the 15-problem mean, much of Astra's total 0.331848-point cleanup gain.
Deterministic cleanup has a useful role; the result measures how small its
aggregate contribution is after this model's stronger structural rewrites.

[Original-arm proof](cases/01_substOldPostSubset/astra_max_original.lean) ·
[Seeded model proof](cases/01_substOldPostSubset/astra_max_deterministic_model.lean) ·
[After cleanup](cases/01_substOldPostSubset/astra_max_deterministic.lean)

## Remaining mechanisms

These entries complete the 15-problem review. Links go to the Astra/max
original-arm declaration; each folder also contains the original, all model
comparators, diffs and visible command/check traces.

| Case | Tokens, original → Astra | Heartbeats, original → Astra | Main visible change |
| --- | ---: | ---: | --- |
| [Electric-field derivative](cases/05_time_deriv_time_deriv_electricField_of_isExtrema/astra_max_original.lean) | 1,372 → 568 | 26,982.141 → 10,238.661 | Share differentiability facts and the Gauss derivative identity; use directed rewrites and finish the algebra locally. |
| [Wick time ordering](cases/06_timeOrderF_superCommuteF_eq_time/astra_max_original.lean) | 1,217 → 768 | 42,058.327 → 14,817.813 | Use `Submodule.span_induction₂` and a shared sorting/factorization helper instead of repeated nested reasoning. |
| [SKI diamond](cases/08_parallelReduction_diamond/astra_max_original.lean) | 407 → 370 | 1,384.048 → 383.817 | Supply reduction witnesses and constructors explicitly; reuse irreducibility lemmas. |
| [CCS choice](cases/09_bisimilarity_congr_choice/astra_max_original.lean) | 251 → 176 | 3,859.535 → 385.743 | Reuse `.follow_fst`/`.follow_snd` with direct transition witnesses instead of manually unpacking and rebuilding bisimilarity. |
| [Fiberwise distance](cases/10_fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius/astra_max_original.lean) | 1,463 → 463 | 15,652.051 → 5,665.882 | Use a minimum disagreement witness and `Finset.card_biUnion_le_card_mul` to bound the union of fibers. |
| [Polynomial fold](cases/11_fold_advances_evaluation_poly/astra_max_original.lean) | 1,906 → 395 | 45,273.569 → 8,905.705 | Factor quotient/fiber identities and a reusable evaluation lemma; apply `evaluation_poly_split_identity` before local ring algebra. |
| [Affine/tensor gaps](cases/12_interleaved_affine_gaps_imply_tensor_gaps/astra_max_original.lean) | 1,353 → 273 | 9,205.314 → 3,128.107 | Streamline dimension induction; compose existing probability-splitting and correlated-agreement lemmas. |
| [Putnam 1964 A4](cases/13_putnam_1964_a4/astra_max_original.lean) | 1,769 → 316 | 141,103.125 → 3,031.809 | Encode recurrence states in `Fin 4 → Set.Icc B T`, apply finite pigeonhole, then strong induction with a shared predecessor helper. |
| [Putnam 1964 B2](cases/14_putnam_1964_b2/astra_max_original.lean) | 1,754 → 237 | 120,503.141 → 933.175 | Use complement membership and a complement bijection with `Finset.card_bijective` and `card_add_card_compl`. |

The reusable strategy is to identify the invariant, representation or library
fact that lets a large portion of the original proof disappear. Whether a
particular replacement saves tokens, heartbeats, both or neither must still be
measured on the actual declaration and pinned versions.
