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

  have h_d_i_gt_0 : d_i > 0 := by
    dsimp only [BBF_CodeDistance, d_i]


    omega

  have h_C_i_nonempty : Nonempty C_i := by
    simp only [nonempty_subtype]
    exact Submodule.nonempty (BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i.val, by omega⟩)

  obtain ⟨g', h_g'_mem, h_g'_min_card⟩ : ∃ g' ∈ C_i, d_fw
    = (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g').ncard := by
    let S := (fun (g : C_i) => (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps
      f g).ncard) '' Set.univ
    have hS_nonempty : S.Nonempty := by
      refine Set.image_nonempty.mpr ?_

      exact Set.univ_nonempty
    have h_sInf_mem : sInf S ∈ S := Nat.sInf_mem hS_nonempty


    rcases h_sInf_mem with ⟨g_subtype, _, h_eq⟩
    exact ⟨g_subtype.val, g_subtype.property, by exact id (Eq.symm h_eq)⟩

  have h_dist_le_fw_dist_times_fiber_size : (hammingDist f g' : ℕ∞) ≤ d_fw * 2 ^ steps := by
    change (Δ₀(f, g') : ℕ∞) ≤ ↑d_fw * ((2 ^ steps : ℕ) : ℕ∞)
    rw [←ENat.coe_mul, ENat.coe_le_coe, h_g'_min_card]
    set ΔH := Finset.filter (fun x => f x ≠ g' x) Finset.univ


    set Y_bad := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g'
    simp only at *


    have hFinType_Y_bad : Fintype Y_bad := by exact Fintype.ofFinite ↑Y_bad
    have h_ΔH_subset_bad_fiber_points : ΔH ⊆ Finset.biUnion Y_bad.toFinset
        (t := fun y => ((qMap_total_fiber 𝔽q β (i := ⟨i, by omega⟩) (steps := steps)
          (h_i_add_steps := by apply Nat.lt_add_of_pos_right_of_le; omega) (y := y)) ''
          (Finset.univ : Finset (Fin ((2:ℕ)^steps)))).toFinset) := by
      intro x hx_in_ΔH;
      simp only [mem_filter, ΔH] at hx_in_ΔH
      let y_of_x := iteratedQuotientMap 𝔽q β h_ℓ_add_R_rate i steps h_i_add_steps x
      apply Finset.mem_biUnion.mpr; use y_of_x
      have h_elemenet_Y_bad : y_of_x ∈ Y_bad.toFinset :=
        Set.mem_toFinset.mpr ⟨x, rfl, hx_in_ΔH.2⟩
      simp only [h_elemenet_Y_bad]

      set qMapFiber := qMap_total_fiber 𝔽q β (i := ⟨i, by omega⟩) (steps := steps)
        (h_i_add_steps := by apply Nat.lt_add_of_pos_right_of_le; omega) (y := y_of_x)
      simp only [coe_univ, Set.image_univ, Set.toFinset_range, mem_image, mem_univ, true_and]
      use (pointToIterateQuotientIndex (i := ⟨i, by omega⟩) (steps := steps)
        (h_i_add_steps := by omega) (x := x))
      exact is_fiber_iff_generates_quotient_point 𝔽q β i steps (by omega)
        (x := x) (y := y_of_x).mp (by rfl)
    apply (Finset.card_le_card h_ΔH_subset_bad_fiber_points).trans
    apply Finset.card_biUnion_le.trans
    calc
      _ ≤ ∑ y ∈ Y_bad.toFinset, 2 ^ steps := by
        apply Finset.sum_le_sum
        intro y hy
        simpa only [coe_univ, Set.image_univ, Set.toFinset_range,
          Fintype.card_fin, Finset.card_univ] using
          (Finset.card_image_le (s := Finset.univ)
            (f := qMap_total_fiber 𝔽q β (i := ⟨i, by omega⟩)
              (steps := steps) (h_i_add_steps := by have := NeZero.pos 𝓡; dsimp; omega) (y := y)))
      _ = _ := by simp only [sum_const, smul_eq_mul, Set.toFinset_card, ← Nat.card_coe_set_eq, Nat.card_eq_fintype_card]

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
    dsimp only [BBF_CodeDistance, Nat.add_one_sub_one, d_i_plus_steps, d_i]
    rw [Nat.sub_mul, ←Nat.pow_add, ←Nat.pow_add];
    congr 1 <;> congr 1 <;> omega

  change 2 * d_H < (d_i : ℕ∞)
  calc
    2 * d_H ≤ 2 * (d_fw * 2 ^ steps) := mul_le_mul_left' h_dist_bridge 2
    _ = ↑((2 * d_fw) * 2 ^ steps) := by rw [mul_assoc]; rfl
    _ ≤ ↑((d_i_plus_steps - 1) * 2 ^ steps) :=
      ENat.coe_le_coe.mpr (Nat.mul_le_mul_right _ h_fw_bound)
    _ < (d_i : ℕ∞) := ENat.coe_lt_coe.mpr (by
      rw [h_algebraic_identity]
      omega)