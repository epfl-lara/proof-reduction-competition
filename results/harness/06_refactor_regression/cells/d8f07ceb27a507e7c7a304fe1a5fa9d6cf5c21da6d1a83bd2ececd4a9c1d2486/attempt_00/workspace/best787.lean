lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  let c := [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF
  let f := (mulLinearMap.comp (LinearMap.mulRight ℂ c)).compr₂
    (ι.toLinearMap ∘ₗ timeOrderF)
  let g := mulLinearMap.compr₂
    (ι.toLinearMap ∘ₗ LinearMap.mulLeft ℂ c ∘ₗ timeOrderF)
  change f a b = g a b
  suffices h : f = g from LinearMap.congr_fun₂ h a b
  refine ofCrAnListFBasis.ext fun xs => ofCrAnListFBasis.ext fun ys => ?_
  simp only [f, g, c, LinearMap.compr₂_apply, LinearMap.comp_apply,
    mulLinearMap_apply, LinearMap.mulRight_apply, LinearMap.mulLeft_apply,
    AlgHom.toLinearMap_apply, ofListBasis_eq_ofList]
  let s := (xs ++ ys).insertionSort crAnTimeOrderRel
  let p := fun z => crAnTimeOrderRel φ z ∧ crAnTimeOrderRel z φ
  let l1 := ι (ofCrAnListF (List.takeWhile (fun c => ¬ crAnTimeOrderRel φ c)
      s ++
    List.filter p xs))
  let l2 := ι (ofCrAnListF (List.filter p ys ++
    List.filter (fun c => crAnTimeOrderRel φ c ∧ ¬ crAnTimeOrderRel c φ)
      s))
  have hs (l : List 𝓕.CrAnFieldOp) (hl : ∀ c ∈ l, p c) :
      ι (ofCrAnListF (crAnTimeOrderList (xs ++ l ++ ys))) =
      l1 * ι (ofCrAnListF l) * l2 := by
    rw [crAnTimeOrderList, insertionSort_of_eq_list _ φ xs l ys hl]
    simp only [l1, l2, s, p, ofCrAnListF_append, map_mul, mul_assoc]
  trans crAnTimeOrderSign (xs ++ φ :: ψ :: ys) •
    (l1 * ι c * l2)
  · simp only [c, superCommuteF_ofCrAnListF_ofCrAnListF, ofList_singleton,
      mul_sub, sub_mul, Algebra.smul_mul_assoc, Algebra.mul_smul_comm,
      map_sub, map_smul, ← ofCrAnListF_singleton, ← ofCrAnListF_append,
      List.cons_append, List.nil_append,
      timeOrderF_ofCrAnListF]
    rw [hs [φ, ψ] (by simp [p, hφψ, hψφ]), hs [ψ, φ] (by simp [p, hφψ, hψφ])]
    simp only [List.append_assoc, List.cons_append, List.nil_append]
    rw [← crAnTimeOrderSign_swap_eq_time hφψ hψφ]
    rw [smul_sub, smul_comm]
  have h0 := hs [] (by simp)
  simp only [List.append_nil, ofCrAnListF_nil, map_one, mul_one] at h0
  rw [Subalgebra.mem_center_iff.mp
    (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ), mul_assoc, ← h0]
  by_cases hq : (𝓕 |>ₛ φ) ≠ (𝓕 |>ₛ ψ)
  · simp only [map_mul, ι_superCommuteF_of_diff_statistic hq, zero_mul, smul_zero]
  · rw [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ
      (not_ne_iff.mp hq).symm, ← crAnTimeOrderSign]
    simp only [map_mul, ← ofCrAnListF_append, timeOrderF_ofCrAnListF, map_smul,
      Algebra.mul_smul_comm]
