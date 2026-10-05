lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  let c := [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF
  change ((mulLinearMap ∘ₗ mulLinearMap.flip c).compr₂
      (ι.toLinearMap ∘ₗ timeOrderF)) a b =
    (mulLinearMap.compr₂ (ι.toLinearMap ∘ₗ mulLinearMap c ∘ₗ timeOrderF)) a b
  refine LinearMap.congr_fun₂
    (LinearMap.ext_basis ofCrAnListFBasis ofCrAnListFBasis fun φs' φs => ?_) a b
  change ι 𝓣ᶠ(ofCrAnListFBasis φs' * c * ofCrAnListFBasis φs) =
    ι (c * 𝓣ᶠ(ofCrAnListFBasis φs' * ofCrAnListFBasis φs))
  simp only [ofListBasis_eq_ofList, map_mul]
  obtain ⟨x, y, hs⟩ : ∃ x y : 𝓕.WickAlgebra, ∀ l,
      (∀ z ∈ l, crAnTimeOrderRel φ z ∧ crAnTimeOrderRel z φ) →
      ι 𝓣ᶠ(ofCrAnListF (φs' ++ l ++ φs)) =
        crAnTimeOrderSign (φs' ++ l ++ φs) • (x * ι (ofCrAnListF l) * y) := by
    refine ⟨
      ι (ofCrAnListF (List.takeWhile (fun z => ¬ crAnTimeOrderRel φ z)
        (crAnTimeOrderList (φs' ++ φs)) ++
        List.filter (fun z => crAnTimeOrderRel φ z ∧ crAnTimeOrderRel z φ) φs')),
      ι (ofCrAnListF (List.filter (fun z => crAnTimeOrderRel φ z ∧ crAnTimeOrderRel z φ) φs ++
        List.filter (fun z => crAnTimeOrderRel φ z ∧ ¬ crAnTimeOrderRel z φ)
          (crAnTimeOrderList (φs' ++ φs)))), fun l h => ?_⟩
    rw [timeOrderF_ofCrAnListF, map_smul, crAnTimeOrderList,
      insertionSort_of_eq_list 𝓕.crAnTimeOrderRel φ φs' l φs h]
    simp only [ofCrAnListF_append, map_mul, mul_assoc]
    rfl
  have h12 := hs [φ, ψ] (by simp [hφψ, hψφ])
  have h21 := hs [ψ, φ] (by simp [hφψ, hψφ])
  have h0 := hs [] (by simp)
  simp only [List.append_nil, ofCrAnListF_nil, map_one, mul_one] at h0
  have hc := superCommuteF_ofCrAnListF_ofCrAnListF [φ] [ψ]
  simp only [ofCrAnListF_singleton, List.singleton_append] at hc
  trans crAnTimeOrderSign (φs' ++ [φ, ψ] ++ φs) •
    (x * ι c * y)
  all_goals dsimp only [c]
  · conv_lhs =>
      rw [hc]
      simp only [mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc,
        ← ofCrAnListF_append, map_sub, map_smul, h12, h21]
    simp only [hc, map_sub, map_smul,
      mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc, smul_sub]
    simp only [List.append_assoc, List.cons_append,
      crAnTimeOrderSign_swap_eq_time hφψ hψφ]
    rw [smul_comm]
  · rw [Subalgebra.mem_center_iff.mp (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ),
      mul_assoc]
    simp only [List.append_assoc, List.cons_append, List.nil_append]
    by_cases hq : (𝓕 |>ₛ φ) = (𝓕 |>ₛ ψ)
    · rw [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ hq.symm,
        ← crAnTimeOrderSign, ← ofCrAnListF_append, h0]
      simp only [Algebra.mul_smul_comm]
    · simp only [ι_superCommuteF_of_diff_statistic hq, zero_mul, smul_zero]