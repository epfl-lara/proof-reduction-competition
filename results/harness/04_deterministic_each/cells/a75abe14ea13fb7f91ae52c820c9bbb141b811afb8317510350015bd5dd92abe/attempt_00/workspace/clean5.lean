lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  let c := [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF
  change ((mulLinearMap ∘ₗ mulLinearMap.flip c).compr₂
      (ι.toLinearMap ∘ₗ timeOrderF)) a b =
    (mulLinearMap.compr₂ (ι.toLinearMap ∘ₗ mulLinearMap c ∘ₗ timeOrderF)) a b
  refine LinearMap.congr_fun (LinearMap.congr_fun
    (LinearMap.ext_basis ofCrAnListFBasis ofCrAnListFBasis fun φs' φs => ?_) a) b
  change ι 𝓣ᶠ(ofCrAnListFBasis φs' * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * ofCrAnListFBasis φs) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(ofCrAnListFBasis φs' * ofCrAnListFBasis φs))
  simp only [ofListBasis_eq_ofList, map_mul]
  let l1 :=
    List.takeWhile (fun c => ¬ crAnTimeOrderRel φ c) (crAnTimeOrderList (φs' ++ φs)) ++
    List.filter (fun c => crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) φs'
  let l2 :=
    List.filter (fun c => crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) φs ++
    List.filter (fun c => crAnTimeOrderRel φ c ∧ ¬ crAnTimeOrderRel c φ)
      (crAnTimeOrderList (φs' ++ φs))
  have hs (l : List 𝓕.CrAnFieldOp) (h : ∀ c ∈ l,
      crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) :
      crAnTimeOrderList (φs' ++ l ++ φs) = l1 ++ l ++ l2 := by
    exact (insertionSort_of_eq_list 𝓕.crAnTimeOrderRel φ φs' l φs h).trans
      (List.append_assoc _ _ _)
  have h12 := hs [φ, ψ] (by simp [hφψ, hψφ])
  have h21 := hs [ψ, φ] (by simp [hφψ, hψφ])
  have h0 : crAnTimeOrderList (φs' ++ φs) = l1 ++ l2 := by
    simpa only [List.append_nil, List.nil_append] using hs [] (by simp)
  have hc := superCommuteF_ofCrAnListF_ofCrAnListF [φ] [ψ]
  simp only [ofCrAnListF_singleton, List.singleton_append] at hc
  trans crAnTimeOrderSign (φs' ++ [φ, ψ] ++ φs) •
    (ι (ofCrAnListF l1) * ι [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * ι (ofCrAnListF l2))
  · conv_lhs =>
      rw [hc]
      simp only [mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc,
        ← ofCrAnListF_append, map_sub, map_smul, timeOrderF_ofCrAnListF, h12, h21]
    simp only [hc, ofCrAnListF_append, map_mul, map_sub, map_smul,
      mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc, smul_sub]
    simp only [List.append_assoc, List.cons_append,
      crAnTimeOrderSign_swap_eq_time hφψ hψφ]
    rw [smul_comm]
  · rw [Subalgebra.mem_center_iff.mp (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ),
      mul_assoc, ← map_mul, ← ofCrAnListF_append, ← h0]
    simp only [List.append_assoc, List.cons_append, List.nil_append]
    by_cases hq : (𝓕 |>ₛ φ) ≠ (𝓕 |>ₛ ψ)
    · simp only [ι_superCommuteF_of_diff_statistic hq, zero_mul, smul_zero]
    · rw [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ
          (not_ne_iff.mp hq).symm, ← crAnTimeOrderSign,
        ← ofCrAnListF_append, timeOrderF_ofCrAnListF]
      simp only [map_smul, Algebra.mul_smul_comm]