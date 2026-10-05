theorem fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius (i : Fin ℓ) (steps : ℕ)
    [NeZero steps] (h_i_add_steps : i.val + steps ≤ ℓ)
    (f : OracleFunction 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  (h_fw_dist_lt : fiberwiseClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := i) (steps := steps) (h_i_add_steps := h_i_add_steps) (f := f)) :
  hammingClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩ f := by
  let C := BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, fin_ℓ_lt_ℓ_add_one i⟩
  obtain ⟨⟨g, hmem⟩, _, hg⟩ := Nat.sInf_mem (s :=
    (fun g : C => (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g).ncard) ''
      Set.univ) (Set.image_nonempty.mpr Set.univ_nonempty)
  let D := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g
  let Q := iteratedQuotientMap 𝔽q β h_ℓ_add_R_rate i steps h_i_add_steps
  let K := pointToIterateQuotientIndex 𝔽q β
    (h_ℓ_add_R_rate := h_ℓ_add_R_rate) i.castSucc steps h_i_add_steps
  let F := qMap_total_fiber 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, fin_ℓ_lt_r (h_ℓ_add_R_rate := h_ℓ_add_R_rate) i⟩ steps (fin_ℓ_steps_lt_ℓ_add_R i steps h_i_add_steps)
  have hb : hammingDist f g ≤ D.ncard * 2 ^ steps := by
    let B := {x // f x ≠ g x}
    let J : B → D × Fin (2 ^ steps) := fun x =>
      (⟨Q x.val, ⟨x.val, rfl, x.property⟩⟩, K x.val)
    have hrec (x) : F (Q x) (K x) = x :=
      (is_fiber_iff_generates_quotient_point 𝔽q β i steps h_i_add_steps x (Q x)).mp rfl
    have hj : Function.Injective J := fun x y h =>
      Subtype.ext ((hrec x.val).symm.trans
        ((congrArg (fun p : D × Fin (2 ^ steps) => F p.1.val p.2) h).trans (hrec y.val)))
    have hc := Nat.card_le_card_of_injective J hj
    have hB : Nat.card B = hammingDist f g :=
      (Nat.card_eq_fintype_card (α := B)).trans (Fintype.card_subtype _)
    rwa [hB, Nat.card_prod, Nat.card_coe_set_eq, Nat.card_fin] at hc
  have hfw : 2 * D.ncard ≤ 2 ^ (ℓ + 𝓡 - (i.val + steps)) -
      2 ^ (ℓ - (i.val + steps)) :=
    le_of_eq_of_le (congrArg (2 * ·) hg)
      (Nat.le_of_lt_succ (WithTop.coe_lt_coe.mp h_fw_dist_lt))
  have ht := Nat.mul_le_mul_right (2 ^ steps) hfw
  rw [Nat.sub_mul, Nat.sub_add_eq, Nat.pow_sub_mul_pow 2
      (Nat.le_sub_of_add_le' (h_i_add_steps.trans (Nat.le_add_right ℓ 𝓡))),
    Nat.sub_add_eq, Nat.pow_sub_mul_pow 2 (Nat.le_sub_of_add_le' h_i_add_steps)] at ht
  have hn : 2 * hammingDist f g < BBF_CodeDistance ℓ 𝓡 ⟨i, fin_ℓ_lt_ℓ_add_one i⟩ :=
    Nat.lt_succ_of_le ((Nat.mul_le_mul_left 2 hb).trans
      (by rw [←mul_assoc]; exact ht))
  unfold hammingClose
  apply lt_of_le_of_lt (mul_le_mul_left' (Code.distFromCode_le_dist_to_mem f g hmem) 2)
  exact ENat.coe_lt_coe.mpr hn
