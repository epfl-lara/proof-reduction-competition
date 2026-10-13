lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  let q := [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF
  let m := @mulLinearMap 𝓕
  refine LinearMap.congr_fun₂
    (f := (m.compr₂ (ι.toLinearMap.comp timeOrderF)).comp (m.flip q))
    (g := m.compr₂ ((ι.toLinearMap.comp (m q)).comp timeOrderF))
    (LinearMap.ext_basis ofCrAnListFBasis ofCrAnListFBasis fun φs' φs => ?_) a b
  dsimp only [m, q, LinearMap.compr₂_apply, LinearMap.comp_apply, LinearMap.flip_apply,
    mulLinearMap_apply, AlgHom.toLinearMap_apply]
  simp only [ofListBasis_eq_ofList]
  let t := (φs' ++ φs).insertionSort crAnTimeOrderRel
  let e := fun c => crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ
  let l1 := List.takeWhile (fun c => ¬ crAnTimeOrderRel φ c)
      t ++
    List.filter e φs'
  let l2 := List.filter e φs ++
    List.filter (fun c => crAnTimeOrderRel φ c ∧ ¬ crAnTimeOrderRel c φ)
      t
  have ht (l)
      (h : ∀ c ∈ l, e c) :
      𝓣ᶠ(ofCrAnListF (φs' ++ l ++ φs)) =
      crAnTimeOrderSign (φs' ++ l ++ φs) •
        ofCrAnListF (l1 ++ l ++ l2) := by
    rw [timeOrderF_ofCrAnListF, crAnTimeOrderList,
      insertionSort_of_eq_list _ φ φs' l φs h]
    simp only [l1, l2, t, e, List.append_assoc]
  trans ι (crAnTimeOrderSign (φs' ++ [φ, ψ] ++ φs) •
    (ofCrAnListF l1 * q * ofCrAnListF l2))
  · apply congrArg ι
    simp only [q, ← ofCrAnListF_singleton, superCommuteF_ofCrAnListF_ofCrAnListF,
      List.singleton_append, ofList_singleton, mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc,
      ← ofCrAnListF_append, map_sub, map_smul]
    rw [ht [φ, ψ] (by simp [e, hφψ, hψφ]), ht [ψ, φ] (by simp [e, hφψ, hψφ])]
    simp only [List.append_assoc, List.cons_append, List.nil_append]
    rw [crAnTimeOrderSign_swap_eq_time hφψ hψφ, smul_sub, smul_comm]
  · have ht0 := ht [] (by simp)
    simp only [List.append_nil, List.nil_append] at ht0
    simp only [map_smul, map_mul (@ι 𝓕)]
    rw [Subalgebra.mem_center_iff.mp
      (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ), mul_assoc,
      ← ofCrAnListF_append, ht0, map_smul]
    by_cases hq : 𝓕.crAnStatistics ψ = 𝓕.crAnStatistics φ
    · simp only [List.append_assoc, List.cons_append, List.nil_append, crAnTimeOrderSign,
        Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ hq,
        Algebra.mul_smul_comm, ofCrAnListF_append, map_mul]
    · simp only [ι_superCommuteF_of_diff_statistic (Ne.symm hq), zero_mul, smul_zero]