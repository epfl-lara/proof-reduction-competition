theorem fiberwise_dist_lt_imp_dist_lt_unique_decoding_radius (i : Fin ℓ) (steps : ℕ)
    [NeZero steps] (h_i_add_steps : i.val + steps ≤ ℓ)
    (f : OracleFunction 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩)
  (h_fw_dist_lt : fiberwiseClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := i) (steps := steps) (h_i_add_steps := h_i_add_steps) (f := f)) :
  hammingClose 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, by omega⟩ f := by
  classical
  unfold fiberwiseClose at h_fw_dist_lt
  have h1 : ℓ + 𝓡 - (i.val + steps) + steps = ℓ + 𝓡 - i.val := by omega
  have h2 : ℓ - (i.val + steps) + steps = ℓ - i.val := by omega
  let C := BBF_Code 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate) ⟨i, fin_ℓ_lt_ℓ_add_one i⟩
  let d := fiberwiseDistance 𝔽q β i steps h_i_add_steps f
  obtain ⟨g, _, hg⟩ := Nat.sInf_mem (s := (fun g : C =>
    (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g).ncard) '' Set.univ)
    (Set.image_nonempty.mpr ⟨⟨0, C.zero_mem⟩, Set.mem_univ _⟩)
  change (fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g).ncard = d at hg
  let Y := fiberwiseDisagreementSet 𝔽q β i steps h_i_add_steps f g
  let q := iteratedQuotientMap 𝔽q β h_ℓ_add_R_rate i steps h_i_add_steps
  let k := pointToIterateQuotientIndex 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := ⟨i, fin_ℓ_lt_ℓ_add_one i⟩)
    (steps := steps) (h_i_add_steps := h_i_add_steps)
  let t := qMap_total_fiber 𝔽q β (h_ℓ_add_R_rate := h_ℓ_add_R_rate)
    (i := ⟨i, fin_ℓ_lt_r (h_ℓ_add_R_rate := h_ℓ_add_R_rate) i⟩) (steps := steps)
    (h_i_add_steps := fin_ℓ_steps_lt_ℓ_add_R i steps h_i_add_steps)
  have ht (x) : t (y := q x) (k x) = x :=
    (is_fiber_iff_generates_quotient_point 𝔽q β i steps h_i_add_steps x (q x)).mp rfl
  let e : {x // f x ≠ g.val x} → Y × Fin (2 ^ steps) :=
    fun x => (⟨q x, ⟨x, rfl, x.property⟩⟩, k x)
  have he : Function.Injective e := by
    intro x z h
    apply Subtype.ext
    exact (ht x.val).symm.trans ((congrArg (fun p : Y × Fin (2 ^ steps) =>
      t (y := p.1) p.2) h).trans (ht z.val))
  have hc : hammingDist f g ≤ d * 2 ^ steps := by
    have h := Nat.card_le_card_of_injective e he
    rw [Nat.card_prod, Nat.card_coe_set_eq Y, hg] at h
    simpa only [Nat.card_eq_fintype_card, Fintype.card_subtype,
      Fintype.card_fin, hammingDist] using h
  have hf : 2 * d ≤ 2 ^ (ℓ + 𝓡 - (i.val + steps)) - 2 ^ (ℓ - (i.val + steps)) := by
    apply Nat.le_of_lt_succ
    exact_mod_cast h_fw_dist_lt
  have hb := Nat.mul_le_mul_left 2 hc
  rw [← Nat.mul_assoc] at hb
  replace hb := hb.trans (Nat.mul_le_mul_right (2 ^ steps) hf)
  rw [Nat.sub_mul, ← Nat.pow_add, ← Nat.pow_add, h1, h2] at hb
  unfold hammingClose
  apply lt_of_le_of_lt (mul_le_mul_left' (Code.distFromCode_le_dist_to_mem f g g.property) 2)
  exact_mod_cast Nat.lt_succ_of_le hb