lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  refine Submodule.span_induction₂
    (p := fun a b _ _ => ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
      ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)))
    ?_ ?_ ?_ ?_ ?_ ?_ ?_ (Basis.mem_span ofCrAnListFBasis a)
      (Basis.mem_span ofCrAnListFBasis b)
  · rintro _ _ ⟨s, rfl⟩ ⟨t, rfl⟩
    simp only [ofListBasis_eq_ofList]
    let l1 := List.takeWhile (fun c => ¬ crAnTimeOrderRel φ c)
      ((s ++ t).insertionSort crAnTimeOrderRel) ++
      List.filter (fun c => crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) s
    let l2 := List.filter (fun c => crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ) t ++
      List.filter (fun c => crAnTimeOrderRel φ c ∧ ¬ crAnTimeOrderRel c φ)
        ((s ++ t).insertionSort crAnTimeOrderRel)
    have ht (x y : 𝓕.CrAnFieldOp) (hx : crAnTimeOrderRel φ x ∧ crAnTimeOrderRel x φ)
        (hy : crAnTimeOrderRel φ y ∧ crAnTimeOrderRel y φ) :
        ι 𝓣ᶠ(ofCrAnListF (s ++ x :: y :: t)) = crAnTimeOrderSign (s ++ x :: y :: t) •
          (ι (ofCrAnListF l1) * ι (ofCrAnListF [x, y]) * ι (ofCrAnListF l2)) := by
      rw [timeOrderF_ofCrAnListF, crAnTimeOrderList,
        show s ++ x :: y :: t = s ++ [x, y] ++ t by simp,
        insertionSort_of_eq_list crAnTimeOrderRel φ s [x, y] t (by simpa using And.intro hx hy)]
      simp only [map_smul, ofCrAnListF_append, map_mul, l1, l2, mul_assoc]
    have hc : ι (ofCrAnListF [φ, ψ]) - 𝓢(𝓕.crAnStatistics φ, 𝓕.crAnStatistics ψ) •
        ι (ofCrAnListF [ψ, φ]) = ι [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF := by
      rw [superCommuteF_ofCrAnOpF_ofCrAnOpF, ← ofCrAnListF_singleton,
        ← ofCrAnListF_singleton]
      simp only [← ofCrAnListF_append, List.cons_append, List.nil_append, Algebra.smul_mul_assoc, map_sub, map_smul]
    have hs : ι 𝓣ᶠ(ofCrAnListF s * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * ofCrAnListF t) =
        crAnTimeOrderSign (s ++ φ :: ψ :: t) •
          (ι (ofCrAnListF l1) * ι [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * ι (ofCrAnListF l2)) := by
      rw [superCommuteF_ofCrAnOpF_ofCrAnOpF, ← ofCrAnListF_singleton,
        ← ofCrAnListF_singleton]
      simp only [mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc,
        ← ofCrAnListF_append, List.cons_append, List.nil_append, List.append_assoc,
        map_sub, map_smul]
      rw [ht φ ψ (by simp) ⟨hφψ, hψφ⟩, ht ψ φ ⟨hφψ, hψφ⟩ (by simp)]
      rw [← crAnTimeOrderSign_swap_eq_time hφψ hψφ]
      simp only [← hc, mul_sub, sub_mul, Algebra.mul_smul_comm, Algebra.smul_mul_assoc,
        smul_sub]
      rw [smul_comm]
    rw [hs, Subalgebra.mem_center_iff.mp (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ),
      mul_assoc, ← map_mul, ← ofCrAnListF_append]
    have hl : l1 ++ l2 = crAnTimeOrderList (s ++ t) := by
      simpa only [l1, l2, List.append_assoc, crAnTimeOrderList] using
        (insertionSort_of_takeWhile_filter crAnTimeOrderRel φ s t).symm
    rw [hl]
    by_cases hq : 𝓕.crAnStatistics ψ = 𝓕.crAnStatistics φ
    · rw [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ hq,
        ← crAnTimeOrderSign, ← ofCrAnListF_append, timeOrderF_ofCrAnListF]
      simp only [map_mul, map_smul, Algebra.mul_smul_comm]
    · simp only [ι_superCommuteF_of_diff_statistic (Ne.symm hq), zero_mul, smul_zero, map_mul]
  · intro y hy
    simp only [zero_mul, map_zero, mul_zero, map_mul]
  · intro x hx
    simp only [mul_zero, map_zero, map_mul]
  · intro x y z hx hy hz h1 h2
    simp only [add_mul, map_add, mul_add, h1, h2]
  · intro x y z hx hy hz h1 h2
    simp only [mul_add, map_add, h1, h2]
  · intro r x y hx hy h
    simp only [Algebra.smul_mul_assoc, map_smul, Algebra.mul_smul_comm, h]
  · intro r x y hx hy h
    simp only [Algebra.mul_smul_comm, map_smul, h]
