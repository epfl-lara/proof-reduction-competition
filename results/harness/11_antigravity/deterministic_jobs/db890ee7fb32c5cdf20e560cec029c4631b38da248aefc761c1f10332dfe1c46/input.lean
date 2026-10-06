lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  induction Basis.mem_span ofCrAnListFBasis b using Submodule.span_induction with
  | mem x hx =>
    obtain ⟨φs, rfl⟩ := hx
    rw [ofListBasis_eq_ofList]
    induction Basis.mem_span ofCrAnListFBasis a using Submodule.span_induction with
    | mem x hx =>
      obtain ⟨φs', rfl⟩ := hx
      rw [ofListBasis_eq_ofList]
      calc _
        _ = crAnTimeOrderSign (φs' ++ φ :: ψ :: φs) •
          (ι (ofCrAnListF (crAnTimeOrderList (φs' ++ φ :: ψ :: φs))) -
          𝓢(𝓕.crAnStatistics φ, 𝓕.crAnStatistics ψ) •
            ι (ofCrAnListF (crAnTimeOrderList (φs' ++ ψ :: φ :: φs)))) := by
          conv_lhs =>
            rw [← ofCrAnListF_singleton, ← ofCrAnListF_singleton,
              superCommuteF_ofCrAnListF_ofCrAnListF]
            simp [mul_sub, sub_mul, ← ofCrAnListF_append]
            rw [timeOrderF_ofCrAnListF, timeOrderF_ofCrAnListF]
          simp only [map_sub, map_smul, smul_sub, sub_right_inj]
          rw [← crAnTimeOrderSign_swap_eq_time hφψ hψφ, smul_comm]
        _ = crAnTimeOrderSign (φs' ++ [φ, ψ] ++ φs) •
            (ι (ofCrAnListF (List.takeWhile (fun c => ¬crAnTimeOrderRel φ c)
                (List.insertionSort crAnTimeOrderRel (φs' ++ φs)))) *
              ι (ofCrAnListF (List.filter (fun c => (crAnTimeOrderRel φ c ∧
                crAnTimeOrderRel c φ)) φs')) *
              ι [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF *
              ι (ofCrAnListF (List.filter (fun c => (crAnTimeOrderRel φ c ∧
                crAnTimeOrderRel c φ)) φs)) *
              ι (ofCrAnListF (List.filter (fun c => (crAnTimeOrderRel φ c ∧ ¬crAnTimeOrderRel c φ))
                (List.insertionSort crAnTimeOrderRel (φs' ++ φs))))) := by
          have h1 := insertionSort_of_eq_list 𝓕.crAnTimeOrderRel φ φs' [φ, ψ] φs
            (by simp [hφψ, hψφ])
          have h2 := insertionSort_of_eq_list 𝓕.crAnTimeOrderRel φ φs' [ψ, φ] φs
            (by simp [hφψ, hψφ])
          have hcomm : ι [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF = ι (ofCrAnListF [φ, ψ]) -
              𝓢(𝓕.crAnStatistics φ, 𝓕.crAnStatistics ψ) • ι (ofCrAnListF [ψ, φ]) := by
            rw [superCommuteF_ofCrAnOpF_ofCrAnOpF, ← ofCrAnListF_singleton, ← ofCrAnListF_singleton]
            simp only [← ofCrAnListF_append, List.cons_append, List.nil_append, Algebra.smul_mul_assoc, map_sub, map_smul]
          rw [crAnTimeOrderList, show φs' ++ φ :: ψ :: φs = φs' ++ [φ, ψ] ++ φs by simp, h1,
            crAnTimeOrderList, show φs' ++ ψ :: φ :: φs = φs' ++ [ψ, φ] ++ φs by simp, h2]
          simp only [ofCrAnListF_append, map_mul, Algebra.smul_mul_assoc]
          rw [hcomm]
          simp only [Algebra.smul_mul_assoc, mul_sub, Algebra.mul_smul_comm, sub_mul]
      rw [Subalgebra.mem_center_iff.mp (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ)]
      repeat rw [mul_assoc]
      rw [← map_mul, ← map_mul, ← map_mul, ← ofCrAnListF_append, ← ofCrAnListF_append,
        ← ofCrAnListF_append]
      have h1 := insertionSort_of_takeWhile_filter 𝓕.crAnTimeOrderRel φ φs' φs
      simp only [ List.append_assoc, List.cons_append, List.nil_append] at h1 ⊢
      rw [← h1, ← crAnTimeOrderList]
      by_cases hq : (𝓕 |>ₛ φ) ≠ (𝓕 |>ₛ ψ)
      · rw [map_mul, ι_superCommuteF_of_diff_statistic hq, zero_mul, smul_zero, zero_mul]
      · rw [map_mul, crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ (not_not.mp hq).symm,
          ← crAnTimeOrderSign, ← ofCrAnListF_append, timeOrderF_ofCrAnListF]
        simp only [map_smul, Algebra.mul_smul_comm]
    | zero => simp
    | add x y _ _ hx hy => simp only [add_mul, map_add, mul_add, hx, hy]
    | smul c x _ hx => simp only [Algebra.smul_mul_assoc, map_smul, Algebra.mul_smul_comm, hx]
  | zero => simp
  | add x y _ _ hx hy => simp only [mul_add, map_add, hx, hy]
  | smul c x _ hx => simp only [Algebra.mul_smul_comm, map_smul, hx]