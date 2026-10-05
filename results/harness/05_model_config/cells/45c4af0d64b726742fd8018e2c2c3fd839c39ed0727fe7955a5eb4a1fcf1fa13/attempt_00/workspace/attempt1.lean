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
      intro _ u hp
      simp_rw [multilinearCombine₁_eq_affineLineEvaluation,
        prob_uniform_singleton_finFun_eq] at hp
      have h := hC_proximityGapAffineLines (u 0) (u 1)
        (by simpa only [Nat.cast_one, one_mul] using hp)
      have hu : finMapTwoWords (u 0) (u 1) = u := by
        funext i
        match i with
        | 0 => rfl
        | 1 => rfl
      simpa only [jointProximityNat₂, hu] using h
    | succ n =>
      intro _ u hp
      let U := splitHalfRowWiseInterleavedWords (ϑ := n + 1) u
      simp_rw [multilinearCombine_recursive_form] at hp
      rw [prob_split_last_uniform_sampling_of_finFun] at hp
      apply CA_split_rowwise_implies_CA (C := MC) (u := u) (e := e)
      apply h_interleaved_gaps _ Nat.one_le_two_pow (⋈|U.1) (⋈|U.2)
      apply lt_of_lt_of_le (prob_R_star_gt_threshold (MC := MC) (ε := ε) u e hp)
      apply Pr_le_Pr_of_implies
      intro r hr
      exact correlatedAgreement_of_mem_R_star_tensor (MC := MC)
        (ih (Nat.succ_pos _)) u ⟨r, hr⟩
