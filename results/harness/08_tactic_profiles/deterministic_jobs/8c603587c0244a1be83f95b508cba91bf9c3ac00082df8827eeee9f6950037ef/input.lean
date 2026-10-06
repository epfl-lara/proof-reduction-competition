theorem interleaved_affine_gaps_imply_tensor_gaps
    (hC_proximityGapAffineLines : e_ε_correlatedAgreementAffineLinesNat
      (F := F) (A := A) (ι := ι) (C := MC) (e := e) (ε := ε))
    (h_interleaved_gaps : ∀ m : ℕ, m ≥ 1 →
      e_ε_correlatedAgreementAffineLinesNat (F := F)
        (A := InterleavedSymbol A (Fin m)) (ι := ι) (C := MC ^⋈ (Fin m)) e ε) :
    ∀ (ϑ : ℕ), (hϑ_gt_0 : ϑ > 0) → δ_ε_multilinearCorrelatedAgreement_Nat (F := F) (A := A)
      (ι := ι) (C := MC) (ϑ := ϑ) (e := e) (ε := ε) := by
  classical
  refine Nat.le_induction ?_ ?_
  ·
    intro u hp
    simp only [multilinearCombine₁_eq_affineLineEvaluation u,
      @prob_uniform_singleton_finFun_eq F _ ⟨0⟩
        (fun r => Code.distFromCode (affineLineEvaluation (u 0) (u 1) r) MC ≤ e),
      Nat.cast_one, ENNReal.coe_one, one_mul] at hp
    have hu : finMapTwoWords (u 0) (u 1) = u :=
      funext (Fin.forall_fin_two.2 ⟨rfl, rfl⟩)
    exact hu ▸ hC_proximityGapAffineLines (u 0) (u 1) hp
  · intro n _ ih u hp
    apply CA_split_rowwise_implies_CA MC u e
    apply h_interleaved_gaps (2 ^ n) Nat.one_le_two_pow
    refine lt_of_lt_of_le (prob_R_star_gt_threshold MC u e ?_) ?_
    · rw [←@prob_split_last_uniform_sampling_of_finFun n F _ ⟨0⟩
        (multilinearCombine_affineComb_split_last_close MC u e)]
      simpa only [multilinearCombine_affineComb_split_last_close,
        multilinearCombine_recursive_form u, Fin.init_def, ENNReal.coe_mul, ENNReal.coe_natCast] using hp
    · apply Pr_le_Pr_of_implies
      intro r hr
      exact ih _ (Finset.mem_filter.mp hr).2