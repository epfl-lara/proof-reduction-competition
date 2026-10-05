lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  induction ofCrAnListFBasis.mem_span a using Submodule.span_induction with
  | mem x h =>
    obtain ⟨φs', rfl⟩ := h
    induction ofCrAnListFBasis.mem_span b using Submodule.span_induction with
    | mem y h =>
      obtain ⟨φs, rfl⟩ := h
      obtain ⟨L1, L2, h⟩ : ∃ L1 L2, ∀ l, (∀ c ∈ l, crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) →
          crAnTimeOrderList (φs' ++ l ++ φs) = L1 ++ l ++ L2 :=
        ⟨_, _, fun l hl => (insertionSort_of_eq_list _ φ φs' l φs hl).trans (List.append_assoc _ _ _)⟩
      have h0 := h [] (by simp)
      have h1 := h [φ, ψ] (by simp [hφψ, hψφ])
      have h2 := h [ψ, φ] (by simp [hφψ, hψφ])
      simp only [List.append_assoc, List.cons_append, List.nil_append, List.append_nil] at h0 h1 h2
      have e : 𝓣ᶠ(ofCrAnListF φs' * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * ofCrAnListF φs) =
          crAnTimeOrderSign (φs' ++ φ :: ψ :: φs) •
          (ofCrAnListF L1 * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * ofCrAnListF L2) := by
        simp only [superCommuteF_ofCrAnOpF_ofCrAnOpF, mul_sub, sub_mul, smul_mul_assoc,
          mul_smul_comm, mul_assoc, ← ofCrAnListF_cons, ← ofCrAnListF_append, map_sub,
          map_smul, timeOrderF_ofCrAnListF, h1, h2]
        rw [crAnTimeOrderSign_swap_eq_time hψφ hφψ, smul_sub, smul_comm]
      rw [ofListBasis_eq_ofList, ofListBasis_eq_ofList, e, ← ofCrAnListF_append,
        timeOrderF_ofCrAnListF, h0, ofCrAnListF_append]
      simp only [map_smul, map_mul, mul_smul_comm, ← mul_assoc,
        Subalgebra.mem_center_iff.mp (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ)]
      rcases eq_or_ne (𝓕 |>ₛ φ) (𝓕 |>ₛ ψ) with hq | hq
      · simp only [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ hq.symm]
      · simp only [ι_superCommuteF_of_diff_statistic hq, zero_mul, smul_zero]
    | zero => simp only [mul_zero, map_zero]
    | add x y _ _ hx hy => simp only [mul_add, map_add, hx, hy]
    | smul c x _ hx => simp only [mul_smul_comm, map_smul, hx]
  | zero => simp only [zero_mul, map_zero, mul_zero]
  | add x y _ _ hx hy => simp only [add_mul, map_add, mul_add, hx, hy]
  | smul c x _ hx => simp only [smul_mul_assoc, map_smul, hx, mul_smul_comm]