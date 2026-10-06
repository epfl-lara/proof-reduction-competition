theorem fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius (i : Fin ℓ) (steps : ℕ)
    [NeZero steps] (h_i_add_steps : i.val + steps ≤ ℓ)
    (f : OracleFunction 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  (h_fw_dist_lt : fiberwiseClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := i) (steps := steps) (h_i_add_steps := h_i_add_steps) (f := f)) :
  hammingClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩ f := by
  let j : Fin (ℓ + 1) := ⟨i, fin_ℓ_lt_ℓ_add_one i⟩
  let j' : Fin (ℓ + 1) := ⟨i.val + steps, Nat.lt_succ_of_le h_i_add_steps⟩
  let C := BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) j
  let D := fun (g : C) => (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g.val).ncard
  obtain ⟨⟨g, hmem⟩, _, hg⟩ := Nat.sInf_mem
    (Set.image_nonempty.mpr Set.univ_nonempty :
      (D '' Set.univ).Nonempty)
  let Y := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g
  let q := iteratedQuotientMap 𝔽q β h_ℓ_add_R_rate i steps h_i_add_steps
  let F := qMap_total_fiber 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) (i := ⟨i, fin_ℓ_lt_r (h_ℓ_add_R_rate := h_ℓ_add_R_rate) i⟩) steps
    (fin_ℓ_steps_lt_ℓ_add_R i steps h_i_add_steps)
  have hcount : hammingDist f g ≤ Y.ncard * 2 ^ steps := by
    calc
      _ ≤ (Finset.image₂ F Y.toFinite.toFinset Finset.univ).card := by
        apply Finset.card_le_card
        intro x hx
        exact Finset.mem_image₂.mpr ⟨q x, Y.toFinite.mem_toFinset.mpr
          ⟨x, rfl, (Finset.mem_filter.mp hx).2⟩, _, Finset.mem_univ _, (is_fiber_iff_generates_quotient_point 𝔽q β i steps
          h_i_add_steps x (q x)).mp rfl⟩
      _ ≤ Y.ncard * 2 ^ steps := by
        simpa only [Finset.card_univ, Fintype.card_fin, ←Set.ncard_eq_toFinset_card] using
          Finset.card_image₂_le F Y.toFinite.toFinset Finset.univ
  have hfw : 2 * Y.ncard ≤ BBF_CodeDistance ℓ 𝓡 j' - 1 := by
    change Y.ncard = _ at hg
    rw [hg]
    exact Nat.le_of_lt_succ (ENat.coe_lt_coe.1 h_fw_dist_lt)
  have halg : (BBF_CodeDistance ℓ 𝓡 j' - 1) * 2 ^ steps =
      BBF_CodeDistance ℓ 𝓡 j - 1 := by
    simp only [BBF_CodeDistance, j, j', Nat.add_one_sub_one]
    rw [Nat.sub_mul, Nat.sub_add_eq, Nat.sub_add_eq,
      pow_sub_mul_pow 2 (Nat.le_sub_of_add_le'
        (h_i_add_steps.trans (Nat.le_add_right ℓ 𝓡))),
      pow_sub_mul_pow 2 (Nat.le_sub_of_add_le' h_i_add_steps)]
  refine lt_of_le_of_lt
    (mul_le_mul_left' (Code.distFromCode_le_dist_to_mem f g hmem) 2)
    (ENat.coe_lt_coe.mpr ?_)
  apply Nat.lt_succ_of_le
  exact (Nat.mul_le_mul_left 2 hcount).trans (by
    rw [←mul_assoc]
    exact (Nat.mul_le_mul_right _ hfw).trans_eq halg)