theorem interleaved_affine_gaps_imply_tensor_gaps
    (hC_proximityGapAffineLines : e_ε_correlatedAgreementAffineLinesNat
      (F := F) (A := A) (ι := ι) (C := MC) (e := e) (ε := ε))
    (h_interleaved_gaps : ∀ m : ℕ, m ≥ 1 →
      e_ε_correlatedAgreementAffineLinesNat (F := F)
        (A := InterleavedSymbol A (Fin m)) (ι := ι) (C := MC ^⋈ (Fin m)) e ε) :
    ∀ (ϑ : ℕ), (hϑ_gt_0 : ϑ > 0) → δ_ε_multilinearCorrelatedAgreement_Nat (F := F) (A := A)
      (ι := ι) (C := MC) (ϑ := ϑ) (e := e) (ε := ε) := by
  classical
  intro n
  induction n with
  | zero => exact fun h => (Nat.not_lt_zero _ h).elim
  | succ n ih =>
    cases n with
    | zero =>
      simp only [zero_add, zero_lt_one, forall_const]
      intro u hp
      simp_rw [multilinearCombine₁_eq_affineLineEvaluation (F := F) (u := u)] at hp
      simp_rw [prob_uniform_singleton_finFun_eq (F := F)
        (P := fun r => Δ₀(affineLineEvaluation (u 0) (u 1) r, MC) ≤ e),
        Nat.cast_one, ENNReal.coe_one, one_mul] at hp
      have h := hC_proximityGapAffineLines (u 0) (u 1) hp
      have hu : u = finMapTwoWords (u 0) (u 1) := by
        funext i
        match i with
        | 0 => rfl
        | 1 => rfl
      exact hu.symm ▸ h
    | succ n =>
      intro _ u hp
      simp_rw [multilinearCombine_recursive_form u] at hp
      change Pr_{let r ← $ᵖ (Fin (n + 1 + 1) → F)}[
        multilinearCombine_affineComb_split_last_close (MC := MC) u e
          (r (Fin.last (n + 1))) (fun i => r i.castSucc)] > _ at hp
      rw [prob_split_last_uniform_sampling_of_finFun
        (multilinearCombine_affineComb_split_last_close (MC := MC) u e)] at hp
      have hr := prob_R_star_gt_threshold (MC := MC) (ε := ε) u e hp
      apply CA_split_rowwise_implies_CA (u := u) (e := e)
      apply h_interleaved_gaps _ Nat.one_le_two_pow
      apply lt_of_lt_of_le hr
      apply Pr_le_Pr_of_implies
      intro r hr
      exact correlatedAgreement_of_mem_R_star_tensor MC (ih (Nat.succ_pos _)) u ⟨r, hr⟩