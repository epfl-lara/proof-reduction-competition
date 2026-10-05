theorem fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius (i : Fin ℓ) (steps : ℕ)
    [NeZero steps] (h_i_add_steps : i.val + steps ≤ ℓ)
    (f : OracleFunction 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  (h_fw_dist_lt : fiberwiseClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := i) (steps := steps) (h_i_add_steps := h_i_add_steps) (f := f)) :
  hammingClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩ f := by
  classical
  let C := BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, fin_ℓ_lt_ℓ_add_one i⟩
  let Y (g : C) := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g
  obtain ⟨g, _, hg⟩ := Nat.sInf_mem (s := (fun g => (Y g).ncard) '' Set.univ)
    ⟨_, 0, Set.mem_univ _, rfl⟩
  have h := Nat.mul_le_mul_right (2 ^ steps)
    (Nat.le_of_lt_succ (ENat.coe_lt_coe.mp h_fw_dist_lt))
  dsimp only [fiberwiseDistance] at h
  rw [← hg, Nat.sub_mul, ← Nat.pow_add, ← Nat.pow_add,
    ← Nat.sub_add_comm (Nat.le_add_right_of_le h_i_add_steps), Nat.add_sub_add_right,
    ← Nat.sub_add_comm h_i_add_steps, Nat.add_sub_add_right, mul_assoc] at h
  refine lt_of_le_of_lt
    (mul_le_mul_left' (Code.distFromCode_le_dist_to_mem f g g.property) 2)
    (ENat.coe_lt_coe.mpr (Nat.lt_succ_of_le ?_))
  refine (Nat.mul_le_mul_left 2 ?_).trans h
  let q := qMap_total_fiber 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    ⟨i, fin_ℓ_lt_r (h_ℓ_add_R_rate := h_ℓ_add_R_rate) i⟩ steps
    (fin_ℓ_steps_lt_ℓ_add_R i steps h_i_add_steps)
  have hc := Finset.card_le_card_of_surjOn (Function.uncurry q)
    (s := (Y g).toFinset ×ˢ (Finset.univ : Finset (Fin (2 ^ steps))))
    (t := Finset.univ.filter (fun x => f x ≠ g.val x)) (by
      intro x hx
      refine ⟨(_, _), ?_,
        (is_fiber_iff_generates_quotient_point 𝔽q β i steps h_i_add_steps x _).mp rfl⟩
      exact Finset.mem_product.mpr
        ⟨Set.mem_toFinset.mpr ⟨x, rfl, (Finset.mem_filter.mp hx).2⟩, Finset.mem_univ _⟩)
  simpa only [hammingDist, Finset.card_product, ← Set.ncard_eq_toFinset_card',
    Finset.card_univ, Fintype.card_fin] using hc
