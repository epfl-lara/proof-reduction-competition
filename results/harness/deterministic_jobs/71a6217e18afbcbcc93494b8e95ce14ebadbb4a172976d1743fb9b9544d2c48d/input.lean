theorem interleaved_affine_gaps_imply_tensor_gaps
    (hC_proximityGapAffineLines : e_ε_correlatedAgreementAffineLinesNat
      (F := F) (A := A) (ι := ι) (C := MC) (e := e) (ε := ε))
    (h_interleaved_gaps : ∀ m : ℕ, m ≥ 1 →
      e_ε_correlatedAgreementAffineLinesNat (F := F)
        (A := InterleavedSymbol A (Fin m)) (ι := ι) (C := MC ^⋈ (Fin m)) e ε) :
    ∀ (ϑ : ℕ), (hϑ_gt_0 : ϑ > 0) → δ_ε_multilinearCorrelatedAgreement_Nat (F := F) (A := A)
      (ι := ι) (C := MC) (ϑ := ϑ) (e := e) (ε := ε) := by
  apply Nat.le_induction
  · intro u hp
    have hu : finMapTwoWords (u 0) (u 1) = u := by
      funext i
      match i with
      | 0 => rfl
      | 1 => rfl
    rw [← hu]
    apply hC_proximityGapAffineLines (u 0) (u 1)
    rw [← prob_uniform_singleton_finFun_eq (F := F)]
    simp only [multilinearCombine₁_eq_affineLineEvaluation (F := F) u,
      Nat.cast_one, ENNReal.coe_one, one_mul] at hp
    assumption
  · intro n hn ih u hp
    apply CA_split_rowwise_implies_CA (C := (MC : Set (Word A ι))) u e
    apply h_interleaved_gaps (2 ^ n) Nat.one_le_two_pow
    refine lt_of_lt_of_le (prob_R_star_gt_threshold MC u e ?_) ?_
    · rw [← prob_split_last_uniform_sampling_of_finFun (F := F) (ϑ := n)]
      simp only [multilinearCombine_recursive_form (F := F) u] at hp
      assumption
    · exact Pr_le_Pr_of_implies _ _ _ fun r hr =>
        correlatedAgreement_of_mem_R_star_tensor MC ih u ⟨r, hr⟩