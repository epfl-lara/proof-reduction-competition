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
    | zero =>
      intro u
      contradiction
    | succ ϑ_sub_1 ih =>
      cases ϑ_sub_1 with
      | zero =>
        -- `ϑ = 1`
        simp only [zero_add, zero_lt_one, forall_const]
        intro u
        let toAffineLineEval := multilinearCombine₁_eq_affineLineEvaluation (F := F) (u := u)
        intro hprob_gt
        simp_rw [toAffineLineEval] at hprob_gt
        let prob_eq := prob_uniform_singleton_finFun_eq (F := F)
          (P := fun r => Δ₀(affineLineEvaluation (u 0) (u 1) r, MC) ≤ e)
        -- Convert sampling (r ← (Fin 1 → F)) into sampling (r ← F)
        simp_rw [prob_eq, Nat.cast_one, ENNReal.coe_one, one_mul] at hprob_gt
        have h_correlated_agreement := hC_proximityGapAffineLines (u 0) (u 1) hprob_gt
        simp only [jointProximityNat₂] at h_correlated_agreement
        have h_u_eq: u = finMapTwoWords (u 0) (u 1) := by
          funext rowIdx
          match rowIdx with
          | 0 => rfl
          | 1 => rfl
        rw [h_u_eq.symm] at h_correlated_agreement
        exact h_correlated_agreement
      | succ n =>
        intro hn u hp
        apply CA_split_rowwise_implies_CA (ϑ := n + 1) (u := u) (e := e)
        apply h_interleaved_gaps (2 ^ (n + 1)) Nat.one_le_two_pow
        apply lt_of_lt_of_le (prob_R_star_gt_threshold (MC := MC) (ε := ε)
          (ϑ := n + 1) (u := u) (e := e) ?_)
        · exact Pr_le_Pr_of_implies (D := $ᵖ F) (h_imp := fun r hr =>
            correlatedAgreement_of_mem_R_star_tensor (ih := ih (Nat.succ_pos n))
              (u := u) ⟨r, hr⟩)
        · rw [← prob_split_last_uniform_sampling_of_finFun]
          simpa only [multilinearCombine_affineComb_split_last_close,
            multilinearCombine_recursive_form u] using hp
