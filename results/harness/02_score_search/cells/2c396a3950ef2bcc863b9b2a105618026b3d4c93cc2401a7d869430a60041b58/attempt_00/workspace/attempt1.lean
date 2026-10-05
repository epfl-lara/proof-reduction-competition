lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  let pb (b : 𝓕.FieldOpFreeAlgebra) (hc : b ∈ Submodule.span ℂ (Set.range ofCrAnListFBasis)) :
    Prop := ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b))
  change pb b (Basis.mem_span _ b)
  apply Submodule.span_induction
  · rintro x ⟨φs, rfl⟩
    simp only [ofListBasis_eq_ofList, map_mul, pb]
    let pa (a : 𝓕.FieldOpFreeAlgebra) (hc : a ∈ Submodule.span ℂ (Set.range ofCrAnListFBasis)) :
      Prop := ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * ofCrAnListF φs) =
      ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a* ofCrAnListF φs))
    change pa a (Basis.mem_span _ a)
    apply Submodule.span_induction
    · rintro x ⟨φs', rfl⟩
      simp only [ofListBasis_eq_ofList, map_mul, pa]
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
      have hc : [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF =
          ofCrAnListF [φ, ψ] - 𝓢(𝓕.crAnStatistics φ, 𝓕.crAnStatistics ψ) •
            ofCrAnListF [ψ, φ] := by
        simp [superCommuteF_ofCrAnOpF_ofCrAnOpF, ofCrAnListF_cons]
      trans crAnTimeOrderSign (φs' ++ φ :: ψ :: φs) •
        (ι (ofCrAnListF l1) * ι [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * ι (ofCrAnListF l2))
      · rw [hc]
        simp only [mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc,
          map_sub, map_smul, ← ofCrAnListF_append, timeOrderF_ofCrAnListF]
        rw [hs [φ, ψ] (by simp [hφψ, hψφ]), hs [ψ, φ] (by simp [hφψ, hψφ])]
        simp only [List.append_assoc, List.cons_append, List.nil_append]
        rw [crAnTimeOrderSign_swap_eq_time hφψ hψφ]
        simp only [mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc,
          smul_sub, smul_comm]
      · rw [Subalgebra.mem_center_iff.mp
          (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ), mul_assoc]
        have h0 := hs [] (by simp)
        simp only [List.append_nil, ofCrAnListF_nil, map_one, mul_one] at h0
        rw [← h0, ← ofCrAnListF_append, timeOrderF_ofCrAnListF, map_smul]
        by_cases hq : (𝓕 |>ₛ φ) = (𝓕 |>ₛ ψ)
        · rw [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ hq.symm]
          exact (Algebra.mul_smul_comm _ _ _).symm
        · simp [ι_superCommuteF_of_diff_statistic hq]
    · simp only [map_mul, zero_mul, map_zero, mul_zero, pa]
    · intro x y hx hy hpx hpy
      simp_all [pa,mul_add, add_mul]
    · intro x hx hpx
      simp_all [pa]
  · simp only [map_mul, mul_zero, map_zero, pb]
  · intro x y hx hy hpx hpy
    simp_all [pb,mul_add]
  · intro x hx hpx
    simp_all [pb]