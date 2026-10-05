theorem interleaved_affine_gaps_imply_tensor_gaps
    (hC_proximityGapAffineLines : e_ε_correlatedAgreementAffineLinesNat
      (F := F) (A := A) (ι := ι) (C := MC) (e := e) (ε := ε))
    (h_interleaved_gaps : ∀ m : ℕ, m ≥ 1 →
      e_ε_correlatedAgreementAffineLinesNat (F := F)
        (A := InterleavedSymbol A (Fin m)) (ι := ι) (C := MC ^⋈ (Fin m)) e ε) :
    ∀ (ϑ : ℕ), (hϑ_gt_0 : ϑ > 0) → δ_ε_multilinearCorrelatedAgreement_Nat (F := F) (A := A)
      (ι := ι) (C := MC) (ϑ := ϑ) (e := e) (ε := ε) := by
  classical
  intro ϑ
  induction ϑ with
  | zero => exact fun h => (Nat.not_lt_zero _ h).elim
  | succ n ih =>
    cases n with
    | zero =>
      simp only [zero_add, zero_lt_one, forall_const]
      intro u hp
      simp_rw [multilinearCombine₁_eq_affineLineEvaluation (u := u)] at hp
      simp_rw [prob_uniform_singleton_finFun_eq (P := fun r =>
        Δ₀(affineLineEvaluation (u 0) (u 1) r, MC) ≤ e),
        Nat.cast_one, ENNReal.coe_one, one_mul] at hp
      have hu : finMapTwoWords (u 0) (u 1) = u := by
        funext i
        match i with
        | 0 => rfl
        | 1 => rfl
      simpa only [jointProximityNat₂, hu] using hC_proximityGapAffineLines (u 0) (u 1) hp
    | succ n =>
      intro _ u hp
      simp_rw [multilinearCombine_recursive_form (u := u)] at hp
      have hs := prob_split_last_uniform_sampling_of_finFun
        (P := multilinearCombine_affineComb_split_last_close (MC := MC) u e)
      dsimp only [multilinearCombine_affineComb_split_last_close] at hs
      rw [hs] at hp
      apply CA_split_rowwise_implies_CA (C := MC) u e
      apply h_interleaved_gaps (2 ^ (n + 1)) Nat.one_le_two_pow
      apply lt_of_lt_of_le (prob_R_star_gt_threshold (MC := MC) u e hp)
      apply Pr_le_Pr_of_implies
      intro r hr
      exact correlatedAgreement_of_mem_R_star_tensor (MC := MC)
        (ih := ih (Nat.succ_pos _)) (u := u) ⟨r, hr⟩
