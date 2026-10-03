theorem fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius (i : Fin ℓ) (steps : ℕ)
    [NeZero steps] (h_i_add_steps : i.val + steps ≤ ℓ)
    (f : OracleFunction 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  (h_fw_dist_lt : fiberwiseClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := i) (steps := steps) (h_i_add_steps := h_i_add_steps) (f := f)) :
  hammingClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩ f := by
  classical
  let C := BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩
  let d := fiberwiseDistance 𝔽q β i steps h_i_add_steps f
  let d_i := BBF_CodeDistance ℓ 𝓡 ⟨i, by omega⟩
  let d_next := BBF_CodeDistance ℓ 𝓡 ⟨i.val + steps, by omega⟩
  obtain ⟨g, _, hg⟩ := Nat.sInf_mem
    (show ((fun g : C => (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g).ncard)
      '' Set.univ).Nonempty from Set.image_nonempty.mpr Set.univ_nonempty)
  let Y := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g
  change Y.ncard = d at hg
  let F := qMap_total_fiber 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) (i := ⟨i, by omega⟩) (steps := steps)
    (h_i_add_steps := by apply Nat.lt_add_of_pos_right_of_le; omega)
  have hcount : hammingDist f g ≤ d * 2 ^ steps := by
    rw [← hg, Set.ncard_eq_toFinset_card']
    calc
      _ ≤ (Finset.image₂ F Y.toFinset Finset.univ).card := by
        apply Finset.card_le_card
        intro x hx
        refine Finset.mem_image₂.mpr
          ⟨iteratedQuotientMap 𝔽q β h_ℓ_add_R_rate i steps h_i_add_steps x,
            ?_, pointToIterateQuotientIndex (i := ⟨i, by omega⟩) (steps := steps)
              (h_i_add_steps := h_i_add_steps) (x := x), Finset.mem_univ _, ?_⟩
        · exact Set.mem_toFinset.mpr ⟨x, rfl, (Finset.mem_filter.mp hx).2⟩
        · exact (is_fiber_iff_generates_quotient_point 𝔽q β i steps h_i_add_steps
            x _).mp rfl
      _ ≤ _ := by
        simpa only [Finset.card_univ, Fintype.card_fin] using
          Finset.card_image₂_le F Y.toFinset Finset.univ
  have hfw : 2 * d ≤ d_next - 1 :=
    Nat.le_of_lt_succ (WithTop.coe_lt_coe.1 h_fw_dist_lt)
  have halg : (d_next - 1) * 2 ^ steps = d_i - 1 := by
    dsimp only [d_next, d_i, BBF_CodeDistance, Nat.add_one_sub_one]
    rw [Nat.sub_mul, ← Nat.pow_add, ← Nat.pow_add,
      show ℓ + 𝓡 - (↑i + steps) + steps = ℓ + 𝓡 - ↑i by omega,
      show ℓ - (↑i + steps) + steps = ℓ - ↑i by omega]
  have hnat : 2 * hammingDist f g < d_i := by
    apply Nat.lt_of_le_pred (h := by dsimp only [d_i, BBF_CodeDistance]; omega)
    calc
      _ ≤ 2 * (d * 2 ^ steps) := Nat.mul_le_mul_left 2 hcount
      _ = (2 * d) * 2 ^ steps := (Nat.mul_assoc _ _ _).symm
      _ ≤ (d_next - 1) * 2 ^ steps := Nat.mul_le_mul_right _ hfw
      _ = _ := halg
  unfold hammingClose
  refine (mul_le_mul_left' (Code.distFromCode_le_dist_to_mem f g g.property)
    (2 : ℕ∞)).trans_lt ?_
  exact ENat.coe_lt_coe.mpr hnat
