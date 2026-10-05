lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  induction (Basis.mem_span ofCrAnListFBasis b) using Submodule.span_induction
  · rename_i x hx
    obtain ⟨φs, rfl⟩ := hx
    simp only [ofListBasis_eq_ofList]
    induction (Basis.mem_span ofCrAnListFBasis a) using Submodule.span_induction
    · rename_i x hx
      obtain ⟨φs', rfl⟩ := hx
      simp only [ofListBasis_eq_ofList, map_mul]
      calc _
        /- Split the commutator. -/
        _ = crAnTimeOrderSign (φs' ++ φ :: ψ :: φs) •
          ι (ofCrAnListF (crAnTimeOrderList (φs' ++ φ :: ψ :: φs))) -
            crAnTimeOrderSign (φs' ++ ψ :: φ :: φs) •
          𝓢(𝓕.crAnStatistics φ, 𝓕.crAnStatistics ψ) •
            ι (ofCrAnListF (crAnTimeOrderList (φs' ++ ψ :: φ :: φs))) := by
          conv_lhs =>
            rw [← ofCrAnListF_singleton, ← ofCrAnListF_singleton,
              superCommuteF_ofCrAnListF_ofCrAnListF]
            simp [mul_sub, sub_mul, ← ofCrAnListF_append]
            rw [timeOrderF_ofCrAnListF, timeOrderF_ofCrAnListF]
          simp only [map_smul, sub_right_inj]
          module
        /- Simplify the signs. -/
        _ = crAnTimeOrderSign (φs' ++ φ :: ψ :: φs) •
          (ι (ofCrAnListF (crAnTimeOrderList (φs' ++ φ :: ψ :: φs))) -
          𝓢(𝓕.crAnStatistics φ, 𝓕.crAnStatistics ψ) •
            ι (ofCrAnListF (crAnTimeOrderList (φs' ++ ψ :: φ :: φs)))) := by
          rw [crAnTimeOrderSign_swap_eq_time hφψ hψφ]
          module
        /- Splitting the time-ordered lists. -/
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
            (by simp_all)
          rw [crAnTimeOrderList, show φs' ++ φ :: ψ :: φs = φs' ++ [φ, ψ] ++ φs by simp, h1]
          have h2 := insertionSort_of_eq_list 𝓕.crAnTimeOrderRel φ φs' [ψ, φ] φs
            (by simp_all)
          rw [crAnTimeOrderList, show φs' ++ ψ :: φ :: φs = φs' ++ [ψ, φ] ++ φs by norm_num, h2]
          repeat rw [ofCrAnListF_append]
          simp only [map_mul]
          rw [superCommuteF_ofCrAnOpF_ofCrAnOpF, ← ofCrAnListF_singleton,
              ← ofCrAnListF_singleton]
          simp only [← ofCrAnListF_append, List.cons_append, List.nil_append, Algebra.smul_mul_assoc, map_sub, map_smul, mul_sub, sub_mul, Algebra.mul_smul_comm]
      rw [Subalgebra.mem_center_iff.mp (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ)]
      repeat rw [mul_assoc]
      rw [← map_mul, ← map_mul, ← map_mul, ← ofCrAnListF_append, ← ofCrAnListF_append,
        ← ofCrAnListF_append]
      have h1 := insertionSort_of_takeWhile_filter 𝓕.crAnTimeOrderRel φ φs' φs
      simp only [ List.append_assoc, List.cons_append, List.nil_append] at h1 ⊢
      rw [← h1, ← crAnTimeOrderList]
      by_cases hq : (𝓕 |>ₛ φ) ≠ (𝓕 |>ₛ ψ)
      · simp only [ι_superCommuteF_of_diff_statistic hq, zero_mul, smul_zero]
      · rw [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ (not_ne_iff.mp hq).symm,
          ← crAnTimeOrderSign, ← ofCrAnListF_append, timeOrderF_ofCrAnListF]
        simp only [map_smul, Algebra.mul_smul_comm]
    · simp
    · rename_i x y hx hy hpx hpy
      simp_all only [map_mul, add_mul, map_add, mul_add]
    · rename_i c x hx hpx
      simp_all only [map_mul, Algebra.smul_mul_assoc, map_smul, Algebra.mul_smul_comm]
  · norm_num
  · rename_i x y hx hy hpx hpy
    simp_all only [ mul_add, map_add]
  · rename_i c x hx hpx
    simp_all only [ Algebra.mul_smul_comm, map_smul]