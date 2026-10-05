lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  induction Basis.mem_span ofCrAnListFBasis b using Submodule.span_induction with
  | mem x hx =>
    rcases hx with ⟨φs, rfl⟩
    simp only [ofListBasis_eq_ofList]
    induction Basis.mem_span ofCrAnListFBasis a using Submodule.span_induction with
    | mem x hx =>
      rcases hx with ⟨φs', rfl⟩
      simp only [ofListBasis_eq_ofList, map_mul]
      let l1 := (List.takeWhile (fun c => ¬ crAnTimeOrderRel φ c)
          ((φs' ++ φs).insertionSort crAnTimeOrderRel)) ++
        (List.filter (fun c => crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) φs')
      let l2 := (List.filter (fun c => crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) φs) ++
        (List.filter (fun c => crAnTimeOrderRel φ c ∧ ¬ crAnTimeOrderRel c φ)
          ((φs' ++ φs).insertionSort crAnTimeOrderRel))
      have hs (l : List 𝓕.CrAnFieldOp)
          (hl : ∀ c ∈ l, crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) :
          ι (ofCrAnListF (crAnTimeOrderList (φs' ++ l ++ φs))) =
            ι (ofCrAnListF l1) * ι (ofCrAnListF l) * ι (ofCrAnListF l2) := by
        rw [crAnTimeOrderList, insertionSort_of_eq_list _ φ _ _ _ hl]
        simp only [l1, l2, ofCrAnListF_append, map_mul, mul_assoc]
      have hs1 := hs [φ, ψ] (by simp [hφψ, hψφ])
      have hs2 := hs [ψ, φ] (by simp [hφψ, hψφ])
      simp only [List.append_assoc, List.cons_append, List.nil_append] at hs1 hs2
      trans crAnTimeOrderSign (φs' ++ φ :: ψ :: φs) •
        (ι (ofCrAnListF l1) * ι [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * ι (ofCrAnListF l2))
      · conv_lhs =>
          rw [superCommuteF_ofCrAnOpF_ofCrAnOpF, ← ofCrAnListF_singleton,
            ← ofCrAnListF_singleton]
          simp only [mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc,
            ← ofCrAnListF_append, List.append_assoc, List.cons_append, List.nil_append,
            map_sub, map_smul, timeOrderF_ofCrAnListF]
        rw [hs1, hs2, ← crAnTimeOrderSign_swap_eq_time hφψ hψφ]
        rw [superCommuteF_ofCrAnOpF_ofCrAnOpF, ← ofCrAnListF_singleton,
          ← ofCrAnListF_singleton]
        simp only [← ofCrAnListF_append, List.cons_append, List.nil_append,
          map_sub, map_smul, mul_sub, sub_mul, Algebra.mul_smul_comm,
          Algebra.smul_mul_assoc, smul_sub]
        module
      · rw [Subalgebra.mem_center_iff.mp
          (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ), mul_assoc]
        have hs0 := hs [] (by simp)
        simp only [List.append_nil, ofCrAnListF_nil, map_one, mul_one] at hs0
        rw [← hs0]
        by_cases hq : (𝓕 |>ₛ φ) ≠ (𝓕 |>ₛ ψ)
        · simp only [ι_superCommuteF_of_diff_statistic hq, zero_mul, smul_zero]
        · rw [crAnTimeOrderSign,
            Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ (not_not.mp hq).symm,
            ← crAnTimeOrderSign, ← ofCrAnListF_append, timeOrderF_ofCrAnListF]
          simp only [map_smul, Algebra.mul_smul_comm]
    | zero => simp only [zero_mul, map_zero, mul_zero]
    | add x y hx hy hpx hpy =>
      simp only [add_mul, map_add, mul_add, hpx, hpy]
    | smul r x hx hpx =>
      simp only [Algebra.smul_mul_assoc, map_smul, Algebra.mul_smul_comm, hpx]
  | zero => simp only [mul_zero, map_zero]
  | add x y hx hy hpx hpy =>
    simp only [mul_add, map_add, hpx, hpy]
  | smul r x hx hpx =>
    simp only [Algebra.mul_smul_comm, map_smul, hpx]
