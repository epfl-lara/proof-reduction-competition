lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  let c := [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF
  have h : (mulLinearMap ∘ₗ mulLinearMap.flip c).compr₂ (ι.toLinearMap ∘ₗ timeOrderF) =
      mulLinearMap.compr₂ (ι.toLinearMap ∘ₗ mulLinearMap c ∘ₗ timeOrderF) := by
    apply LinearMap.ext_basis ofCrAnListFBasis ofCrAnListFBasis
    intro s t
    simp only [LinearMap.compr₂_apply, LinearMap.comp_apply, LinearMap.flip_apply,
      mulLinearMap_apply, AlgHom.toLinearMap_apply, ofListBasis_eq_ofList]
    let l1 := List.takeWhile (fun c => ¬ crAnTimeOrderRel φ c)
      ((s ++ t).insertionSort crAnTimeOrderRel) ++
      List.filter (fun c => crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) s
    let l2 := List.filter (fun c => crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) t ++
      List.filter (fun c => crAnTimeOrderRel φ c ∧ ¬ crAnTimeOrderRel c φ)
        ((s ++ t).insertionSort crAnTimeOrderRel)
    have ht (l : List 𝓕.CrAnFieldOp) (hl : ∀ z ∈ l,
        crAnTimeOrderRel φ z ∧ crAnTimeOrderRel z φ) :
        crAnTimeOrderList ((s ++ l) ++ t) = (l1 ++ l) ++ l2 := by
      simpa only [crAnTimeOrderList, l1, l2, List.append_assoc] using
        insertionSort_of_eq_list crAnTimeOrderRel φ s l t hl
    have h1 := ht [φ, ψ] (by simp [hφψ, hψφ])
    have h2 := ht [ψ, φ] (by simp [hφψ, hψφ])
    have h0 := ht [] (List.forall_mem_nil _)
    simp only [List.append_assoc, List.cons_append, List.nil_append, List.append_nil] at h0 h1 h2
    trans crAnTimeOrderSign (s ++ φ :: ψ :: t) •
      (ι (ofCrAnListF l1) * ι c * ι (ofCrAnListF l2))
    · simp only [c, ← ofCrAnListF_singleton, superCommuteF_ofCrAnListF_ofCrAnListF,
        mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc,
        ← ofCrAnListF_append, List.cons_append, List.nil_append, List.append_assoc,
        map_sub, map_smul, ofList_singleton, timeOrderF_ofCrAnListF,
        h1, h2,
        ← crAnTimeOrderSign_swap_eq_time hφψ hψφ]
      simp only [ofCrAnListF_append, ofCrAnListF_cons, ofCrAnListF_nil, mul_one, mul_assoc,
        map_mul, map_one, mul_sub, sub_mul, Algebra.mul_smul_comm,
        Algebra.smul_mul_assoc, smul_sub]
      rw [smul_comm]
    · rw [Subalgebra.mem_center_iff.mp (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ),
        mul_assoc, ← map_mul, ← ofCrAnListF_append]
      rw [← h0]
      by_cases hq : 𝓕.crAnStatistics ψ = 𝓕.crAnStatistics φ
      · rw [← ofCrAnListF_append, timeOrderF_ofCrAnListF]
        simp only [c, crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ hq,
          map_mul, map_smul, Algebra.mul_smul_comm]
      · simp only [c, ι_superCommuteF_of_diff_statistic (Ne.symm hq), zero_mul, smul_zero, map_mul]
  exact DFunLike.congr_fun (DFunLike.congr_fun h a) b
