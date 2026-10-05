theorem interleaved_affine_gaps_imply_tensor_gaps
    (hC_proximityGapAffineLines : e_ε_correlatedAgreementAffineLinesNat
      (F := F) (A := A) (ι := ι) (C := MC) (e := e) (ε := ε))
    (h_interleaved_gaps : ∀ m : ℕ, m ≥ 1 →
      e_ε_correlatedAgreementAffineLinesNat (F := F)
        (A := InterleavedSymbol A (Fin m)) (ι := ι) (C := MC ^⋈ (Fin m)) e ε) :
    ∀ (ϑ : ℕ), (hϑ_gt_0 : ϑ > 0) → δ_ε_multilinearCorrelatedAgreement_Nat (F := F) (A := A)
      (ι := ι) (C := MC) (ϑ := ϑ) (e := e) (ε := ε) := by
  refine Nat.le_induction (m := 1) ?_ ?_
  · intro u hp
    have hu : finMapTwoWords (u 0) (u 1) = u :=
      funext (Fin.forall_fin_two.2 ⟨rfl, rfl⟩)
    refine hu ▸ hC_proximityGapAffineLines (u 0) (u 1) ?_
    rw [← prob_uniform_singleton_finFun_eq]
    simpa only [multilinearCombine₁_eq_affineLineEvaluation,
      Nat.cast_one, ENNReal.coe_one, one_mul, ENNReal.coe_natCast] using hp
  · intro n _ ih u hp
    refine CA_split_rowwise_implies_CA _ u e
      (h_interleaved_gaps _ Nat.one_le_two_pow _ _ ?_)
    apply lt_of_lt_of_le (prob_R_star_gt_threshold MC u e ?_)
    · exact Pr_le_Pr_of_implies _ _ _ fun r hr =>
        correlatedAgreement_of_mem_R_star_tensor MC ih u ⟨r, hr⟩
    · rw [← prob_split_last_uniform_sampling_of_finFun]
      simpa only [multilinearCombine_affineComb_split_last_close,
        multilinearCombine_recursive_form u, Fin.init_def,
        ENNReal.coe_mul, ENNReal.coe_natCast] using hp
