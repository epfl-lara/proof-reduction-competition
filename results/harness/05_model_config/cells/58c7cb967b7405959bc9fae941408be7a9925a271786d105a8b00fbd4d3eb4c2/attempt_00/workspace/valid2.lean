theorem fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius (i : Fin ℓ) (steps : ℕ)
    [NeZero steps] (h_i_add_steps : i.val + steps ≤ ℓ)
    (f : OracleFunction 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  (h_fw_dist_lt : fiberwiseClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := i) (steps := steps) (h_i_add_steps := h_i_add_steps) (f := f)) :
  hammingClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩ f := by
  classical
  let C := BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩
  obtain ⟨g, _, hg⟩ := Nat.sInf_mem (Set.image_nonempty.mpr
    (show (Set.univ : Set C).Nonempty from ⟨0, Set.mem_univ _⟩) :
    ((fun g : C => (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g).ncard) ''
      Set.univ).Nonempty)
  let Y := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g
  let Q := qMap_total_fiber 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) (i := ⟨i, by omega⟩) (steps := steps)
    (h_i_add_steps := by apply Nat.lt_add_of_pos_right_of_le; omega)
  have hd : hammingDist f g ≤ Y.ncard * 2 ^ steps := by
    have hs : Finset.univ.filter (fun x => f x ≠ g.val x) ⊆
        Finset.image₂ Q Y.toFinset Finset.univ := by
      intro x hx
      exact Finset.mem_image₂.mpr
        ⟨iteratedQuotientMap 𝔽q β h_ℓ_add_R_rate i steps h_i_add_steps x,
          Set.mem_toFinset.mpr ⟨x, rfl, (Finset.mem_filter.mp hx).2⟩,
          pointToIterateQuotientIndex (i := ⟨i, by omega⟩) (steps := steps)
            (h_i_add_steps := h_i_add_steps) (x := x), Finset.mem_univ _,
          (is_fiber_iff_generates_quotient_point 𝔽q β i steps h_i_add_steps x _).mp rfl⟩
    simpa only [hammingDist, Set.ncard_eq_toFinset_card', Finset.card_univ,
      Fintype.card_fin] using
      (Finset.card_le_card hs).trans (Finset.card_image₂_le Q Y.toFinset Finset.univ)
  have hb : 2 * Y.ncard ≤ 2 ^ (ℓ + 𝓡 - (i.val + steps)) -
      2 ^ (ℓ - (i.val + steps)) := by
    unfold fiberwiseClose at h_fw_dist_lt
    have ht := WithTop.coe_lt_coe.1 h_fw_dist_lt
    change Y.ncard = fiberwiseDistance 𝔽q β i steps h_i_add_steps f at hg
    rw [← hg] at ht
    exact Nat.le_of_lt_succ ht
  have ha : (2 ^ (ℓ + 𝓡 - (i.val + steps)) - 2 ^ (ℓ - (i.val + steps))) *
      2 ^ steps = 2 ^ (ℓ + 𝓡 - i.val) - 2 ^ (ℓ - i.val) := by
    rw [Nat.sub_mul, ← Nat.pow_add, ← Nat.pow_add]
    congr 2 <;> omega
  have hn : 2 * hammingDist f g < BBF_CodeDistance ℓ 𝓡 ⟨i, by omega⟩ := by
    have := (Nat.mul_le_mul_left 2 hd).trans
      (by simpa only [← mul_assoc] using Nat.mul_le_mul_right (2 ^ steps) hb)
    rw [ha] at this
    exact Nat.lt_succ_of_le this
  unfold hammingClose
  apply lt_of_le_of_lt (mul_le_mul_left' (Code.distFromCode_le_dist_to_mem f g g.property) 2)
  exact WithTop.coe_lt_coe.2 hn
