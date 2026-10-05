theorem fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius (i : Fin ℓ) (steps : ℕ)
    [NeZero steps] (h_i_add_steps : i.val + steps ≤ ℓ)
    (f : OracleFunction 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  (h_fw_dist_lt : fiberwiseClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := i) (steps := steps) (h_i_add_steps := h_i_add_steps) (f := f)) :
  hammingClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩ f := by
  classical
  let C := BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩
  let D (g : C) := (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g).ncard
  obtain ⟨g, _, hg⟩ := Nat.sInf_mem
    (Set.image_nonempty.mpr (Set.univ_nonempty : (Set.univ : Set C).Nonempty) :
      (D '' Set.univ).Nonempty)
  have hb : 2 * D g ≤ 2 ^ (ℓ + 𝓡 - (i.val + steps)) - 2 ^ (ℓ - (i.val + steps)) := by
    have h := ENat.coe_lt_coe.mp h_fw_dist_lt
    change 2 * sInf (D '' Set.univ) < _ at h
    rw [← hg] at h
    exact Nat.le_of_lt_succ h
  have hc : hammingDist f g ≤ D g * 2 ^ steps := by
    let Y := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g
    let q := qMap_total_fiber 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
      ⟨i, by omega⟩ steps (fin_ℓ_steps_lt_ℓ_add_R i steps h_i_add_steps)
    have h := Finset.card_le_card_of_surjOn (fun p => q p.1 p.2)
      (s := Y.toFinset ×ˢ (Finset.univ : Finset (Fin (2 ^ steps))))
      (t := Finset.univ.filter (fun x => f x ≠ g.val x)) (by
        intro x hx
        refine ⟨(iteratedQuotientMap 𝔽q β h_ℓ_add_R_rate i steps h_i_add_steps x,
          pointToIterateQuotientIndex (i := ⟨i, by omega⟩)
            (steps := steps) (h_i_add_steps := h_i_add_steps) (x := x)), ?_, ?_⟩
        · exact Finset.mem_product.mpr
            ⟨Set.mem_toFinset.mpr ⟨x, rfl, (Finset.mem_filter.mp hx).2⟩, Finset.mem_univ _⟩
        · exact (is_fiber_iff_generates_quotient_point 𝔽q β i steps h_i_add_steps x _).mp rfl)
    simpa only [hammingDist, D, Y, Finset.card_product, ← Set.ncard_eq_toFinset_card', Finset.card_univ, Fintype.card_fin] using h
  have he : (2 ^ (ℓ + 𝓡 - (i.val + steps)) - 2 ^ (ℓ - (i.val + steps))) * 2 ^ steps =
      2 ^ (ℓ + 𝓡 - i.val) - 2 ^ (ℓ - i.val) := by
    rw [Nat.sub_mul, ← Nat.pow_add, ← Nat.pow_add,
      show ℓ + 𝓡 - (i.val + steps) + steps = ℓ + 𝓡 - i.val by omega,
      show ℓ - (i.val + steps) + steps = ℓ - i.val by omega]
  have hn : 2 * hammingDist f g < BBF_CodeDistance ℓ 𝓡 ⟨i, by omega⟩ := by
    apply Nat.lt_succ_of_le
    calc
      2 * hammingDist f g ≤ (2 * D g) * 2 ^ steps := by
        rw [mul_assoc]
        exact Nat.mul_le_mul_left 2 hc
      _ ≤ (2 ^ (ℓ + 𝓡 - (i.val + steps)) - 2 ^ (ℓ - (i.val + steps))) * 2 ^ steps :=
        Nat.mul_le_mul_right _ hb
      _ = _ := he
  exact lt_of_le_of_lt
    (mul_le_mul_left' (Code.distFromCode_le_dist_to_mem f g g.property) 2)
    (ENat.coe_lt_coe.mpr hn)
