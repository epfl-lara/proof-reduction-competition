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
      simp only [zero_add, zero_lt_one, forall_const]
      intro u
      simp_rw [multilinearCombine₁_eq_affineLineEvaluation (F := F) (u := u)]
      intro hprob_gt
      simp_rw [prob_uniform_singleton_finFun_eq (F := F)
        (P := fun r => Δ₀(affineLineEvaluation (u 0) (u 1) r, MC) ≤ e),
        Nat.cast_one, ENNReal.coe_one, one_mul] at hprob_gt
      have h_correlated_agreement := hC_proximityGapAffineLines (u 0) (u 1) hprob_gt
      simp only [jointProximityNat₂] at h_correlated_agreement
      have h_u_eq : u = finMapTwoWords (u 0) (u 1) := by
        funext i
        fin_cases i <;> rfl
      rw [h_u_eq.symm] at h_correlated_agreement
      exact h_correlated_agreement
    | succ ϑ_sub_2 =>
      intro hϑ_gt_0 u hP_multilinearCombine_close_gt
      set U₀ : Fin (2 ^ (ϑ_sub_2 + 1)) → Word A ι :=
        (splitHalfRowWiseInterleavedWords (ϑ := ϑ_sub_2 + 1) u).1
      set U₁ : Fin (2 ^ (ϑ_sub_2 + 1)) → Word A ι :=
        (splitHalfRowWiseInterleavedWords (ϑ := ϑ_sub_2 + 1) u).2
      unfold jointProximityNat
      simp only
      have h_finsnoc_eq_r : ∀ r : Fin (ϑ_sub_2 + 1 + 1) → F,
          Fin.snoc (fun (i : Fin (ϑ_sub_2 + 1)) ↦ r i.castSucc)
            (r (Fin.last (ϑ_sub_2 + 1))) = r := fun r => by
        funext i
        by_cases h : i = Fin.last (ϑ_sub_2 + 1)
        · simp only [h, Fin.snoc_last]
        · have h_i_ne_last_val : i.val ≠ Fin.last (ϑ_sub_2 + 1) := by omega
          rw [Fin.val_last] at h_i_ne_last_val
          simp only [Fin.snoc, Fin.castSucc_castLT, cast_eq, dite_eq_ite,
            ite_eq_left_iff]
          omega
      let P : F → (Fin (ϑ_sub_2 + 1) → F) → Prop := fun r_last r_init =>
        Δ₀(multilinearCombine (u := u) (r := Fin.snoc r_init r_last), MC) ≤ e
      let hP_split_r_last := prob_split_last_uniform_sampling_of_finFun
        (ϑ := ϑ_sub_2 + 1) (F := F) (P := P)
      unfold P at hP_split_r_last
      simp_rw [h_finsnoc_eq_r] at hP_split_r_last
      rw [hP_split_r_last] at hP_multilinearCombine_close_gt
      let ϑ_pred := ϑ_sub_2 + 1
      have multilinearCombine_snoc_eq_multilinearCombine_affine
          (r_init : Fin ϑ_pred → F) (r_last : F) :
          multilinearCombine u (Fin.snoc r_init r_last) =
            multilinearCombine (affineLineEvaluation U₀ U₁ r_last) r_init := by
        rw [multilinearCombine_recursive_form]
        simp only [Fin.snoc_last, Fin.init_snoc]
        rfl
      simp_rw [multilinearCombine_snoc_eq_multilinearCombine_affine]
        at hP_multilinearCombine_close_gt
      let R_star_set := R_star_tensor MC (m := ϑ_pred) (e := e) (ε := ε) U₀ U₁
      have h_prob_Rstar_gt_eps_div_q : Pr_{ let r ← $ᵖ F }[r ∈ R_star_set]
          > (↑ε : ENNReal) / (Fintype.card F : ENNReal) := by
        exact prob_R_star_gt_threshold (MC := MC) (ε := ε) (ϑ := ϑ_sub_2 + 1)
          (u := u) (e := e) hP_multilinearCombine_close_gt
      have h_line_close_to_C_m : ∀ (r : R_star_set),
          jointProximityNat (u := affineLineEvaluation U₀ U₁ r.val) (e := e) (C := MC) := by
        intro r_in_Rstar
        apply correlatedAgreement_of_mem_R_star_tensor
          (ih := fun u_prev => ih (Nat.zero_lt_succ _) u_prev) (u := u)
      have h_C_m_gap := h_interleaved_gaps (2 ^ (ϑ_sub_2 + 1)) (Nat.one_le_two_pow)
      have h_prob_line_gt_eps_div_q :
          Pr_{ let r ← $ᵖ F }[
            Δ₀(affineLineEvaluation
              (u₀ := ⋈|(show WordStack A (Fin (2 ^ (ϑ_sub_2 + 1))) ι from U₀))
              (u₁ := ⋈|(show WordStack A (Fin (2 ^ (ϑ_sub_2 + 1))) ι from U₁)) (r := r),
              ((MC ^⋈ (Fin (2 ^ (ϑ_sub_2 + 1)))))) ≤ e] >
              (↑ε : ENNReal) / (Fintype.card F : ENNReal) := by
        apply lt_of_le_of_lt' _ h_prob_Rstar_gt_eps_div_q
        have h_r_implies : ∀ (r : F), r ∈ R_star_set →
            Δ₀(affineLineEvaluation
              (u₀ := ⋈|(show WordStack A (Fin (2 ^ (ϑ_sub_2 + 1))) ι from U₀))
              (u₁ := ⋈|(show WordStack A (Fin (2 ^ (ϑ_sub_2 + 1))) ι from U₁)) (r := r),
              ((MC ^⋈ (Fin (2 ^ (ϑ_sub_2 + 1)))))) ≤ e := by
          intro r hr_in_Rstar
          specialize h_line_close_to_C_m ⟨r, hr_in_Rstar⟩
          unfold jointProximityNat at h_line_close_to_C_m
          assumption
        exact Pr_le_Pr_of_implies (D := $ᵖ F)
          (g := fun r => Δ₀(affineLineEvaluation
            (u₀ := ⋈|(show WordStack A (Fin (2 ^ (ϑ_sub_2 + 1))) ι from U₀))
            (u₁ := ⋈|(show WordStack A (Fin (2 ^ (ϑ_sub_2 + 1))) ι from U₁)) (r := r),
            ((MC ^⋈ (Fin (2 ^ (ϑ_sub_2 + 1)))))) ≤ e)
          (f := fun r => r ∈ R_star_set) h_r_implies
      have h_final_gap : jointProximityNat₂
          (u₀ := ⋈|(show WordStack A (Fin (2 ^ (ϑ_sub_2 + 1))) ι from U₀))
          (u₁ := ⋈|(show WordStack A (Fin (2 ^ (ϑ_sub_2 + 1))) ι from U₁)) (e := e)
          (C := MC ^⋈ (Fin (2 ^ (ϑ_sub_2 + 1)))) := by
        exact h_C_m_gap
          (u₀ := ⋈|(show WordStack A (Fin (2 ^ (ϑ_sub_2 + 1))) ι from U₀))
          (u₁ := ⋈|(show WordStack A (Fin (2 ^ (ϑ_sub_2 + 1))) ι from U₁))
          h_prob_line_gt_eps_div_q
      apply CA_split_rowwise_implies_CA (u := u) (e := e)
      exact h_final_gap
