lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  induction Basis.mem_span ofCrAnListFBasis a, Basis.mem_span ofCrAnListFBasis b
      using Submodule.span_induction₂ with
  | mem_mem x y hx hy =>
    obtain ⟨xs, rfl⟩ := hx
    obtain ⟨ys, rfl⟩ := hy
    simp only [ofListBasis_eq_ofList]
    let l1 := List.takeWhile (fun c => ¬ crAnTimeOrderRel φ c)
        ((xs ++ ys).insertionSort crAnTimeOrderRel) ++
      List.filter (fun c => crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) xs
    let l2 := List.filter (fun c => crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) ys ++
      List.filter (fun c => crAnTimeOrderRel φ c ∧ ¬ crAnTimeOrderRel c φ)
        ((xs ++ ys).insertionSort crAnTimeOrderRel)
    have hs (l : List 𝓕.CrAnFieldOp) (hl : ∀ c ∈ l,
        crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) :
        ι (ofCrAnListF (crAnTimeOrderList (xs ++ l ++ ys))) =
        ι (ofCrAnListF l1) * ι (ofCrAnListF l) * ι (ofCrAnListF l2) := by
      rw [crAnTimeOrderList, insertionSort_of_eq_list _ φ xs l ys hl]
      simp only [l1, l2, ofCrAnListF_append, map_mul, mul_assoc]
    have hcomm : [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF =
        ofCrAnListF [φ, ψ] - 𝓢(𝓕.crAnStatistics φ, 𝓕.crAnStatistics ψ) •
          ofCrAnListF [ψ, φ] := by
      rw [superCommuteF_ofCrAnOpF_ofCrAnOpF]
      simp only [ofCrAnListF_cons, ofCrAnListF_nil, mul_one, Algebra.smul_mul_assoc]
    have hc : ι 𝓣ᶠ(ofCrAnListF xs * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * ofCrAnListF ys) =
        crAnTimeOrderSign (xs ++ φ :: ψ :: ys) •
          (ι (ofCrAnListF l1) * ι [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * ι (ofCrAnListF l2)) := by
      rw [hcomm]
      simp only [mul_sub, sub_mul, Algebra.smul_mul_assoc, Algebra.mul_smul_comm,
        map_sub, map_smul, ← ofCrAnListF_append, timeOrderF_ofCrAnListF]
      rw [hs [φ, ψ] (by simp [hφψ, hψφ]), hs [ψ, φ] (by simp [hφψ, hψφ])]
      simp only [List.append_assoc, List.cons_append, List.nil_append]
      rw [← crAnTimeOrderSign_swap_eq_time hφψ hψφ]
      simp only [map_sub, map_smul, mul_sub, sub_mul, Algebra.mul_smul_comm,
        Algebra.smul_mul_assoc, smul_sub]
      rw [smul_comm]
    have hl : l1 ++ l2 = crAnTimeOrderList (xs ++ ys) := by
      simpa only [l1, l2, crAnTimeOrderList, List.append_assoc] using
        (insertionSort_of_takeWhile_filter crAnTimeOrderRel φ xs ys).symm
    rw [hc, Subalgebra.mem_center_iff.mp
      (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ), mul_assoc,
      ← map_mul, ← ofCrAnListF_append, hl]
    by_cases hq : (𝓕 |>ₛ φ) ≠ (𝓕 |>ₛ ψ)
    · simp only [map_mul, ι_superCommuteF_of_diff_statistic hq, zero_mul, smul_zero]
    · rw [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ
        (not_ne_iff.mp hq).symm, ← crAnTimeOrderSign]
      simp only [map_mul, ← ofCrAnListF_append, timeOrderF_ofCrAnListF, map_smul,
        Algebra.mul_smul_comm]
  | zero_left y hy => simp only [zero_mul, map_zero, mul_zero]
  | zero_right x hx => simp only [mul_zero, map_zero]
  | add_left x y z hx hy hz ihx ihy =>
    simp only [add_mul, mul_add, map_add, ihx, ihy]
  | add_right x y z hx hy hz ihx ihy =>
    simp only [mul_add, map_add, ihx, ihy]
  | smul_left c x y hx hy ih =>
    simp only [Algebra.smul_mul_assoc, Algebra.mul_smul_comm, map_smul, ih]
  | smul_right c x y hx hy ih =>
    simp only [Algebra.mul_smul_comm, map_smul, ih]
