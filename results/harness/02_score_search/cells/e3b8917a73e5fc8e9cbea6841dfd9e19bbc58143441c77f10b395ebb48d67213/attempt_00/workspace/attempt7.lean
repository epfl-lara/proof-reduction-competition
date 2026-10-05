theorem interleaved_affine_gaps_imply_tensor_gaps
    (hC_proximityGapAffineLines : e_ε_correlatedAgreementAffineLinesNat
      (F := F) (A := A) (ι := ι) (C := MC) (e := e) (ε := ε))
    (h_interleaved_gaps : ∀ m : ℕ, m ≥ 1 →
      e_ε_correlatedAgreementAffineLinesNat (F := F)
        (A := InterleavedSymbol A (Fin m)) (ι := ι) (C := MC ^⋈ (Fin m)) e ε) :
    ∀ (ϑ : ℕ), (hϑ_gt_0 : ϑ > 0) → δ_ε_multilinearCorrelatedAgreement_Nat (F := F) (A := A)
      (ι := ι) (C := MC) (ϑ := ϑ) (e := e) (ε := ε) := by
  classical
  refine Nat.le_induction (m := 1) ?_ ?_
  · intro u hp
    simp_rw [multilinearCombine₁_eq_affineLineEvaluation] at hp
    rw [prob_uniform_singleton_finFun_eq
      (fun r => Δ₀(affineLineEvaluation (u 0) (u 1) r, MC) ≤ e)] at hp
    have h := hC_proximityGapAffineLines (u 0) (u 1) (by
      simpa only [Nat.cast_one, ENNReal.coe_one, one_mul, ENNReal.coe_natCast] using hp)
    have hu : finMapTwoWords (u 0) (u 1) = u := by
      funext i
      match i with
      | 0 => rfl
      | 1 => rfl
    simpa only [jointProximityNat₂, hu] using h
  · intro n _ ih u hp
    apply CA_split_rowwise_implies_CA (u := u) (e := e)
    apply h_interleaved_gaps (2 ^ n) Nat.one_le_two_pow
    apply lt_of_lt_of_le (prob_R_star_gt_threshold (MC := MC) (ε := ε) u e ?_)
    · apply Pr_le_Pr_of_implies
      intro r hr
      exact ih _ (Finset.mem_filter.mp hr).2
    · rw [← prob_split_last_uniform_sampling_of_finFun]
      dsimp only [multilinearCombine_affineComb_split_last_close]
      simp_rw [multilinearCombine_recursive_form u, Fin.init_def] at hp
      simpa only [ENNReal.coe_mul, ENNReal.coe_natCast] using hp
