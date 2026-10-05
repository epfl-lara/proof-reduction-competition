lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  induction (Basis.mem_span ofCrAnListFBasis a), (Basis.mem_span ofCrAnListFBasis b)
      using Submodule.span_induction₂ with
  | mem_mem a b ha hb =>
    obtain ⟨φs', rfl⟩ := ha
    obtain ⟨φs, rfl⟩ := hb
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
        smul_sub]
      rw [smul_comm]
    · rw [Subalgebra.mem_center_iff.mp
        (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ), mul_assoc]
      have h0 := hs [] (by simp)
      simp only [List.append_nil, ofCrAnListF_nil, map_one, mul_one] at h0
      rw [← h0, ← ofCrAnListF_append, timeOrderF_ofCrAnListF, map_smul]
      by_cases hq : (𝓕 |>ₛ φ) = (𝓕 |>ₛ ψ)
      · rw [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ hq.symm]
        exact (Algebra.mul_smul_comm _ _ _).symm
      · simp [ι_superCommuteF_of_diff_statistic hq]
  | zero_left => simp
  | zero_right => simp
  | add_left x y z hx hy hz hpx hpy => simp [add_mul, mul_add, hpx, hpy]
  | add_right x y z hx hy hz hpx hpy => simp [mul_add, hpx, hpy]
  | smul_left r x y hx hy hp => simpa using congrArg (r • ·) hp
  | smul_right r x y hx hy hp => simpa using congrArg (r • ·) hp
