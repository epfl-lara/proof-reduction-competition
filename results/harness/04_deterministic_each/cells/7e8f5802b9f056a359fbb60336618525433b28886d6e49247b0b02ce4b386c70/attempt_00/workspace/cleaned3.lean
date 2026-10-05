theorem fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius (i : Fin ℓ) (steps : ℕ)
    [NeZero steps] (h_i_add_steps : i.val + steps ≤ ℓ)
    (f : OracleFunction 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  (h_fw_dist_lt : fiberwiseClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := i) (steps := steps) (h_i_add_steps := h_i_add_steps) (f := f)) :
  hammingClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩ f := by
  classical
  let C := BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩
  obtain ⟨g, _, hg⟩ := Nat.sInf_mem (s :=
    (fun g : C => (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g).ncard) ''
      Set.univ) (Set.image_nonempty.mpr Set.univ_nonempty)
  let Y := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g
  have hfw : 2 * Y.ncard ≤ BBF_CodeDistance ℓ 𝓡 ⟨i.val + steps, by omega⟩ - 1 := by
    have h : (2 * Y.ncard : ℕ) < BBF_CodeDistance ℓ 𝓡 ⟨i.val + steps, by omega⟩ := by
      apply ENat.coe_lt_coe.mp
      simpa only [Nat.cast_mul, Nat.cast_ofNat, Y, hg, fiberwiseClose,
        fiberwiseDistance, C] using h_fw_dist_lt
    omega
  have hcount : hammingDist f g ≤ Y.ncard * 2 ^ steps := by
    rw [ Set.ncard_eq_toFinset_card', ← Fintype.card_fin (n := 2 ^ steps),
      ← Finset.card_univ, ← Finset.card_product]
    apply Finset.card_le_card_of_surjOn (fun p =>
      qMap_total_fiber 𝔽q β (i := ⟨i, by omega⟩) (steps := steps)
        (h_i_add_steps := fin_ℓ_steps_lt_ℓ_add_R i steps h_i_add_steps) (y := p.1) p.2)
    intro x hx
    refine ⟨(iteratedQuotientMap 𝔽q β h_ℓ_add_R_rate i steps h_i_add_steps x,
      pointToIterateQuotientIndex (i := ⟨i, by omega⟩) (steps := steps)
        (h_i_add_steps := h_i_add_steps) (x := x)), ?_, ?_⟩
    · exact Finset.mem_product.mpr ⟨Set.mem_toFinset.mpr
        ⟨x, rfl, (Finset.mem_filter.mp hx).2⟩, Finset.mem_univ _⟩
    · exact (is_fiber_iff_generates_quotient_point 𝔽q β i steps h_i_add_steps x _).mp rfl
  have hid : (BBF_CodeDistance ℓ 𝓡 ⟨i.val + steps, by omega⟩ - 1) * 2 ^ steps =
      BBF_CodeDistance ℓ 𝓡 ⟨i, by omega⟩ - 1 := by
    dsimp only [BBF_CodeDistance, Nat.add_one_sub_one]
    rw [Nat.sub_mul, ← Nat.pow_add, ← Nat.pow_add]
    congr 2 <;> omega
  have hnat : 2 * hammingDist f g < BBF_CodeDistance ℓ 𝓡 ⟨i, by omega⟩ := by
    have h := (Nat.mul_le_mul_left 2 hcount).trans
      (by simpa only [mul_assoc] using Nat.mul_le_mul_right (2 ^ steps) hfw)
    rw [] at h
    have : 0 < BBF_CodeDistance ℓ 𝓡 ⟨i, by omega⟩ := Nat.succ_pos _
    omega
  unfold hammingClose
  apply lt_of_le_of_lt
    (mul_le_mul_left' (Code.distFromCode_le_dist_to_mem f g g.property) 2)
  exact_mod_cast hnat
