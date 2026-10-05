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
  | zero => exact fun h => False.elim (Nat.not_lt_zero _ h)
  | succ n ih =>
    cases n with
    | zero =>
      simp only [zero_add, gt_iff_lt, zero_lt_one, ModuleCode, forall_const]
      intro u hp
      simp_rw [multilinearCombine₁_eq_affineLineEvaluation] at hp
      rw [prob_uniform_singleton_finFun_eq (F := F) (P := fun r => Δ₀(affineLineEvaluation (u 0) (u 1) r, MC) ≤ e)] at hp
      simp only [Nat.cast_one, ENNReal.coe_one, one_mul] at hp
      have h := hC_proximityGapAffineLines (u 0) (u 1) hp
      have hu : u = finMapTwoWords (u 0) (u 1) := by
        funext i
        match i with
        | 0 => rfl
        | 1 => rfl
      exact hu ▸ h
    | succ n =>
      intro _ u hp
      let U₀ := (splitHalfRowWiseInterleavedWords (ϑ := n + 1) u).1
      let U₁ := (splitHalfRowWiseInterleavedWords (ϑ := n + 1) u).2
      have hs := prob_split_last_uniform_sampling_of_finFun (F := F)
        (fun r_last r_init => Δ₀(multilinearCombine u (Fin.snoc r_init r_last), MC) ≤ e)
      have hn (r : Fin (n + 1 + 1) → F) :
          Fin.snoc (fun i => r i.castSucc) (r (Fin.last (n + 1))) = r :=
        Fin.snoc_init_self r
      simp only [hn] at hs
      rw [hs] at hp
      have he (r : Fin (n + 1) → F) (s : F) :
          multilinearCombine u (Fin.snoc r s) =
            multilinearCombine (affineLineEvaluation U₀ U₁ s) r := by
        rw [multilinearCombine_recursive_form]
        simp only [Fin.snoc_last, Fin.init_snoc]
        rfl
      simp_rw [he] at hp
      let R_star_set := R_star_tensor MC (m:=(n + 1)) (e:=e) (ε:=ε) U₀ U₁
      have h_prob_Rstar_gt_eps_div_q : Pr_{ let r ← $ᵖ F }[ r ∈ R_star_set ]
        > (↑ε : ENNReal) / (Fintype.card F : ENNReal) := by
        let res := prob_R_star_gt_threshold (MC := MC) (ε := ε) (ϑ := n + 1) (u := u)
          (e := e) (hp)
        exact res
      have h_line_close_to_C_m : ∀ (r : R_star_set),
        jointProximityNat (u := affineLineEvaluation U₀ U₁ r.val) (e := e) (C := MC) := by
        intro r_in_Rstar
        apply correlatedAgreement_of_mem_R_star_tensor
          (ih := fun u_prev => ih (by omega) u_prev ) (u := u)
      have h_C_m_gap := h_interleaved_gaps (2^(n + 1)) (Nat.one_le_two_pow)
      have h_prob_line_gt_eps_div_q :
        Pr_{ let r ← $ᵖ F }[
          Δ₀(affineLineEvaluation (u₀ := ⋈|(show WordStack A (Fin (2 ^ (n + 1))) ι from U₀))
            (u₁ := ⋈|(show WordStack A (Fin (2 ^ (n + 1))) ι from U₁)) (r := r),
            ((MC ^⋈ (Fin (2 ^ (n + 1)))))) ≤ e
        ] > (↑ε : ENNReal) / (Fintype.card F : ENNReal) := by
          apply lt_of_le_of_lt' _ h_prob_Rstar_gt_eps_div_q
          have h_r_implies: ∀ (r : F), r ∈ R_star_set →
            Δ₀(affineLineEvaluation
              (u₀ := ⋈|(show WordStack A (Fin (2 ^ (n + 1))) ι from U₀))
              (u₁ := ⋈|(show WordStack A (Fin (2 ^ (n + 1))) ι from U₁)) (r := r),
              ((MC ^⋈ (Fin (2 ^ (n + 1)))))) ≤ e := by
            intro r hr_in_Rstar
            specialize h_line_close_to_C_m ⟨r, hr_in_Rstar⟩
            unfold jointProximityNat at h_line_close_to_C_m
            exact h_line_close_to_C_m
          let Pr_le := Pr_le_Pr_of_implies (D := $ᵖ F)
            (g := fun r => Δ₀(affineLineEvaluation
              (u₀ := ⋈|(show WordStack A (Fin (2 ^ (n + 1))) ι from U₀))
              (u₁ := ⋈|(show WordStack A (Fin (2 ^ (n + 1))) ι from U₁)) (r := r),
              ((MC ^⋈ (Fin (2 ^ (n + 1)))))) ≤ e)
            (f := fun r => r ∈ R_star_set) (h_imp := h_r_implies)
          simp only at Pr_le
          exact Pr_le
      have h_final_gap : jointProximityNat₂
        (u₀ := ⋈|(show WordStack A (Fin (2 ^ (n + 1))) ι from U₀))
        (u₁ := ⋈|(show WordStack A (Fin (2 ^ (n + 1))) ι from U₁)) (e := e)
        (C := (MC ^⋈ (Fin (2^(n + 1))))) := by
        apply h_C_m_gap (u₀ := ⋈|(show WordStack A (Fin (2 ^ (n + 1))) ι from U₀))
          (u₁ := ⋈|(show WordStack A (Fin (2 ^ (n + 1))) ι from U₁))
          (h_prob_line_gt_eps_div_q)
      apply CA_split_rowwise_implies_CA (u := u) (e := e)
      exact h_final_gap
