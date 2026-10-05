lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  let c := [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF
  change ((mulLinearMap.comp (mulLinearMap.flip c)).compr₂
    (ι.toLinearMap ∘ₗ timeOrderF)) a b =
    (mulLinearMap.compr₂ (ι.toLinearMap ∘ₗ mulLinearMap c ∘ₗ timeOrderF)) a b
  refine LinearMap.congr_fun₂ (ofCrAnListFBasis.ext fun φs' ↦
    ofCrAnListFBasis.ext fun φs ↦ ?_) a b
  simp only [LinearMap.compr₂_apply, LinearMap.comp_apply, mulLinearMap_apply,
    LinearMap.flip_apply, ofListBasis_eq_ofList, AlgHom.toLinearMap_apply]
  obtain ⟨l1, l2, split⟩ : ∃ l1 l2 : List 𝓕.CrAnFieldOp,
      ∀ (l : List 𝓕.CrAnFieldOp),
      (∀ x ∈ l, crAnTimeOrderRel φ x ∧ crAnTimeOrderRel x φ) →
      crAnTimeOrderList (φs' ++ l ++ φs) = l1 ++ l ++ l2 := by
    exact ⟨_, _, fun l h => (insertionSort_of_eq_list _ φ φs' l φs h).trans
      (List.append_assoc _ _ _)⟩
  trans ι (crAnTimeOrderSign (φs' ++ φ :: ψ :: φs) •
    (ofCrAnListF l1 * c * ofCrAnListF l2))
  · apply congrArg ι
    simp only [c, ← ofCrAnListF_singleton, superCommuteF_ofCrAnListF_ofCrAnListF,
      ofList_singleton, List.singleton_append, mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc,
      map_sub, map_smul, ← ofCrAnListF_append, timeOrderF_ofCrAnListF,
      split [φ, ψ] (by simp [hφψ, hψφ]), split [ψ, φ] (by simp [hφψ, hψφ])]
    simp only [List.append_assoc, List.cons_append, List.nil_append]
    rw [← crAnTimeOrderSign_swap_eq_time hφψ hψφ, smul_sub, smul_comm]
  have h0 := split [] (by simp)
  simp only [List.append_nil] at h0
  rw [map_smul, map_mul, map_mul,
    Subalgebra.mem_center_iff.mp (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ),
    mul_assoc, ← map_mul, ← ofCrAnListF_append, ← h0, map_mul, ← ofCrAnListF_append, timeOrderF_ofCrAnListF,
    map_smul]
  by_cases hq : (𝓕 |>ₛ ψ) = (𝓕 |>ₛ φ)
  · rw [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ hq]
    exact (Algebra.mul_smul_comm _ _ _).symm
  · simp only [c, ι_superCommuteF_of_diff_statistic (Ne.symm hq), zero_mul, smul_zero]
