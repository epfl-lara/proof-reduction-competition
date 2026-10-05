lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  let c := [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF
  let T := ι.toLinearMap ∘ₗ timeOrderF (𝓕 := 𝓕)
  let U := ι.toLinearMap ∘ₗ mulLinearMap c ∘ₗ timeOrderF
  change ((mulLinearMap.comp (mulLinearMap.flip c)).compr₂ T) a b =
    (mulLinearMap.compr₂ U) a b
  refine LinearMap.congr_fun₂ (ofCrAnListFBasis.ext fun φs' ↦
    ofCrAnListFBasis.ext fun φs ↦ ?_) a b
  change ι 𝓣ᶠ(ofCrAnListFBasis φs' * c * ofCrAnListFBasis φs) =
    ι (c * 𝓣ᶠ(ofCrAnListFBasis φs' * ofCrAnListFBasis φs))
  simp only [ofListBasis_eq_ofList]
  let l1 := List.takeWhile (fun x => ¬ crAnTimeOrderRel φ x)
      ((φs' ++ φs).insertionSort crAnTimeOrderRel) ++
    List.filter (fun x => crAnTimeOrderRel φ x ∧ crAnTimeOrderRel x φ) φs'
  let l2 := List.filter (fun x => crAnTimeOrderRel φ x ∧ crAnTimeOrderRel x φ) φs ++
    List.filter (fun x => crAnTimeOrderRel φ x ∧ ¬ crAnTimeOrderRel x φ)
      ((φs' ++ φs).insertionSort crAnTimeOrderRel)
  have split (l : List 𝓕.CrAnFieldOp)
      (h : ∀ x ∈ l, crAnTimeOrderRel φ x ∧ crAnTimeOrderRel x φ) :
      ofCrAnListF (crAnTimeOrderList (φs' ++ l ++ φs)) =
        ofCrAnListF l1 * ofCrAnListF l * ofCrAnListF l2 := by
    rw [crAnTimeOrderList, insertionSort_of_eq_list _ φ _ _ _ h]
    simp only [l1, l2, ofCrAnListF_append, mul_assoc]
  have hc : c = ofCrAnListF [φ, ψ] -
      𝓢(𝓕.crAnStatistics φ, 𝓕.crAnStatistics ψ) • ofCrAnListF [ψ, φ] := by
    simp only [c, superCommuteF_ofCrAnOpF_ofCrAnOpF, ofCrAnListF_cons,
      ofCrAnListF_nil, mul_one, Algebra.smul_mul_assoc]
  have ht : 𝓣ᶠ(ofCrAnListF φs' * c * ofCrAnListF φs) =
      crAnTimeOrderSign (φs' ++ φ :: ψ :: φs) •
        (ofCrAnListF l1 * c * ofCrAnListF l2) := by
    conv_lhs =>
      rw [hc]
      simp only [mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc,
        map_sub, map_smul, ← ofCrAnListF_append]
      rw [timeOrderF_ofCrAnListF, timeOrderF_ofCrAnListF,
        split [φ, ψ] (by simp [hφψ, hψφ]), split [ψ, φ] (by simp [hφψ, hψφ])]
    simp only [List.append_assoc, List.cons_append, List.nil_append]
    rw [← crAnTimeOrderSign_swap_eq_time hφψ hψφ, hc]
    simp only [mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc, smul_sub]
    rw [smul_comm]
  have h0 : ofCrAnListF (crAnTimeOrderList (φs' ++ φs)) =
      ofCrAnListF l1 * ofCrAnListF l2 := by
    simpa only [List.append_nil, ofCrAnListF_nil, mul_one] using split [] (by simp)
  rw [ht, map_smul, map_mul, map_mul,
    Subalgebra.mem_center_iff.mp (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ),
    mul_assoc, ← map_mul, ← h0, map_mul, ← ofCrAnListF_append, timeOrderF_ofCrAnListF,
    map_smul]
  by_cases hq : (𝓕 |>ₛ ψ) = (𝓕 |>ₛ φ)
  · rw [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ hq]
    exact (Algebra.mul_smul_comm _ _ _).symm
  · simp only [c, ι_superCommuteF_of_diff_statistic (Ne.symm hq), zero_mul, smul_zero]
