lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  induction (Basis.mem_span ofCrAnListFBasis a), (Basis.mem_span ofCrAnListFBasis b)
      using Submodule.span_induction₂ with
  | mem_mem x y hx hy =>
    obtain ⟨φs', rfl⟩ := hx
    obtain ⟨φs, rfl⟩ := hy
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
      simpa only [crAnTimeOrderList, l1, l2, List.append_assoc] using
        insertionSort_of_eq_list 𝓕.crAnTimeOrderRel φ φs' l φs h
    have h12 := hs [φ, ψ] (by simp [hφψ, hψφ])
    have h21 := hs [ψ, φ] (by simp [hφψ, hψφ])
    have h0 : crAnTimeOrderList (φs' ++ φs) = l1 ++ l2 := by
      simpa only [List.append_nil, List.nil_append] using hs [] (by simp)
    have hc := superCommuteF_ofCrAnListF_ofCrAnListF [φ] [ψ]
    simp only [ofCrAnListF_singleton, ofList_singleton, List.singleton_append] at hc
    trans crAnTimeOrderSign (φs' ++ [φ, ψ] ++ φs) •
      (ι (ofCrAnListF l1) * ι [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * ι (ofCrAnListF l2))
    · conv_lhs =>
        rw [hc]
        simp only [mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc,
          ← ofCrAnListF_append, map_sub, map_smul, timeOrderF_ofCrAnListF, h12, h21]
      simp only [hc, ofCrAnListF_append, map_mul, map_sub, map_smul,
        mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc, smul_sub]
      simp only [List.append_assoc, List.cons_append, List.nil_append,
        crAnTimeOrderSign_swap_eq_time hφψ hψφ, smul_comm]
    · rw [Subalgebra.mem_center_iff.mp (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ),
        mul_assoc, ← map_mul, ← ofCrAnListF_append, ← h0]
      simp only [List.append_assoc, List.cons_append, List.nil_append]
      by_cases hq : (𝓕 |>ₛ φ) ≠ (𝓕 |>ₛ ψ)
      · simp only [ι_superCommuteF_of_diff_statistic hq, zero_mul, smul_zero]
      · rw [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ
            (not_ne_iff.mp hq).symm, ← crAnTimeOrderSign,
          ← ofCrAnListF_append, timeOrderF_ofCrAnListF]
        simp only [map_smul, Algebra.mul_smul_comm]
  | _ => simp_all only [map_add, map_smul, map_zero, zero_mul, mul_zero,
      add_mul, mul_add, Algebra.smul_mul_assoc, Algebra.mul_smul_comm]
