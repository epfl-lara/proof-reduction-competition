theorem fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius (i : Fin ℓ) (steps : ℕ)
    [NeZero steps] (h_i_add_steps : i.val + steps ≤ ℓ)
    (f : OracleFunction 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  (h_fw_dist_lt : fiberwiseClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := i) (steps := steps) (h_i_add_steps := h_i_add_steps) (f := f)) :
  hammingClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩ f := by
  unfold fiberwiseClose at h_fw_dist_lt
  unfold hammingClose
  let d_fw := fiberwiseDistance 𝔽q β (i := i) steps h_i_add_steps f
  let C_i := (BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  let d_H := Code.distFromCode f C_i
  let d_i := BBF_CodeDistance ℓ 𝓡 (⟨i, by omega⟩)
  let d_i_plus_steps := BBF_CodeDistance ℓ 𝓡 ⟨i.val + steps, by omega⟩
  obtain ⟨g', h_g'_mem, h_g'_min_card⟩ : ∃ g' ∈ C_i, d_fw
    = (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g').ncard := by
    let S := (fun (g : C_i) => (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps
      f g).ncard) '' Set.univ
    obtain ⟨g, _, hg⟩ := Nat.sInf_mem (show S.Nonempty from
      ⟨_, ⟨⟨0, C_i.zero_mem⟩, Set.mem_univ _, rfl⟩⟩)
    exact ⟨g.val, g.property, hg.symm⟩
  have h_dist_le_fw_dist_times_fiber_size : (hammingDist f g' : ℕ∞) ≤ d_fw * 2 ^ steps := by
    change (Δ₀(f, g') : ℕ∞) ≤ ↑d_fw * ((2 ^ steps : ℕ) : ℕ∞)
    rw [←ENat.coe_mul, ENat.coe_le_coe, h_g'_min_card]
    let Y := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g'
    letI : Fintype Y := Fintype.ofFinite Y
    let F := fun (y : sDomain 𝔽q β h_ℓ_add_R_rate ⟨i.val + steps, by omega⟩) => Finset.univ.image (qMap_total_fiber 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
      (i := ⟨i, by omega⟩) (steps := steps)
      (h_i_add_steps := fin_ℓ_steps_lt_ℓ_add_R i steps h_i_add_steps) (y := y))
    have hsub : Finset.univ.filter (fun x => f x ≠ g' x) ⊆ Y.toFinset.biUnion F := by
      intro x hx
      let y := iteratedQuotientMap 𝔽q β h_ℓ_add_R_rate i steps h_i_add_steps x
      refine Finset.mem_biUnion.mpr ⟨y, Set.mem_toFinset.mpr
        ⟨x, rfl, (Finset.mem_filter.mp hx).2⟩, ?_⟩
      exact Finset.mem_image.mpr ⟨_, Finset.mem_univ _,
        (is_fiber_iff_generates_quotient_point 𝔽q β i steps h_i_add_steps x y).mp rfl⟩
    apply (Finset.card_le_card hsub).trans
    apply Finset.card_biUnion_le.trans
    calc
      _ ≤ ∑ y ∈ Y.toFinset, 2 ^ steps := Finset.sum_le_sum fun y _ =>
        (Finset.card_image_le).trans_eq (Fintype.card_fin _)
      _ = Y.ncard * 2 ^ steps := by simp
  have h_dist_bridge : d_H ≤ d_fw * 2 ^ steps :=
    (Code.distFromCode_le_dist_to_mem f g' h_g'_mem).trans
      h_dist_le_fw_dist_times_fiber_size
  have h_fw_bound : 2 * d_fw ≤ d_i_plus_steps - 1 := by
    exact Nat.le_of_lt_succ (WithTop.coe_lt_coe.1 h_fw_dist_lt)
  have h_algebraic_identity : (d_i_plus_steps - 1) * 2 ^ steps = d_i - 1 := by
    dsimp [d_i, d_i_plus_steps, BBF_CodeDistance]
    rw [Nat.sub_mul, ←Nat.pow_add, ←Nat.pow_add];
    have h1 : ℓ + 𝓡 - (↑i + steps) + steps = ℓ + 𝓡 - i := by omega
    have h2 : ℓ - (↑i + steps) + steps = ℓ - i := by omega
    rw [h1, h2]
  have h_nat : 2 * (d_fw * 2 ^ steps) < d_i := by
    have h := Nat.mul_le_mul_right (2 ^ steps) h_fw_bound
    rw [h_algebraic_identity, Nat.mul_assoc] at h
    dsimp [d_i, BBF_CodeDistance] at *
    omega
  exact lt_of_le_of_lt (mul_le_mul_left' h_dist_bridge 2)
    (by exact_mod_cast h_nat)
