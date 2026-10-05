theorem fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius (i : Fin ℓ) (steps : ℕ)
    [NeZero steps] (h_i_add_steps : i.val + steps ≤ ℓ)
    (f : OracleFunction 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  (h_fw_dist_lt : fiberwiseClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := i) (steps := steps) (h_i_add_steps := h_i_add_steps) (f := f)) :
  hammingClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩ f := by
  unfold fiberwiseClose at h_fw_dist_lt
  let C := BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, fin_ℓ_lt_ℓ_add_one i⟩
  let d := fiberwiseDistance 𝔽q β i steps h_i_add_steps f
  obtain ⟨g, _, hg⟩ : ∃ g : C, g ∈ Set.univ ∧
      (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g).ncard = d :=
    Nat.sInf_mem (Set.image_nonempty.mpr Set.univ_nonempty)
  let Y := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g
  letI : Fintype Y := Fintype.ofFinite Y
  let q := iteratedQuotientMap 𝔽q β h_ℓ_add_R_rate i steps h_i_add_steps
  let F := qMap_total_fiber 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) (i := ⟨i, lt_trans i.isLt (Nat.lt_of_add_right_lt h_ℓ_add_R_rate)⟩) steps
    (fin_ℓ_steps_lt_ℓ_add_R i steps h_i_add_steps)
  have hc : hammingDist f g ≤ Y.ncard * 2 ^ steps := by
    calc
      _ ≤ (Y.toFinset ×ˢ (Finset.univ : Finset (Fin (2 ^ steps)))).card := by
        apply Finset.card_le_card_of_surjOn (fun p => F p.1 p.2)
        intro x hx
        refine ⟨(q x, pointToIterateQuotientIndex
          (i := i.castSucc) (steps := steps) (h_i_add_steps := h_i_add_steps) (x := x)), ?_, ?_⟩
        · exact Finset.mem_product.mpr ⟨Set.mem_toFinset.mpr
            ⟨x, rfl, (Finset.mem_filter.mp hx).2⟩, Finset.mem_univ _⟩
        · exact (is_fiber_iff_generates_quotient_point 𝔽q β i steps h_i_add_steps
            x (q x)).mp rfl
      _ = _ := by
        rw [Finset.card_product, Finset.card_univ, Fintype.card_fin,
          ← Set.ncard_eq_toFinset_card']
  have hfw : 2 * Y.ncard ≤ 2 ^ (ℓ + 𝓡 - (i.val + steps)) -
      2 ^ (ℓ - (i.val + steps)) := by
    rw [hg]
    exact Nat.le_of_lt_succ (WithTop.coe_lt_coe.mp h_fw_dist_lt)
  have hn : 2 * hammingDist f g < BBF_CodeDistance ℓ 𝓡 ⟨i, fin_ℓ_lt_ℓ_add_one i⟩ := by
    apply Nat.lt_succ_of_le
    calc
      _ ≤ 2 * (Y.ncard * 2 ^ steps) := Nat.mul_le_mul_left 2 hc
      _ = (2 * Y.ncard) * 2 ^ steps := (Nat.mul_assoc _ _ _).symm
      _ ≤ _ := Nat.mul_le_mul_right (2 ^ steps) hfw
      _ = _ := by
        rw [Nat.sub_mul, ← Nat.pow_add, ← Nat.pow_add,
          show ℓ + 𝓡 - (i.val + steps) + steps = ℓ + 𝓡 - i.val by omega,
          show ℓ - (i.val + steps) + steps = ℓ - i.val by omega]
  unfold hammingClose
  apply lt_of_le_of_lt (mul_le_mul_left'
    (Code.distFromCode_le_dist_to_mem f g g.property) 2)
  exact WithTop.coe_lt_coe.mpr hn
