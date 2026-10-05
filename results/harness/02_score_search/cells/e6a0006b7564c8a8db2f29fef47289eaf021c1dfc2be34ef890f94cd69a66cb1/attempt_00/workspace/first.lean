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
  have h_C_i_nonempty : Nonempty C_i := by
    simp only [nonempty_subtype, C_i]
    exact Submodule.nonempty (BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i.val, by omega⟩)
  obtain ⟨g', h_g'_mem, h_g'_min_card⟩ : ∃ g' ∈ C_i, d_fw
    = (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g').ncard := by
    let S := (fun (g : C_i) => (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps
      f g).ncard) '' Set.univ
    have hS_nonempty : S.Nonempty := by
      refine Set.image_nonempty.mpr ?_
      exact Set.univ_nonempty
    have h_sInf_mem : sInf S ∈ S := Nat.sInf_mem hS_nonempty
    unfold d_fw at h_sInf_mem
    rw [Set.mem_image] at h_sInf_mem
    rcases h_sInf_mem with ⟨g_subtype, _, h_eq⟩
    exact ⟨g_subtype.val, g_subtype.property, by exact id (Eq.symm h_eq)⟩
  have h_dist_le_fw_dist_times_fiber_size : (hammingDist f g' : ℕ∞) ≤ d_fw * 2 ^ steps := by
    change (Δ₀(f, g') : ℕ∞) ≤ ↑d_fw * ((2 ^ steps : ℕ) : ℕ∞)
    rw [←ENat.coe_mul, ENat.coe_le_coe, h_g'_min_card]
    set ΔH := Finset.filter (fun x => f x ≠ g' x) Finset.univ
    have h_dist_eq_card : hammingDist f g' = ΔH.card := by
      simp only [hammingDist, ne_eq, ΔH]
    rw [h_dist_eq_card]
    set Y_bad := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g'
    simp only at *
    have hFinType_Y_bad : Fintype Y_bad := by exact Fintype.ofFinite ↑Y_bad
    have h_ΔH_subset_bad_fiber_points : ΔH ⊆ Finset.biUnion Y_bad.toFinset
        (t := fun y => ((qMap_total_fiber 𝔽q β (i := ⟨i, by omega⟩) (steps := steps)
          (h_i_add_steps := by apply Nat.lt_add_of_pos_right_of_le; omega) (y := y)) ''
          (Finset.univ : Finset (Fin ((2:ℕ)^steps)))).toFinset) := by
      intro x hx_in_ΔH;
      simp only [ΔH, Finset.mem_filter] at hx_in_ΔH
      let y_of_x := iteratedQuotientMap 𝔽q β h_ℓ_add_R_rate i steps h_i_add_steps x
      apply Finset.mem_biUnion.mpr; use y_of_x
      have h_elemenet_Y_bad : y_of_x ∈ Y_bad.toFinset := by
        exact Set.mem_toFinset.mpr ⟨x, rfl, hx_in_ΔH.2⟩
      simp only [h_elemenet_Y_bad, true_and]
      set qMapFiber := qMap_total_fiber 𝔽q β (i := ⟨i, by omega⟩) (steps := steps)
        (h_i_add_steps := by apply Nat.lt_add_of_pos_right_of_le; omega) (y := y_of_x)
      simp only [coe_univ, Set.image_univ, Set.toFinset_range, mem_image, mem_univ, true_and]
      use (pointToIterateQuotientIndex (i := ⟨i, by omega⟩) (steps := steps)
        (h_i_add_steps := by omega) (x := x))
      have h_res := is_fiber_iff_generates_quotient_point 𝔽q β i steps (by omega)
        (x := x) (y := y_of_x).mp (by rfl)
      exact h_res
    apply (Finset.card_le_card h_ΔH_subset_bad_fiber_points).trans
    rw [Finset.card_biUnion]
    ·
      simp only [Set.toFinset_card]
      have h_card_fiber_per_quotient_point := card_qMap_total_fiber 𝔽q β
        (h_ℓ_add_R_rate := h_ℓ_add_R_rate) i steps h_i_add_steps
      simp only [Set.image_univ, Fintype.card_ofFinset,
        Subtype.forall] at h_card_fiber_per_quotient_point
      have h_card_fiber_of_each_y : ∀ y ∈ Y_bad.toFinset,
          Fintype.card ((qMap_total_fiber 𝔽q β (i := ⟨↑i, by omega⟩) (steps := steps)
            (h_i_add_steps := by apply Nat.lt_add_of_pos_right_of_le; omega) (y := y)) ''
            ↑(Finset.univ : Finset (Fin ((2:ℕ)^steps)))) = 2 ^ steps := by
        intro y hy_in_Y_bad
        have hy_card_fiber_of_y := h_card_fiber_per_quotient_point (a := y) (b := by
          exact Submodule.coe_mem y)
        simp only [coe_univ, Set.image_univ, Fintype.card_ofFinset, hy_card_fiber_of_y]
      rw [Finset.sum_congr rfl h_card_fiber_of_each_y]
      simp only [sum_const, Set.toFinset_card, smul_eq_mul, ofNat_pos, pow_pos,
        _root_.mul_le_mul_right, ge_iff_le]
      conv_rhs => rw [←_root_.Nat.card_coe_set_eq]
      simp only [card_eq_fintype_card, le_refl]
    ·
      intro y₁ hy₁ y₂ hy₂ hy_ne
      have h_disjoint := qMap_total_fiber_disjoint (i := ⟨↑i, by omega⟩) (steps := steps)
        (h_i_add_steps := by omega) (y₁ := y₁) (y₂ := y₂) (hy_ne := hy_ne)
      simp only [Function.onFun, coe_univ]
      exact h_disjoint
  have h_dist_bridge : d_H ≤ d_fw * 2 ^ steps := by
    apply le_trans (a := d_H) (c := d_fw * 2 ^ steps) (b := hammingDist f g')
    ·
      simp only [distFromCode, SetLike.mem_coe, hammingDist, ne_eq, d_H];
      apply sInf_le
      use g'
    · exact h_dist_le_fw_dist_times_fiber_size
  have h_fw_bound : 2 * d_fw ≤ d_i_plus_steps - 1 := by
    exact Nat.le_of_lt_succ (WithTop.coe_lt_coe.1 h_fw_dist_lt)
  have h_algebraic_identity : (d_i_plus_steps - 1) * 2 ^ steps = d_i - 1 := by
    dsimp [d_i, d_i_plus_steps, BBF_CodeDistance]
    rw [Nat.sub_mul, ←Nat.pow_add, ←Nat.pow_add];
    have h1 : ℓ + 𝓡 - (↑i + steps) + steps = ℓ + 𝓡 - i := by
      rw [Nat.sub_add_eq_sub_sub_rev (h1 := by omega) (h2 := by omega),
        Nat.add_sub_cancel (n := i) (m := steps)]
    have h2 : (ℓ - (↑i + steps) + steps) = ℓ - i := by
      rw [Nat.sub_add_eq_sub_sub_rev (h1 := by omega) (h2 := by omega),
        Nat.add_sub_cancel (n := i) (m := steps)]
    rw [h1, h2]
  have h_nat : 2 * (d_fw * 2 ^ steps) < d_i := by
    have h := Nat.mul_le_mul_right (2 ^ steps) h_fw_bound
    rw [h_algebraic_identity, Nat.mul_assoc] at h
    dsimp [d_i, BBF_CodeDistance] at *
    omega
  exact lt_of_le_of_lt (mul_le_mul_left' h_dist_bridge 2)
    (by exact_mod_cast h_nat)
