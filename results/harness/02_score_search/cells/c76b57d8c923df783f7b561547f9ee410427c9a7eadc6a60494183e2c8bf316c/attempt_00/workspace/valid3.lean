theorem fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius (i : Fin ℓ) (steps : ℕ)
    [NeZero steps] (h_i_add_steps : i.val + steps ≤ ℓ)
    (f : OracleFunction 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  (h_fw_dist_lt : fiberwiseClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := i) (steps := steps) (h_i_add_steps := h_i_add_steps) (f := f)) :
  hammingClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩ f := by
  classical
  let C := BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩
  obtain ⟨g, _, hg⟩ := Nat.sInf_mem (s := (fun g : C =>
    (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g).ncard) '' Set.univ)
    (Set.image_nonempty.mpr Set.univ_nonempty)
  let Y := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g
  have hcount : hammingDist f g ≤ Y.ncard * 2 ^ steps := by
    let q := qMap_total_fiber 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) (i := ⟨i, by omega⟩) (steps := steps)
      (h_i_add_steps := fin_ℓ_steps_lt_ℓ_add_R i steps h_i_add_steps)
    have h := Finset.card_le_card_of_surjOn
      (s := Y.toFinset ×ˢ (Finset.univ : Finset (Fin (2 ^ steps))))
      (t := Finset.univ.filter (fun x => f x ≠ g.val x)) (fun p => q p.1 p.2) (by
        intro x hx
        refine ⟨(iteratedQuotientMap 𝔽q β h_ℓ_add_R_rate i steps h_i_add_steps x,
          pointToIterateQuotientIndex (i := ⟨i, by omega⟩) (steps := steps)
            (h_i_add_steps := h_i_add_steps) (x := x)), ?_, ?_⟩
        · simp only [Finset.mem_coe, Finset.mem_product, Set.mem_toFinset,
            Finset.mem_univ, and_true]
          exact ⟨x, rfl, (Finset.mem_filter.mp hx).2⟩
        · exact (is_fiber_iff_generates_quotient_point 𝔽q β i steps h_i_add_steps x _).mp rfl)
    simpa only [Finset.card_product, ← Set.ncard_eq_toFinset_card',
      Finset.card_univ, Fintype.card_fin, hammingDist] using h
  have hfw : 2 * Y.ncard ≤ 2 ^ (ℓ + 𝓡 - (i.val + steps)) -
      2 ^ (ℓ - (i.val + steps)) := by
    unfold fiberwiseClose fiberwiseDistance at h_fw_dist_lt
    rw [← hg] at h_fw_dist_lt
    exact Nat.le_of_lt_succ (WithTop.coe_lt_coe.1 h_fw_dist_lt)
  have hscale : (2 ^ (ℓ + 𝓡 - (i.val + steps)) - 2 ^ (ℓ - (i.val + steps))) *
      2 ^ steps = 2 ^ (ℓ + 𝓡 - i.val) - 2 ^ (ℓ - i.val) := by
    rw [Nat.sub_mul, ← Nat.pow_add, ← Nat.pow_add]
    congr 2 <;> omega
  have hfinal : 2 * hammingDist f g < BBF_CodeDistance ℓ 𝓡 ⟨i, by omega⟩ := by
    apply Nat.lt_succ_of_le
    calc
      2 * hammingDist f g ≤ 2 * (Y.ncard * 2 ^ steps) := Nat.mul_le_mul_left 2 hcount
      _ = (2 * Y.ncard) * 2 ^ steps := (Nat.mul_assoc _ _ _).symm
      _ ≤ (2 ^ (ℓ + 𝓡 - (i.val + steps)) - 2 ^ (ℓ - (i.val + steps))) * 2 ^ steps :=
        Nat.mul_le_mul_right _ hfw
      _ = _ := hscale
  unfold hammingClose
  apply lt_of_le_of_lt (mul_le_mul_left' (Code.distFromCode_le_dist_to_mem f g g.property) 2)
  exact ENat.coe_lt_coe.mpr hfinal
