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

      have hr := prob_R_star_gt_threshold (MC := MC) (ε := ε) u e hp
      have hc := correlatedAgreement_of_mem_R_star_tensor
        (ih := ih (Nat.succ_pos _)) (u := u)
      exact CA_split_rowwise_implies_CA (C := (MC : Set (Word A ι))) (u := u) (e := e)
        (h_interleaved_gaps (2 ^ (n + 1)) Nat.one_le_two_pow
          (⋈|(show WordStack A (Fin (2 ^ (n + 1))) ι from U₀))
          (⋈|(show WordStack A (Fin (2 ^ (n + 1))) ι from U₁))
          (lt_of_lt_of_le hr
            (Pr_le_Pr_of_implies (D := $ᵖ F) (h_imp := fun r hr => hc ⟨r, hr⟩))))
