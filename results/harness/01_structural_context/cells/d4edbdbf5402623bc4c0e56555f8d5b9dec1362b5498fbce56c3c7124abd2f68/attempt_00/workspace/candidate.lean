lemma ι_timeOrderF_superCommuteF_eq_time {φ ψ : 𝓕.CrAnFieldOp}
    (hφψ : crAnTimeOrderRel φ ψ) (hψφ : crAnTimeOrderRel ψ φ) (a b : 𝓕.FieldOpFreeAlgebra) :
    ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b)) := by
  let leftMul : 𝓕.WickAlgebra →ₗ[ℂ] 𝓕.WickAlgebra := {
    toFun := fun x => ι [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * x
    map_add' := fun x y => by simp [mul_add]
    map_smul' := fun c x => by simp [smul_mul_assoc]
  }
  let pb (b : 𝓕.FieldOpFreeAlgebra) (hc : b ∈ Submodule.span ℂ (Set.range ofCrAnListFBasis)) :
    Prop := ι 𝓣ᶠ(a * [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * b) =
    ι ([ofCrAnOpF φ, ofCrAnOpF ψ]ₛF * 𝓣ᶠ(a * b))
  change pb b (Basis.mem_span _ b)
  apply Submodule.span_induction
  · rintro x ⟨φs, rfl⟩
    simp only [ofListBasis_eq_ofList, map_mul, pb]
    let pa (b : 𝓕.FieldOpFreeAlgebra) : 𝓕.FieldOpFreeAlgebra →ₗ[ℂ] 𝓕.WickAlgebra :=
      ι.toLinearMap.comp (timeOrderF.comp
        ((mulLinearMap.flip b).comp (mulLinearMap.flip [ofCrAnOpF φ, ofCrAnOpF ψ]ₛF)))
    let qa (b : 𝓕.FieldOpFreeAlgebra) : 𝓕.FieldOpFreeAlgebra →ₗ[ℂ] 𝓕.WickAlgebra :=
      leftMul.comp (ι.toLinearMap.comp
        (timeOrderF.comp (mulLinearMap.flip b)))
    change pa (ofCrAnListF φs) a = qa (ofCrAnListF φs) a
    refine LinearMap.congr_fun (ofCrAnListFBasis.ext fun φs' => ?_) a
    simp only [pa, qa, LinearMap.coe_comp, Function.comp_apply, LinearMap.flip_apply,
      mulLinearMap, LinearMap.coe_mk, AddHom.coe_mk, ofListBasis_eq_ofList]
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
            ι (ofCrAnListF (List.filter (fun c =>
              (crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ)) φs')) *
            ι (ofCrAnListF [φ, ψ]) *
            ι (ofCrAnListF (List.filter (fun c =>
              (crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ)) φs)) *
            ι (ofCrAnListF (List.filter (fun c => (crAnTimeOrderRel φ c ∧ ¬crAnTimeOrderRel c φ))
              (List.insertionSort crAnTimeOrderRel (φs' ++ φs)))) -
        𝓢(𝓕.crAnStatistics φ, 𝓕.crAnStatistics ψ) •
        ι (ofCrAnListF (List.takeWhile (fun c => ¬crAnTimeOrderRel φ c)
                    (List.insertionSort crAnTimeOrderRel (φs' ++ φs)))) *
            ι (ofCrAnListF (List.filter (fun c =>
              (crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ)) φs')) *
            ι (ofCrAnListF [ψ, φ]) *
            ι (ofCrAnListF (List.filter (fun c =>
              (crAnTimeOrderRel φ c ∧ crAnTimeOrderRel c φ)) φs)) *
            ι (ofCrAnListF
            (List.filter (fun c => decide (crAnTimeOrderRel φ c ∧ ¬crAnTimeOrderRel c φ))
              (List.insertionSort crAnTimeOrderRel (φs' ++ φs))))) := by
        have h1 := insertionSort_of_eq_list 𝓕.crAnTimeOrderRel φ φs' [φ, ψ] φs
          (by simp_all)
        rw [crAnTimeOrderList, show φs' ++ φ :: ψ :: φs = φs' ++ [φ, ψ] ++ φs by simp, h1]
        have h2 := insertionSort_of_eq_list 𝓕.crAnTimeOrderRel φ φs' [ψ, φ] φs
          (by simp_all)
        rw [crAnTimeOrderList, show φs' ++ ψ :: φ :: φs = φs' ++ [ψ, φ] ++ φs by simp, h2]
        repeat rw [ofCrAnListF_append]
        simp
      _ = crAnTimeOrderSign (φs' ++ [φ, ψ] ++ φs) •
          (ι (ofCrAnListF (List.takeWhile (fun c => ¬crAnTimeOrderRel φ c)
              (List.insertionSort crAnTimeOrderRel (φs' ++ φs)))) *
            ι (ofCrAnListF (List.filter (fun c => (crAnTimeOrderRel φ c ∧
              crAnTimeOrderRel c φ)) φs')) *
            (ι (ofCrAnListF [φ, ψ]) - 𝓢(𝓕.crAnStatistics φ, 𝓕.crAnStatistics ψ) •
              ι (ofCrAnListF [ψ, φ])) *
            ι (ofCrAnListF (List.filter (fun c => (crAnTimeOrderRel φ c ∧
              crAnTimeOrderRel c φ)) φs)) *
            ι (ofCrAnListF (List.filter (fun c => (crAnTimeOrderRel φ c ∧ ¬crAnTimeOrderRel c φ))
              (List.insertionSort crAnTimeOrderRel (φs' ++ φs))))) := by
          simp [mul_sub, sub_mul]
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
          congr
          rw [superCommuteF_ofCrAnOpF_ofCrAnOpF, ← ofCrAnListF_singleton,
            ← ofCrAnListF_singleton]
          simp [← ofCrAnListF_append]
    rw [Subalgebra.mem_center_iff.mp (ι_superCommuteF_ofCrAnOpF_ofCrAnOpF_mem_center φ ψ)]
    repeat rw [mul_assoc]
    rw [← map_mul, ← map_mul, ← map_mul, ← ofCrAnListF_append, ← ofCrAnListF_append,
      ← ofCrAnListF_append]
    have h1 := insertionSort_of_takeWhile_filter 𝓕.crAnTimeOrderRel φ φs' φs
    simp [decide_not, Bool.decide_and, List.append_assoc, List.cons_append] at h1 ⊢
    rw [← h1, ← crAnTimeOrderList]
    by_cases hq : (𝓕 |>ₛ φ) ≠ (𝓕 |>ₛ ψ)
    · simp [leftMul, ι_superCommuteF_of_diff_statistic hq]
    · rw [crAnTimeOrderSign, Wick.koszulSign_eq_rel_eq_stat _ _ hφψ hψφ (by simp_all),
        ← crAnTimeOrderSign, ← ofCrAnListF_append, timeOrderF_ofCrAnListF]
      simp only [map_smul, Algebra.mul_smul_comm, leftMul, LinearMap.coe_mk, AddHom.coe_mk]

  · simp only [map_mul, mul_zero, map_zero, pb]
  · intro x y hx hy hpx hpy
    simp_all [pb,mul_add]
  · intro x hx hpx
    simp_all [pb]