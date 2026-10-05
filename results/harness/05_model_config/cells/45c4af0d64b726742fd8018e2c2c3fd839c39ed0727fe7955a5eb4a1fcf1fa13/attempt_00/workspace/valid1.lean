theorem interleaved_affine_gaps_imply_tensor_gaps
    (hC_proximityGapAffineLines : e_ε_correlatedAgreementAffineLinesNat
      (F := F) (A := A) (ι := ι) (C := MC) (e := e) (ε := ε))
    (h_interleaved_gaps : ∀ m : ℕ, m ≥ 1 →
      e_ε_correlatedAgreementAffineLinesNat (F := F)
        (A := InterleavedSymbol A (Fin m)) (ι := ι) (C := MC ^⋈ (Fin m)) e ε) :
    ∀ (ϑ : ℕ), (hϑ_gt_0 : ϑ > 0) → δ_ε_multilinearCorrelatedAgreement_Nat (F := F) (A := A)
      (ι := ι) (C := MC) (ϑ := ϑ) (e := e) (ε := ε) := by
  classical
  intro ϑ hϑ
  induction ϑ, hϑ using Nat.le_induction with
  | base =>
    intro u hp
    simp_rw [multilinearCombine₁_eq_affineLineEvaluation (u := u)] at hp
    simp_rw [prob_uniform_singleton_finFun_eq
      (P := fun r => Δ₀(affineLineEvaluation (u 0) (u 1) r, MC) ≤ e),
      Nat.cast_one, ENNReal.coe_one, one_mul] at hp
    have h := hC_proximityGapAffineLines (u 0) (u 1) hp
    have hu : finMapTwoWords (u 0) (u 1) = u := by
      funext i
      match i with
      | 0 => rfl
      | 1 => rfl
    simpa only [jointProximityNat₂, hu] using h
  | succ n hn ih =>
    intro u hp
    let U := splitHalfRowWiseInterleavedWords (ϑ := n) u
    have hs := prob_split_last_uniform_sampling_of_finFun (F := F)
      (P := fun a b => Δ₀(multilinearCombine u (Fin.snoc b a), MC) ≤ e)
    simp only [← Fin.init_def, Fin.snoc_init_self] at hs
    rw [hs] at hp
    have he (b : Fin n → F) (a : F) :
        multilinearCombine u (Fin.snoc b a) =
        multilinearCombine (affineLineEvaluation U.1 U.2 a) b := by
      rw [multilinearCombine_recursive_form]
      simp only [Fin.snoc_last, Fin.init_snoc]
      rfl
    simp_rw [he] at hp
    apply CA_split_rowwise_implies_CA (C := MC) (u := u) (e := e)
    apply h_interleaved_gaps _ Nat.one_le_two_pow (interleaveWordStack U.1) (interleaveWordStack U.2)
    apply lt_of_lt_of_le (prob_R_star_gt_threshold (MC := MC) (ε := ε) u e hp)
    apply Pr_le_Pr_of_implies
    intro r hr
    exact correlatedAgreement_of_mem_R_star_tensor (MC := MC) ih u ⟨r, hr⟩
