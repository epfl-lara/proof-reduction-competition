theorem fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius (i : Fin ℓ) (steps : ℕ)
    [NeZero steps] (h_i_add_steps : i.val + steps ≤ ℓ)
    (f : OracleFunction 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  (h_fw_dist_lt : fiberwiseClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := i) (steps := steps) (h_i_add_steps := h_i_add_steps) (f := f)) :
  hammingClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩ f := by
  classical
  let C := BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, fin_ℓ_lt_ℓ_add_one i⟩
  obtain ⟨g, _, hg⟩ := Nat.sInf_mem (s :=
    (fun g : C => (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g).ncard) ''
      Set.univ) (Set.image_nonempty.mpr Set.univ_nonempty)
  let Y := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g
  have hcount : hammingDist f g ≤ Y.ncard * 2 ^ steps := by
    rw [ Set.ncard_eq_toFinset_card', ← Fintype.card_fin (n := 2 ^ steps),
      ← Finset.card_univ, ← Finset.card_product]
    apply Finset.card_le_card_of_surjOn (fun p =>
      qMap_total_fiber 𝔽q β (i := ⟨i, i.isLt.trans (lt_of_add_right_lt h_ℓ_add_R_rate)⟩) (steps := steps)
        (h_i_add_steps := fin_ℓ_steps_lt_ℓ_add_R i steps h_i_add_steps) (y := p.1) p.2)
    intro x hx
    refine ⟨(_, _), ?_,
      (is_fiber_iff_generates_quotient_point 𝔽q β i steps h_i_add_steps x _).mp rfl⟩
    exact Finset.mem_product.mpr ⟨Set.mem_toFinset.mpr
      ⟨x, rfl, (Finset.mem_filter.mp hx).2⟩, Finset.mem_univ _⟩
  have hfw : 2 * Y.ncard ≤ 2 ^ (ℓ + 𝓡 - (i.val + steps)) -
      2 ^ (ℓ - (i.val + steps)) := by
    rw [show Y.ncard = _ from hg]
    exact Nat.le_of_lt_succ (ENat.coe_lt_coe.mp h_fw_dist_lt)
  refine (mul_le_mul_left' (Code.distFromCode_le_dist_to_mem f g g.property) 2).trans_lt
    (ENat.coe_lt_coe.mpr (Nat.lt_succ_of_le ?_))
  have h := Nat.mul_le_mul_right (2 ^ steps) hfw
  rw [Nat.sub_mul, ← Nat.pow_add, ← Nat.pow_add,
    Nat.sub_add_eq, Nat.sub_add_cancel
      (Nat.le_sub_of_add_le' (h_i_add_steps.trans (Nat.le_add_right ℓ 𝓡))),
    Nat.sub_add_eq, Nat.sub_add_cancel (Nat.le_sub_of_add_le' h_i_add_steps)] at h
  exact (Nat.mul_le_mul_left 2 hcount).trans (by simpa only [mul_assoc] using h)
