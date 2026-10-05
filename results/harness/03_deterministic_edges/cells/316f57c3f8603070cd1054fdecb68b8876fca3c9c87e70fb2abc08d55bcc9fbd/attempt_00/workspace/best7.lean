theorem interleaved_affine_gaps_imply_tensor_gaps
    (hC_proximityGapAffineLines : e_ε_correlatedAgreementAffineLinesNat
      (F := F) (A := A) (ι := ι) (C := MC) (e := e) (ε := ε))
    (h_interleaved_gaps : ∀ m : ℕ, m ≥ 1 →
      e_ε_correlatedAgreementAffineLinesNat (F := F)
        (A := InterleavedSymbol A (Fin m)) (ι := ι) (C := MC ^⋈ (Fin m)) e ε) :
    ∀ (ϑ : ℕ), (hϑ_gt_0 : ϑ > 0) → δ_ε_multilinearCorrelatedAgreement_Nat (F := F) (A := A)
      (ι := ι) (C := MC) (ϑ := ϑ) (e := e) (ε := ε) := by
  apply Nat.le_induction
  · intro u h
    have hu : u = finMapTwoWords (u 0) (u 1) := funext fun
      | 0 => rfl
      | 1 => rfl
    rw [hu]
    apply hC_proximityGapAffineLines
    simp_rw [multilinearCombine₁_eq_affineLineEvaluation u,
      prob_uniform_singleton_finFun_eq (fun r =>
        Δ₀(affineLineEvaluation (u 0) (u 1) r, MC) ≤ e),
      Nat.cast_one, ENNReal.coe_one, one_mul] at h
    exact h
  · intro n _ ih u h
    apply CA_split_rowwise_implies_CA (u := u) (e := e)
    apply h_interleaved_gaps (2 ^ n) Nat.one_le_two_pow
    have hp := prob_R_star_gt_threshold (MC := MC) (ε := ε) u e (by
      rw [← prob_split_last_uniform_sampling_of_finFun]
      simp_rw [multilinearCombine_recursive_form u] at h
      exact h)
    refine lt_of_lt_of_le hp ?_
    apply Pr_le_Pr_of_implies
    intro r hr
    exact correlatedAgreement_of_mem_R_star_tensor (MC := MC) ih u ⟨r, hr⟩
