theorem interleaved_affine_gaps_imply_tensor_gaps
    (hC_proximityGapAffineLines : e_ε_correlatedAgreementAffineLinesNat
      (F := F) (A := A) (ι := ι) (C := MC) (e := e) (ε := ε))
    (h_interleaved_gaps : ∀ m : ℕ, m ≥ 1 →
      e_ε_correlatedAgreementAffineLinesNat (F := F)
        (A := InterleavedSymbol A (Fin m)) (ι := ι) (C := MC ^⋈ (Fin m)) e ε) :
    ∀ (ϑ : ℕ), (hϑ_gt_0 : ϑ > 0) → δ_ε_multilinearCorrelatedAgreement_Nat (F := F) (A := A)
      (ι := ι) (C := MC) (ϑ := ϑ) (e := e) (ε := ε) := by
  intro ϑ hϑ
  induction ϑ, hϑ using Nat.le_induction with
  | base =>
    intro u hp
    simp only [multilinearCombine₁_eq_affineLineEvaluation (u := u),
      prob_uniform_singleton_finFun_eq (P := fun r =>
      Δ₀(affineLineEvaluation (u 0) (u 1) r, MC) ≤ e),
      Nat.cast_one, ENNReal.coe_one, one_mul] at hp
    have hu : finMapTwoWords (u 0) (u 1) = u := by
      funext i
      match i with
      | 0 => rfl
      | 1 => rfl
    exact hu ▸ hC_proximityGapAffineLines (u 0) (u 1) hp
  | succ n hn ih =>
    intro u hp
    simp only [multilinearCombine_recursive_form (u := u)] at hp
    have hs := prob_split_last_uniform_sampling_of_finFun
      (P := multilinearCombine_affineComb_split_last_close (MC := MC) u e)
    apply CA_split_rowwise_implies_CA (C := MC) u e
    apply h_interleaved_gaps (2 ^ n) Nat.one_le_two_pow
    apply lt_of_lt_of_le (prob_R_star_gt_threshold (MC := MC) u e (hs ▸ hp))
    apply Pr_le_Pr_of_implies
    intro r hr
    exact ih _ (by
      simpa only [R_star_tensor, Finset.mem_filter, Finset.mem_univ, true_and] using hr)
